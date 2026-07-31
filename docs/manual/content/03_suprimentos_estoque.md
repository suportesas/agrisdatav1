# Suprimentos & Estoque

## Produtos (`/produtos/`)

### Visão geral

O catálogo de produtos é a base de todo o sistema: praticamente todos os outros módulos (compras, estoque, vendas, faturamento) referenciam um `Produto`. Cada produto pertence a uma hierarquia **Categoria → Subcategoria** (ex: Fertilizante → Químico/Orgânico/Foliar/Mineral; Defensivo → Herbicida/Inseticida/Fungicida/Acaricida), tem uma **Unidade de Medida**, um **Tipo de Produto** e dados fiscais (NCM, tributação) usados na emissão de notas fiscais.

### Conceitos principais

| Conceito | Papel |
|---|---|
| Categoria → Subcategoria | Classificação hierárquica do produto; a subcategoria só aparece no formulário depois de escolhida a categoria pai |
| Tipo de Produto | Classificação livre adicional (ex: matéria-prima, revenda, insumo) |
| Unidade de Medida | Unidade em que o produto é estocado; pode ser diferente da unidade de compra/venda (o **Fator de Conversão** faz a ponte entre elas) |
| Marca | Fabricante/marca comercial do produto |
| Natureza de Operação | Natureza fiscal usada nas notas fiscais que envolvem o produto |
| Variantes / Atributos | Permitem um mesmo produto-base ter variações (ex: tamanho, cor) sem duplicar o cadastro |

Produtos do tipo **Defensivo Agrícola** têm campos próprios (ingrediente ativo, classe toxicológica, intervalo de segurança, culturas registradas) e podem ser vinculados a culturas específicas — essa relação alimenta as recomendações do módulo MIP (Manejo Integrado de Pragas).

### Tela: Dashboard de Produtos

<figure>
  <img src="screenshots/produtos/01-dashboard.png" alt="Dashboard de Produtos">
  <figcaption>Indicadores gerais do catálogo: total de produtos, ativos/inativos, alertas de estoque baixo.</figcaption>
</figure>

### Tela: Lista de Produtos

<figure>
  <img src="screenshots/produtos/02-lista.png" alt="Lista de Produtos">
  <figcaption>Catálogo em cards, com foto, categoria, status, preço de venda e estoque atual de cada produto.</figcaption>
</figure>

A listagem (`/produtos/`) mostra contadores no topo (total, ativos, inativos, estoque baixo) e permite buscar por código/nome/código de barras, e filtrar por categoria, tipo e status. Cada card traz atalhos rápidos para visualizar, editar, duplicar e excluir (soft-delete via `ativo=False`). Produtos com variantes mostram um indicador "N variantes" em vez de um preço único.

### Tela: Detalhe do Produto

<figure>
  <img src="screenshots/produtos/03-detalhe.png" alt="Detalhe de um Produto">
  <figcaption>Ficha completa do produto: dados gerais, fiscais, fornecedores vinculados e histórico de preços.</figcaption>
</figure>

### Tela: Novo Produto

<figure>
  <img src="screenshots/produtos/04-novo.png" alt="Formulário de Novo Produto">
  <figcaption>Formulário em 6 abas: Geral, Fiscal, Tributações, Financeiro, Estoque, Fornecedores.</figcaption>
</figure>

**Como preencher (aba Geral):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Código | Não | Deixe em branco para o sistema gerar automaticamente |
| Código de Barras | Não | EAN/GTIN, se houver |
| Nome | Sim | Nome completo do produto |
| Nome Resumido | Não | Usado onde o espaço é curto (ex: etiquetas) |
| Categoria | Sim | Escolher primeiro — filtra as opções de Subcategoria |
| Subcategoria | Não | Só aparece depois de escolher a Categoria; o botão **+** ao lado cria uma nova subcategoria sem sair do formulário |
| Unidade de Medida / Unidade de Compra / Unidade de Venda | Sim (medida) | Se a compra/venda usa unidade diferente da de estoque, preencha o **Fator de Conversão** |
| Peso líquido / bruto por unidade | Não | Usado em cálculos de packing list e frete |
| Ativo | Não (padrão ligado) | Desligar em vez de excluir um produto já usado em documentos |

A aba **Fiscal** define NCM, CFOP padrão e origem da mercadoria; **Tributações** guarda alíquotas por operação; **Financeiro** define preço de custo, preço de venda e margem; **Estoque** define estoque mínimo/máximo e se o produto **controla estoque** (produtos de serviço, por exemplo, não controlam); **Fornecedores** vincula fornecedores habituais e seus preços de referência.

### Telas de apoio ao catálogo

<figure>
  <img src="screenshots/produtos/05-tipos-produto.png" alt="Tipos de Produto">
  <figcaption>Tipos de Produto (`/produtos/tipos-produto/`).</figcaption>
</figure>

<figure>
  <img src="screenshots/produtos/06-categorias.png" alt="Categorias">
  <figcaption>Categorias (`/produtos/categorias/`) — nível superior da hierarquia de classificação.</figcaption>
</figure>

<figure>
  <img src="screenshots/produtos/07-subcategorias.png" alt="Subcategorias">
  <figcaption>Subcategorias (`/produtos/subcategorias/`), sempre associadas a uma categoria pai.</figcaption>
</figure>

<figure>
  <img src="screenshots/produtos/08-marcas.png" alt="Marcas">
  <figcaption>Marcas (`/produtos/marcas/`) — fabricantes/marcas comerciais dos produtos.</figcaption>
</figure>

<figure>
  <img src="screenshots/produtos/09-unidades.png" alt="Unidades de Medida">
  <figcaption>Unidades de Medida (`/produtos/unidades/`), usadas em compras, estoque e vendas.</figcaption>
</figure>

<figure>
  <img src="screenshots/produtos/10-naturezas.png" alt="Naturezas de Operação">
  <figcaption>Naturezas de Operação (`/produtos/naturezas/`) — classificação fiscal usada nas notas fiscais.</figcaption>
</figure>

Essas seis telas de apoio (Tipos de Produto, Categorias, Subcategorias, Marcas, Unidades e Naturezas de Operação) seguem o mesmo padrão simples: uma lista com busca/status e um formulário curto (nome + código, em geral 1-2 campos obrigatórios). São cadastradas uma vez e reutilizadas por todos os produtos — e podem ser criadas "on the fly" pelo botão **+** direto no formulário de produto, sem precisar navegar até a tela dedicada.

### Fluxo passo a passo — cadastrar um produto novo

1. Garanta que a **Categoria** (e Subcategoria, se aplicável) já existe — ou crie na hora, pelo botão **+**.
2. Garanta que a **Unidade de Medida** existe.
3. Preencha a aba Geral (nome, categoria, unidade) e salve — ou navegue pelas demais abas antes de salvar, se já tiver os dados fiscais/financeiros em mãos.
4. Complete a aba **Fiscal** antes do produto ser usado numa nota fiscal — NCM incorreto ou ausente bloqueia a emissão.
5. Se o produto for comprado de fornecedores específicos, vincule-os na aba **Fornecedores** — isso acelera a criação de cotações no módulo de Compras.

### Dicas e erros comuns

- Um produto **inativo** (`ativo=False`) continua existindo no histórico (notas, movimentações antigas) mas some das buscas de uso corrente — é a forma correta de "excluir" um produto que já foi usado.
- Sem uma **Subcategoria** compatível com a Categoria escolhida, o formulário não deixa salvar — cadastre a subcategoria que falta antes de criar o produto (ou use o botão **+**).
- Produtos do tipo Defensivo Agrícola sem os campos de registro/classe toxicológica preenchidos aparecem incompletos nas recomendações do módulo MIP.

## Estoque (`/estoque/`)

### Visão geral

O módulo de Estoque controla armazéns, locais de estocagem, lotes e movimentações, e é o responsável por manter `Produto.estoque_atual` sempre correto. O sistema suporta **dois fluxos de atualização** que convivem lado a lado:

- **Fluxo com lote** (rastreabilidade completa) — usado quando o produto exige controle por lote (validade, número de lote, rastreamento PEPS/FIFO). A movimentação referencia um `Lote`; ao executá-la, o sistema atualiza a quantidade do lote e recalcula o estoque do produto como soma dos lotes disponíveis.
- **Fluxo direto** (entrada rápida, sem lote) — usado para produtos sem necessidade de rastreabilidade detalhada. A `MovimentacaoEstoque` é criada sem lote; o estoque do produto é recalculado automaticamente como `soma das entradas - soma das saídas`, sem precisar de uma etapa extra de execução.

### Conceitos principais

| Conceito | Papel |
|---|---|
| Armazém | Unidade física/organizacional onde o estoque é guardado |
| Local de Estocagem | Subdivisão de um armazém (prateleira, box, câmara fria); pode ser bloqueado |
| Lote | Quantidade de um produto com identidade própria (validade, número de lote); usado no fluxo rastreável |
| Movimentação de Estoque | Registro de entrada, saída, transferência ou ajuste; pode precisar de execução explícita |
| Inventário Cíclico | Contagem periódica programada para conferir o saldo físico contra o sistema |

Status de uma Movimentação: **Pendente** (criada, aguardando execução) → **Executada** (estoque atualizado). Toda movimentação que envolve lote (saída, transferência, ajuste) fica pendente até ser **executada** — a execução valida a quantidade disponível no lote de origem antes de efetivar a baixa. Já a entrada simples (sem lote) atualiza o estoque assim que é salva.

### Tela: Dashboard de Estoque

<figure>
  <img src="screenshots/estoque/01-dashboard.png" alt="Dashboard de Estoque">
  <figcaption>Indicadores gerais: valor em estoque, produtos com estoque baixo, movimentações recentes.</figcaption>
</figure>

### Tela: Estoque de Produtos

<figure>
  <img src="screenshots/estoque/02-produtos-estoque.png" alt="Estoque de Produtos">
  <figcaption>Visão de estoque por produto (`/estoque/produtos/`), com quantidade atual, mínima e máxima.</figcaption>
</figure>

### Tela: Lista de Armazéns

<figure>
  <img src="screenshots/estoque/03-armazens-lista.png" alt="Lista de Armazéns">
  <figcaption>Armazéns cadastrados (`/estoque/armazens/`).</figcaption>
</figure>

### Tela: Formulário de Novo Armazém

<figure>
  <img src="screenshots/estoque/16-armazem-form.png" alt="Formulário de Novo Armazém">
  <figcaption>Nome, tipo de armazém e se controla localização interna (locais de estocagem).</figcaption>
</figure>

### Tela: Detalhe do Armazém

<figure>
  <img src="screenshots/estoque/04-armazem-detalhe.png" alt="Detalhe de um Armazém">
  <figcaption>Locais de estocagem e lotes vinculados a um armazém específico.</figcaption>
</figure>

### Tela: Locais de Estocagem

<figure>
  <img src="screenshots/estoque/05-locais-lista.png" alt="Locais de Estocagem">
  <figcaption>Subdivisões de armazém (`/estoque/locais/`); podem ser bloqueados para impedir novas movimentações.</figcaption>
</figure>

### Tela: Lista de Lotes

<figure>
  <img src="screenshots/estoque/06-lotes-lista.png" alt="Lista de Lotes">
  <figcaption>Lotes ativos (`/estoque/lotes/`), com validade e quantidade atual.</figcaption>
</figure>

### Tela: Formulário de Novo Lote

<figure>
  <img src="screenshots/estoque/17-lote-form.png" alt="Formulário de Novo Lote">
  <figcaption>Produto, armazém/local, quantidade inicial, número do lote e validade.</figcaption>
</figure>

Normalmente um lote **não é criado manualmente aqui** — ele nasce automaticamente de um Recebimento de Compra ou de uma Entrada de Estoque com lote. Este formulário é usado só para casos excepcionais, como um saldo inicial de migração.

### Tela: Detalhe do Lote

<figure>
  <img src="screenshots/estoque/07-lote-detalhe.png" alt="Detalhe de um Lote">
  <figcaption>Histórico de movimentações de um lote específico — base do relatório de rastreamento.</figcaption>
</figure>

### Tela: Lista de Movimentações

<figure>
  <img src="screenshots/estoque/08-movimentacoes-lista.png" alt="Lista de Movimentações">
  <figcaption>Todas as movimentações (`/estoque/movimentacoes/`): entrada, saída, transferência, ajuste.</figcaption>
</figure>

### Tela: Detalhe da Movimentação

<figure>
  <img src="screenshots/estoque/09-movimentacao-detalhe.png" alt="Detalhe de uma Movimentação">
  <figcaption>Dados da movimentação e, quando pendente, o botão para executá-la ou cancelá-la.</figcaption>
</figure>

### Tela: Entrada de Estoque

<figure>
  <img src="screenshots/estoque/10-entrada.png" alt="Registrar Entrada">
  <figcaption>Formulário em 4 abas (Tipo e Origem, Produto e Quantidade, Lote, Informações Adicionais), com painel de dicas embutido.</figcaption>
</figure>

**Como preencher (aba Tipo e Origem)** — o próprio formulário traz um painel de dicas:

| Campo | Obrigatório | Descrição |
|---|---|---|
| Tipo | Sim | Entrada, Saída, Transferência ou Ajuste |
| Origem | Sim | Motivo da movimentação — ex: compra, produção própria, devolução de cliente |

O painel de dicas do sistema resume: use Entrada para **compras, produção própria e devoluções de clientes**; a entrada **aumenta a quantidade do lote selecionado** (quando houver lote); informe o **documento de referência** (NF, OP, etc.) na aba Informações Adicionais. Nas abas seguintes: **Produto e Quantidade** (o quê e quanto), **Lote** (se o produto controla lote, informe número/validade — ou deixe em branco para o fluxo direto).

### Tela: Saída de Estoque

<figure>
  <img src="screenshots/estoque/11-saida.png" alt="Registrar Saída">
  <figcaption>Mesma estrutura da Entrada, mas reduz a quantidade do lote/produto.</figcaption>
</figure>

### Tela: Transferência de Estoque

<figure>
  <img src="screenshots/estoque/12-transferencia.png" alt="Registrar Transferência">
  <figcaption>Move quantidade de um armazém/local/lote de origem para um de destino.</figcaption>
</figure>

**Como preencher:** escolha o lote/produto de **origem**, o armazém/local de **destino**, e a quantidade a mover. Diferente de entrada/saída simples, a transferência sempre precisa ser **executada** depois de criada — ela move saldo entre dois pontos, então o sistema valida disponibilidade na origem antes de efetivar.

### Fluxo passo a passo — registrar uma movimentação de estoque

1. Escolha o **Tipo** (Entrada/Saída/Transferência/Ajuste) e a **Origem/motivo**.
2. Informe o **produto e a quantidade**.
3. Se o produto controla lote, preencha os dados do **lote** (ou selecione um lote existente, no caso de saída/transferência).
4. Salve — movimentações **sem lote** já atualizam o estoque na hora; movimentações **com lote** (saída/transferência/ajuste) ficam **Pendentes** até você abrir o detalhe e clicar em **Executar**.
5. Confirme no **Estoque de Produtos** ou no **Detalhe do Lote** que a quantidade foi atualizada como esperado.

### Tela: Inventário Cíclico

<figure>
  <img src="screenshots/estoque/13-inventario-ciclico.png" alt="Inventário Cíclico">
  <figcaption>Contagens programadas (`/estoque/inventario-ciclico/`), com registro de contagem e conciliação de divergências.</figcaption>
</figure>

### Tela: Formulário de Novo Inventário Cíclico

<figure>
  <img src="screenshots/estoque/18-inventario-form.png" alt="Formulário de Novo Inventário Cíclico">
  <figcaption>Escopo da contagem: armazém, categoria de produto e data programada.</figcaption>
</figure>

### Fluxo passo a passo — inventário cíclico

1. Crie o inventário definindo o escopo (armazém e/ou categoria de produto) e a data.
2. No dia da contagem, abra o inventário e **registre a contagem física** de cada item.
3. O sistema compara a contagem com o saldo do sistema e aponta as **divergências**.
4. **Concilie** as divergências — isso gera automaticamente os ajustes de estoque necessários.
5. **Finalize** o inventário. O relatório de acurácia (menu Relatórios) usa esses dados para medir a precisão do estoque ao longo do tempo.

### Tela: Relatório de Alertas de Estoque

<figure>
  <img src="screenshots/estoque/14-relatorio-alertas.png" alt="Relatório de Alertas de Estoque">
  <figcaption>Produtos em estado crítico (saldo ≤ estoque mínimo) e em excesso, paginados, com opção de gerar solicitação de compra em lote.</figcaption>
</figure>

Um produto crítico que ainda não tem solicitação de compra em aberto pode ser marcado direto nesta tela para gerar uma nova Solicitação de Compra, unificando o alerta com a ação de repor o estoque.

### Tela: Análise ABC

<figure>
  <img src="screenshots/estoque/15-relatorio-abc.png" alt="Análise ABC">
  <figcaption>Classificação de produtos por relevância de valor em estoque (curva ABC).</figcaption>
</figure>

Há ainda outros relatórios avançados no menu Relatórios (comparativo entre períodos, auditoria, rastreamento de lote, validação de disponibilidade) que seguem o mesmo padrão de filtro por período/armazém/produto.

### Dicas e erros comuns

- Uma movimentação de **saída/transferência/ajuste** que não aparece refletida no estoque provavelmente ainda não foi **executada** — verifique o status na lista de movimentações.
- Um **local de estocagem bloqueado** não aceita novas movimentações; desbloqueie antes de tentar novamente.
- Relatórios como Alertas e Análise ABC podem demorar alguns segundos para carregar em bases com muitos produtos — isso é esperado, não é travamento.
- Divergências do inventário cíclico só se refletem no estoque depois de **conciliadas**; registrar a contagem sozinha não altera o saldo.

## Compras (`/compras/`)

### Visão geral

O módulo de Compras organiza a compra de insumos e materiais em três níveis de formalidade, que convivem no mesmo sistema:

- **Pedido direto** — compra rápida, sem cotação, para reposições simples e urgências de baixo valor.
- **Fluxo completo com cotação seletiva** — Solicitação de Compra (SC) → Cotação com múltiplos fornecedores → Pedido de Compra → Recebimento. É o caminho recomendado para compras de maior valor ou que exigem comparação de preços.
- **Entrada direta de NF-e** — importação do XML de uma nota fiscal do fornecedor diretamente para o estoque, pulando o fluxo de solicitação/pedido quando a compra já aconteceu por fora do sistema (ex: compra de balcão).

O ponto central do fluxo formal é a **cotação seletiva**: dentro de uma mesma Solicitação de Compra, o comprador pode escolher cotar só uma parte dos itens em cada rodada, permitindo cobrir os itens urgentes primeiro e deixar o restante para uma cotação seguinte.

### Conceitos e status

| Documento | Prefixo | Para que serve |
|---|---|---|
| Solicitação de Compra (SC) | `SC-000024` | Pedido interno de compra, feito por qualquer usuário autorizado |
| Cotação (COT) | vinculada à SC | Rodada de consulta de preço a um ou mais fornecedores |
| Pedido de Compra (PC) | gerado da cotação vencedora ou direto | Documento formal enviado ao fornecedor |
| Recebimento | vinculado ao PC | Conferência física da mercadoria + registro da nota fiscal |

Status de uma Solicitação de Compra, na ordem em que aparecem na coluna **Status** da listagem:

```
RASCUNHO → PENDENTE → APROVADA → PARCIALMENTE COTADA → TOTALMENTE COTADA → EM COMPRA → CONCLUÍDA
```

A coluna **% Cotado** na lista de solicitações mostra o percentual de itens da SC que já têm um fornecedor vencedor definido — 100% não significa que o pedido já foi feito, só que toda a SC já foi cotada.

Existe também um fluxo **emergencial**: ao marcar a solicitação como emergencial, ela pula a etapa `PENDENTE` e já nasce `APROVADA`, com o próprio solicitante como aprovador (exige justificativa). É pensado para quebra de equipamento ou falta de insumo crítico que não pode esperar aprovação formal — use com critério, pois hoje o sistema não limita quem pode marcar uma compra como emergencial por valor ou cargo.

### Tela: Dashboard de Compras

<figure>
  <img src="screenshots/compras/01-dashboard.png" alt="Dashboard de Compras">
  <figcaption>Painel com indicadores gerais de compras: solicitações em aberto, pedidos pendentes de recebimento e alertas.</figcaption>
</figure>

Ponto de partida do módulo (`/compras/dashboard-compras/`). Mostra de forma resumida quantas solicitações aguardam ação, quantos pedidos estão pendentes de recebimento e atalhos para as ações mais comuns.

### Tela: Lista de Solicitações de Compra

<figure>
  <img src="screenshots/compras/02-solicitacoes-lista.png" alt="Lista de Solicitações de Compra">
  <figcaption>Lista de solicitações (`/compras/solicitacoes/`), com número, solicitante, datas, status e % cotado.</figcaption>
</figure>

Cada linha é uma SC. O ícone de olho (👁) na coluna **Ações** abre o detalhe. O botão **Nova Solicitação**, no canto superior direito, inicia uma nova SC. O botão **Filtros** permite restringir a lista por período, status ou solicitante.

### Tela: Detalhe da Solicitação de Compra

<figure>
  <img src="screenshots/compras/03-solicitacao-detalhe.png" alt="Detalhe de uma Solicitação de Compra">
  <figcaption>Tela de detalhe de uma SC: itens solicitados, status individual de cada item e histórico.</figcaption>
</figure>

Aqui ficam os itens da solicitação, cada um com seu próprio status (`PENDENTE → SELECIONADO → EM_COTAÇÃO → COTADO → APROVADO`). É nesta tela que o comprador marca quais itens entram na próxima rodada de cotação, usando o checkbox de seleção e o botão **Cotar Selecionados**.

### Tela: Nova Solicitação de Compra

<figure>
  <img src="screenshots/compras/04-solicitacao-nova.png" alt="Formulário de Nova Solicitação de Compra">
  <figcaption>Formulário de criação de uma SC: itens, quantidades, data de necessidade e urgência.</figcaption>
</figure>

**Como preencher:**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Itens (produto, quantidade, unidade) | Sim (≥1 item) | Cada linha é um item a comprar |
| Data de Necessidade | Sim | Quando o material precisa estar disponível |
| Emergencial | Não | Se marcado, exige **Justificativa Emergencial** e pula a etapa de aprovação formal |
| Observações | Não | Contexto adicional para quem aprova/cota |

### Fluxo passo a passo — do pedido ao estoque

1. Um usuário abre uma **Solicitação de Compra** informando o que precisa e para quando.
2. Um aprovador aprova a SC (ou ela nasce aprovada, se marcada como emergencial).
3. O comprador seleciona os itens que quer cotar agora — não precisa ser todos de uma vez — e cria uma **Cotação**.
4. As propostas de cada fornecedor são lançadas item a item; o comprador escolhe o vencedor por item.
5. Ao concluir a cotação, o pedido de compra é gerado a partir dos itens vencedores.
6. O pedido é enviado ao fornecedor (e-mail, WhatsApp ou PDF).
7. Quando a mercadoria chega, o **Recebimento** é conferido contra o pedido; divergências (falta, sobra, avaria) são registradas.
8. Confirmado o recebimento, o estoque é atualizado automaticamente (gera lote, se aplicável) e — se houver NF vinculada — o lançamento financeiro (Conta a Pagar) é criado.

### Tela: Lista de Cotações

<figure>
  <img src="screenshots/compras/05-cotacoes-lista.png" alt="Lista de Cotações">
  <figcaption>Lista de cotações (`/compras/cotacoes/`), cada uma vinculada a uma SC.</figcaption>
</figure>

Cada cotação nasce de uma seleção de itens dentro de uma SC. Uma mesma SC pode gerar mais de uma cotação ao longo do tempo, se o comprador optar por cotar em rodadas separadas.

### Tela: Detalhe da Cotação (comparativo de fornecedores)

<figure>
  <img src="screenshots/compras/06-cotacao-detalhe.png" alt="Detalhe de uma Cotação">
  <figcaption>Comparativo de propostas de fornecedores por item, com seleção do vencedor.</figcaption>
</figure>

**Como preencher:** para cada item da cotação, use **Adicionar Proposta** e informe o fornecedor, preço, prazo de entrega e condição de pagamento. Repita para cada fornecedor consultado. Depois de lançadas as propostas, clique em **Selecionar** na proposta vencedora de cada item — isso desmarca automaticamente as demais propostas daquele item. Ao **Concluir** a cotação, o Pedido de Compra é gerado a partir dos itens com vencedor definido.

### Tela: Lista de Pedidos de Compra

<figure>
  <img src="screenshots/compras/07-pedidos-lista.png" alt="Lista de Pedidos de Compra">
  <figcaption>Pedidos de compra (`/compras/pedidos/`) gerados a partir de cotações concluídas ou de pedido direto.</figcaption>
</figure>

### Tela: Detalhe do Pedido de Compra

<figure>
  <img src="screenshots/compras/08-pedido-detalhe.png" alt="Detalhe de um Pedido de Compra">
  <figcaption>Detalhe do pedido: itens, fornecedor, valores e ações de envio/cancelamento/PDF.</figcaption>
</figure>

A partir daqui é possível enviar o pedido ao fornecedor (e-mail ou WhatsApp), gerar o PDF do pedido, cancelá-lo ou — quando a mercadoria chegar — iniciar o recebimento.

### Tela: Pedido Direto (compra rápida)

<figure>
  <img src="screenshots/compras/09-pedido-direto.png" alt="Formulário de Pedido Direto">
  <figcaption>Formulário de compra rápida: fornecedor, produtos, quantidades e preços, sem cotação.</figcaption>
</figure>

**Como preencher:** escolha o **Fornecedor**, adicione os **itens** (produto, quantidade, preço unitário) e salve — o Pedido de Compra é criado diretamente, sem passar por SC nem cotação. Use para reposições rotineiras de baixo risco, quando comparar preços de vários fornecedores não compensa o tempo gasto.

### Tela: Lista de Recebimentos

<figure>
  <img src="screenshots/compras/10-recebimentos-lista.png" alt="Lista de Recebimentos">
  <figcaption>Recebimentos (`/compras/recebimentos/`) — conferência física da mercadoria vinculada a um pedido.</figcaption>
</figure>

### Tela: Detalhe do Recebimento

<figure>
  <img src="screenshots/compras/11-recebimento-detalhe.png" alt="Detalhe de um Recebimento">
  <figcaption>Conferência de itens recebidos, registro de divergências e vínculo com a nota fiscal do fornecedor.</figcaption>
</figure>

**Como preencher:** para cada item do pedido, confira e informe a **quantidade efetivamente recebida** — se for diferente do pedido, registre o tipo de **divergência** (falta, sobra, avaria). Depois de conferir todos os itens, clique em **Entrada em Estoque** para gerar o(s) lote(s) e atualizar o saldo. Se houver nota fiscal do fornecedor, use **Faturar** para vincular a NF e gerar automaticamente a Conta a Pagar no Financeiro.

### Tela: Entrada Direta de NF-e

<figure>
  <img src="screenshots/compras/12-entrada-direta-nf.png" alt="Entrada Direta de NF-e">
  <figcaption>Importação do XML da nota fiscal do fornecedor direto para o estoque.</figcaption>
</figure>

Usada quando a compra já foi feita fora do fluxo de solicitação/pedido. Basta importar o XML da NF-e; o sistema lê os produtos e quantidades e permite vincular cada item da nota a um produto já cadastrado antes de lançar a entrada em estoque.

### Tela: Manifestação do Destinatário (MD-e)

<figure>
  <img src="screenshots/compras/13-mde-lista.png" alt="Manifestação do Destinatário">
  <figcaption>Lista de notas fiscais recebidas de fornecedores pendentes de manifestação junto à SEFAZ.</figcaption>
</figure>

Toda NF-e emitida contra o CNPJ da empresa precisa ser "manifestada" perante a SEFAZ (confirmar ciência, confirmar a operação, ou declarar desconhecimento/operação não realizada). Esta tela reúne as notas pendentes dessa manifestação — o mesmo conjunto de notas que aparece na Distribuição de DF-e do módulo Faturamento.

### Tela: Planejamento de Embalagens

<figure>
  <img src="screenshots/compras/14-planejamento-embalagem.png" alt="Planejamento de Embalagens">
  <figcaption>Planejamento de compra de embalagens com base na previsão de uso.</figcaption>
</figure>

### Tela: Relatório Geral de Compras

<figure>
  <img src="screenshots/compras/15-relatorio-geral.png" alt="Relatório Geral de Compras">
  <figcaption>Visão consolidada de compras por período, fornecedor e status.</figcaption>
</figure>

### Dicas e erros comuns

- Uma SC com **% Cotado** menor que 100% ainda tem itens pendentes de uma rodada de cotação — não é um erro, é esperado em cotação seletiva com múltiplas rodadas.
- Uma solicitação **Cancelada** não pode voltar a tramitar; é preciso abrir uma nova.
- A **Entrada Direta de NF-e** não substitui o fluxo formal quando já existe um Pedido de Compra em aberto para aquele fornecedor — use-a só para compras que não passaram pelo fluxo de solicitação.
- Notas pendentes de **manifestação** por muito tempo podem gerar bloqueios fiscais; vale revisar a tela de MD-e periodicamente.
