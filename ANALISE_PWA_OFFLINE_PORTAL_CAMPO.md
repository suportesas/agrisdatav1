# Análise — PWA do Portal Campo não funciona offline

**Data da análise:** 2026-07-29
**Escopo:** `static/campo_pwa/` (`pwa.js`, `sw.js`, `offline-db.js`) e `cadastros/views_portal_campo.py`
**Sintoma relatado:** app mostra a tela "Sem conexão" ao abrir offline, mesmo sendo um PWA com Service Worker e SQLite WASM já implementados.

## Diagnóstico

O app tem a infraestrutura de um PWA offline-first (Service Worker, Cache API, SQLite WASM via OPFS, fila de sincronização), mas ela está **parcialmente implementada e parcialmente não conectada**. O "offline" hoje funciona só por acidente (cache HTTP de páginas já visitadas), não por design.

### 1. Tela "Sem conexão" é o fallback padrão do Service Worker, sem app-shell precacheado
- `static/campo_pwa/sw.js:6-12` — `STATIC_CACHE` (populado no `install`) só contém `pwa.js`, `offline-db.js` e CSS de CDN. Nenhuma rota HTML (`/portal/campo/`, login, detalhe de OS) é precacheada.
- `static/campo_pwa/sw.js:44-54` e `71-84` — toda navegação GET usa `networkFirstPortal`: tenta rede, cai pro Cache Storage, e se não achar nada aí, retorna `offlineFallbackPage()` (`sw.js:109-125` — é a tela do print).
- **Consequência:** uma rota só existe offline depois de ter sido visitada com sucesso online pelo menos uma vez. Primeira instalação, cache limpo (troca de aparelho, `unregister`, storage cheio) ou qualquer página nova → tela "Sem conexão" imediatamente.

### 2. Banco SQLite offline (`offline-db.js`) não é usado para leitura — é código morto
- `offline-db.js` define `CampoDB.upsertOS()`, `listOS()`, `getOS()` — pensado para servir os dados de OS a partir do banco local quando offline (é literalmente o que o comentário no topo do `sw.js` promete: *"quando offline, serve do SQLite local"*).
- Busca em todos os templates de `cadastros/templates/cadastros/portal_campo/` não encontrou nenhuma chamada a `CampoDB`, `listOS`, `upsertOS` ou `getOS`.
- **Consequência:** os dados de OS nunca são gravados no SQLite local quando a página carrega online, e nunca são lidos dele quando offline. O único uso real do SQLite hoje é a tabela `sync_queue` (fila de escrita).

### 3. Fila de sincronização de escrita só reconhece 2 das 5 ações de OS
- `cadastros/views_portal_campo.py:863-905` (`_process_offline_mutation`) só mapeia os endpoints `.../os/<id>/iniciar/` e `.../os/<id>/executar/`.
- **`pausar`, `retomar` e `concluir` não têm handler.** Se enfileiradas offline, o SW já responde `{ok: true, offline: true}` na hora para não travar a UI (`sw.js:102`), fazendo o usuário achar que a ação foi concluída.
- Quando a fila sincroniza de verdade (`pwa.js:54-86`, evento `online`), o servidor devolve `{'ok': False, 'detail': 'endpoint não mapeado: ...'}` — e isso é tratado só como "incrementa tentativa" (`pwa.js:78`), sem nunca avisar o usuário que a ação nunca foi aplicada no banco.

### 4. Concluir OS offline é impossível mesmo se fosse mapeado (exige foto obrigatória)
- `campo_os_concluir` (`views_portal_campo.py:715-786`) exige `request.FILES.get('foto_evidencia')` — RN-03, foto obrigatória (`views_portal_campo.py:728-730`). O form desta tela é `multipart/form-data`.
- `postWithOfflineQueue` (`sw.js:86-107`) lê o corpo da requisição com `cloned.text()` e faz `new URLSearchParams(text).entries()` (`sw.js:96`) — isso não extrai arquivos/blobs de um corpo `multipart/form-data`; o campo de arquivo se perde na conversão.
- **Consequência:** mesmo corrigindo o item 3, a foto de evidência (obrigatória) nunca chegaria ao servidor via fila offline — a conclusão de OS ficaria bloqueada por RN-03 mesmo depois de "sincronizar".

## Correções propostas (para execução futura)

Ordem sugerida: 1 e 2 resolvem o sintoma relatado (tela offline "morta"); 3 e 4 resolvem a corrupção silenciosa de dados que aconteceria assim que o offline passasse a ser usado de verdade em campo.

### Correção 1 — Precachear o app-shell no `install`
- Adicionar ao `STATIC_CACHE` (ou a um precache separado) as rotas de navegação essenciais: `/portal/campo/` (home), tela de login, e o template de detalhe de OS (ao menos o shell, já que o conteúdo dinâmico virá do SQLite — ver Correção 2).
- Alternativa mais robusta: usar `cache.addAll` num evento disparado após o primeiro login bem-sucedido, para já cachear a página autenticada real (evita cachear a tela de login como se fosse a home).

### Correção 2 — Ligar o SQLite WASM como fonte de leitura offline real
- Ao carregar `campo_home` (lista de OS) e `campo_os_detail` com sucesso online, chamar `CampoDB.upsertOS(...)` com os dados renderizados (via um `<script type="application/json">` no template, lido pelo JS da página).
- Quando `networkFirstPortal` cair no fallback (offline e sem cache daquela rota), em vez de só devolver `offlineFallbackPage()`, a página (ou um shell precacheado) deve chamar `CampoDB.listOS()` / `CampoDB.getOS(id)` e renderizar a lista/detalhe a partir do banco local. Isso exige um template "shell" que renderiza via JS a partir do SQLite, não apenas HTML estático de servidor.
- Manter `offlineFallbackPage()` só como fallback de último caso (banco local também vazio, ex.: primeiro acesso do dispositivo sem nunca ter sincronizado).

### Correção 3 — Mapear `pausar`, `retomar` e `concluir` em `_process_offline_mutation`
- Adicionar os três blocos `re.match` faltantes em `views_portal_campo.py`, espelhando a lógica das views síncronas (`campo_os_pausar`, `campo_os_retomar`, `campo_os_concluir` — sem a parte de arquivo, ver Correção 4).
- No `pwa.js`, quando `data.results[i].ok === false` após sync, notificar o usuário (banner/alerta), não só logar/reincrementar tentativa silenciosamente — hoje o usuário nunca fica sabendo que uma ação offline falhou permanentemente.

### Correção 4 — Suportar upload de foto na fila offline
- Trocar a fila de `sync_queue` (JSON/texto) por um formato que suporte Blob: gravar a foto como `Blob`/`ArrayBuffer` em uma tabela própria do SQLite (ou em IndexedDB, mais simples para Blobs que SQLite WASM/OPFS) e referenciar o item da fila por essa foto.
- Ajustar `postWithOfflineQueue` (`sw.js`) para extrair o campo de arquivo do `FormData` (usar `request.formData()` em vez de `request.text()` quando `Content-Type` for `multipart/form-data`) antes de enfileirar.
- Ajustar `campo_sync_offline` / `_process_offline_mutation` no backend para aceitar o arquivo (ex.: endpoint de sync separado para multipart, ou enviar a foto como base64 dentro do JSON — mais simples de implementar, com custo de payload maior).
- Enquanto isso não for implementado, considerar um aviso explícito na UI: "Concluir OS requer conexão (foto obrigatória)" para não deixar o usuário achar que a ação offline funcionou quando na verdade não vai sincronizar.

### Correção 5 — Resolução de conflitos (edição concorrente offline vs. servidor)

**Problema:** enquanto um funcionário está offline enfileirando ações numa OS, o estado dessa OS no servidor pode mudar (outro funcionário agiu, um gestor cancelou a OS pelo sistema web, etc.). Sem tratamento, ao sincronizar a fila o sistema pode aplicar uma ação sobre um estado que não existe mais, corrompendo o histórico, ou simplesmente falhar sem o usuário nunca saber.

**Como outros sistemas resolvem isso** (categorias reais de mercado, da mais simples à mais complexa):

1. **Last-Write-Wins (LWW) por timestamp** — usado por Trello, Notion, CouchDB/PouchDB por padrão. Cada mutação carrega o horário do dispositivo; a última a chegar "vence". Simples, mas pode descartar dados silenciosamente — não recomendado para OS onde uma foto obrigatória ou um encerramento não pode simplesmente sumir.
2. **Concorrência otimista com versão (optimistic concurrency)** — usado por Salesforce Field Service, Google Docs (nível de documento), APIs REST com `ETag`/`If-Match`. Cada registro tem uma versão/`updated_at`; o cliente guarda a versão que leu por último quando estava online. Ao sincronizar, o servidor compara: se a versão mudou, a mutação é **rejeitada como conflito** (não aplicada às cegas) e devolvida ao app para o usuário decidir o que fazer.
3. **Log de operações (event sourcing) com validação de precondição no replay** — usado por sistemas de campo tipo ServiceMax, Fieldwire, Kickserv: a ação offline não é "sobrescreva o campo X", é "aplique a transição Y **se** a OS ainda estiver no estado Z". Se a precondição falhar no momento da sincronização, a operação é rejeitada com um motivo, nunca aplicada de qualquer jeito. **É exatamente o padrão que `_process_offline_mutation` já usa parcialmente hoje** (`views_portal_campo.py:873`: só transiciona `APROVADA → EM_ANDAMENTO` se o status ainda for `APROVADA`) — só precisa ser estendido para as 5 ações e ter o resultado exposto ao usuário.
4. **CRDTs / Operational Transformation** — usado por Google Docs/Figma para edição simultânea caractere-a-caractere. É a solução mais robusta, mas serve para edição granular colaborativa em tempo real; é over-engineering para um fluxo de OS onde só uma pessoa por vez opera cada ordem de serviço.

**Proposta de replicação para o Portal Campo (combina as opções 2 e 3, que já são o caminho natural dado o código atual):**

- **Ações que são transições de estado** (`iniciar`, `pausar`, `retomar`, `concluir`): manter e generalizar o padrão que já existe — cada handler em `_process_offline_mutation` deve validar a precondição de status atual antes de aplicar (ex.: `concluir` só é válido se `status in ('APROVADA', 'EM_ANDAMENTO')`, igual à view síncrona `campo_os_concluir` já faz). Se a precondição falhar, retornar `{'ok': False, 'motivo': 'A OS não está mais no estado esperado (status atual: X). Ação não aplicada.'}` em vez de tentar forçar.
- **Ações que são inserções** (registro de execução `OSFuncionario`, insumos aplicados, horímetro): continuar como *append*, nunca *update* de um valor existente. Isso já é o padrão do código (`OSFuncionario.objects.create(...)` em vez de update) — é o motivo pelo qual essas ações praticamente não geram conflito: duas inserções de dois funcionários diferentes convivem, não se sobrescrevem. Manter esse padrão para qualquer nova ação offline.
- **Adicionar um carimbo de versão/estado esperado na fila local**: quando o app enfileira uma ação offline, gravar junto o `status` da OS que o funcionário via na tela naquele momento (já disponível no HTML/JS renderizado). Ao sincronizar, o servidor compara esse "status esperado" com o status real atual — se bater, aplica; se não bater, marca como conflito e devolve o motivo, em vez de assumir que a precondição do fluxo normal (checada por outra lógica) é suficiente.
- **Nunca falhar silenciosamente**: todo `{'ok': False}` retornado pelo `_process_offline_mutation` deve chegar até a UI (banner ou notificação, ver Correção 3) com o motivo humano-legível — hoje o `pwa.js` só incrementa `tentativas` e tenta de novo depois, o que nunca resolve um conflito de estado (tentar de novo não muda o fato de que a OS já foi cancelada por outra pessoa).
- **Não implementar CRDT/OT** — desnecessário aqui: o volume de concorrência é baixo (um funcionário por OS na prática) e as ações já são majoritariamente idempotentes/append-only. O ganho de robustez de LWW → optimistic concurrency + validação de precondição já cobre os cenários reais de campo (perda de sinal, gestor alterando OS pelo painel web) sem a complexidade de um CRDT.

## Arquivos envolvidos
- `static/campo_pwa/sw.js`
- `static/campo_pwa/pwa.js`
- `static/campo_pwa/offline-db.js`
- `cadastros/views_portal_campo.py` (`campo_os_iniciar`, `campo_os_pausar`, `campo_os_retomar`, `campo_os_executar`, `campo_os_concluir`, `campo_sync_offline`, `_process_offline_mutation`)
- `cadastros/templates/cadastros/portal_campo/` (templates que precisarão renderizar a partir do SQLite local quando offline)
