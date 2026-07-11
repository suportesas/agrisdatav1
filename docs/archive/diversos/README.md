Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Documentos históricos diversos sem cluster próprio

# Índice de documentos diversos arquivados

Os arquivos abaixo foram movidos para esta pasta sem consolidação (cada um mantém seu conteúdo original e nome de arquivo, sem subpasta `fontes/`), por serem documentos pontuais de features/correções já concluídas e sem sobreposição forte entre si. Um resumo de uma linha por arquivo:

- **`ANALISE_SEPARACAO_MENUS.md`** — Análise do problema de menus não diferenciados corretamente por tipo de usuário (Superuser Admin / Empresa Admin / Operador) e proposta do que cada perfil deveria ver.
- **`ANALISE_STATUS.md`** — Snapshot de status do projeto (2026-04-27) comparando módulos do PRD com o que estava implementado/parcial/faltando, por fase do roadmap.
- **`ANALISE_STATUS_PRD.md`** — snapshot de 2026-02-17, referencia Django 5.2.7 (desatualizado — versão atual é 6.0.6 conforme README.md raiz). Levantamento percentual de requisitos funcionais (RF-xxx) do PRD implementados/parciais/planejados, com links para arquivos-fonte.
- **`CORRECOES_SOLICITACAO_COMPRA.md`** — Correção de bug de duplicação de campos de produto no formset do formulário de Solicitação de Compra (template + JavaScript de clonagem de linha).
- **`DOCUMENTACAO_ESTAGIO_TEMPLATE.md`** — Documentação do sistema de "Estágios Template" (estágios de desenvolvimento de pragas pré-cadastrados, copiados automaticamente para novas empresas via signal).
- **`FIXO_ENTRADA_ESTOQUE.md`** — Correção de bug em que `ItemRecebimento` registrava entrada de estoque prematuramente (ainda em PENDENTE/CONFERIDO) em vez de apenas na finalização do recebimento (`compras/models.py`).
- **`FIX_CULTURA_IMAGE_STORAGE.md`** — Correção de upload de imagem de Cultura para o Supabase Storage, que falhava por RLS; solução trocou `SUPABASE_ANON_KEY` por `SUPABASE_SERVICE_ROLE_KEY` em `core/storage.py`.
- **`GUIA_DIVERGENCIAS_AVALIACAO.md`** — Guia de uso do sistema de tipos de divergência (recebimento), conferência estruturada de divergências e avaliação de fornecedor (5 critérios) pós-finalização do recebimento.
- **`IMPLEMENTACAO_CADASTRO_LOTE_ESTAGIOS.md`** — Implementação de cadastro em lote (via AJAX, sem reload) de estágios de desenvolvimento de pragas, com views em `cadastros/views_monitoramento_mip.py`.
- **`IMPLEMENTACAO_GRUPOS_CORPORATIVOS.md`** — Implementação da Fase 1 de "Grupos Corporativos" (Enterprise Plus): model `GrupoCorporativo`, vínculo opcional de `Empresa` a um grupo, forms e views de gestão.
- **`IMPLEMENTACAO_PRAZO_HIDDEN_FIELDS.md`** — Integração do campo `prazo_pagamento` do cadastro de cliente com presets de prazo via campos hidden preenchidos por JavaScript (em vez de input numérico direto).
- **`LEIA_ME_DIVERGENCIAS.md`** — Registro de implementação completa do sistema de divergências de recebimento e avaliação de fornecedor (models `TipoDivergencia`, `DivergenciaRecebimento`, `AvaliacaoFornecedor`) — par do `GUIA_DIVERGENCIAS_AVALIACAO.md` acima, um é o guia de uso e o outro a confirmação técnica da entrega.
- **`MUDANCAS_VISUALIZACAO_ESTAGIOS.md`** — Redesenho da listagem de estágios de desenvolvimento de pragas: de tabela única para accordion Bootstrap agrupado por praga (`estagio_list.html` + `views_monitoramento_mip.py`).
- **`PERMISSAO_AUTOMATICA_ADMIN.md`** — Implementação (RF-055) de concessão automática da permissão `view_other_fazendas_estoque` a todo usuário administrador via signal Django, com remoção automática caso o usuário deixe de ser admin.
- **`PROMPT_EXECUCAO_PENDENTES.md`** — Prompt/especificação técnica preparado para uma sessão futura de desenvolvimento, listando módulos pendentes do PRD (ex.: Estufas e Transplantio) com modelos e regras arquiteturais a seguir — não é um registro de trabalho já feito, é uma instrução para trabalho futuro.
- **`QUESTIONAMENTO_MOVIMENTACOES_ESTOQUE.md`** — Registro de dúvida/investigação (03/03/2026) sobre o comportamento de status PENDENTE vs. execução em movimentações de estoque e clareza de exibição do tipo/origem no template de detalhe; documento fica em aberto ("pendente de análise detalhada"), não confirma uma correção.
- **`pr_body_for_PR.md`** — descrição de PR avulsa, não é documentação de produto. Descreve correções nos formulários de upload de documentos de Fornecedor/Fazenda e validação de `FornecedorForm` (campo `regime_tributario` deixou de ser obrigatório), incluindo sincronização de endereço entre `Fornecedor` e `FornecedorEndereco`.
