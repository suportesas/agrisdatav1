# Financeiro & Fiscal

## Cadastros Fiscais (`/cadastros/`)

### Visão geral

NCM e CFOP são tabelas fiscais de referência usadas na emissão de notas fiscais e no cadastro de produtos. Normalmente são importadas em lote (arquivo oficial da Receita/SEFAZ) e depois só consultadas — não é comum cadastrar item a item manualmente.

### Tela: Lista de NCM

<figure>
  <img src="screenshots/cadastros_fiscal/01-ncm-lista.png" alt="Lista de NCM">
  <figcaption>Códigos NCM cadastrados (`/cadastros/ncm/`), com opção de importação em massa.</figcaption>
</figure>

### Tela: Lista de CFOP

<figure>
  <img src="screenshots/cadastros_fiscal/02-cfop-lista.png" alt="Lista de CFOP">
  <figcaption>Códigos CFOP cadastrados (`/cadastros/cfop/`), usados para definir a natureza fiscal de cada operação.</figcaption>
</figure>

### Dicas e erros comuns

- Prefira sempre **importar** a tabela oficial de NCM/CFOP em vez de cadastrar manualmente, para evitar divergência com a tabela usada pela SEFAZ.

## Financeiro (`/financeiro/`)

### Visão geral

Controla o ciclo completo de **Contas a Pagar** e **Contas a Receber**. A hierarquia de cada lado é a mesma: um documento principal, dividido em parcelas, cada parcela podendo ter um ou mais pagamentos/recebimentos registrados.

```
ContaPagar
  └─ ParcelaContaPagar (1..N)
       └─ PagamentoContaPagar (0..N)

ContaReceber
  └─ ParcelaContaReceber (1..N)
       └─ RecebimentoContaReceber (0..N)
```

### Conceitos e status

Uma **Conta a Pagar** segue o ciclo `ABERTA → APROVADA → PAGA` (ou `CANCELADA`/`RENEGOCIADA`). Se marcada como `requer_aprovacao`, fica bloqueada para pagamento até ser aprovada. Cada parcela tem seu próprio status (`ABERTA | VENCIDA | PAGA | RENEGOCIADA | CANCELADA`) e os juros/multa de atraso **não são recalculados automaticamente** — é preciso acionar o recálculo (botão na tela da conta) para atualizar o valor devido antes de registrar o pagamento.

Uma **Conta a Receber** pode nascer de um Pedido de Venda, de uma Nota Fiscal, de uma Invoice de Exportação, ou ser lançada manualmente — e suporta moeda estrangeira (valor na moeda + taxa de câmbio, convertido para BRL).

A maior parte das Contas a Pagar nasce automaticamente do módulo de **Compras**, no momento em que a nota fiscal do fornecedor é registrada no Recebimento (botão **Faturar**) — por isso este módulo funciona como o destino natural do fluxo de compras. Mesmo assim, é possível lançar uma Conta a Pagar manualmente (despesas que não vêm de uma compra de produto, como serviços ou aluguel).

### Tela: Dashboard Financeiro

<figure>
  <img src="screenshots/financeiro/01-dashboard.png" alt="Dashboard Financeiro">
  <figcaption>Posição consolidada: total a pagar, a receber e saldo líquido projetado.</figcaption>
</figure>

### Tela: Contas a Pagar

<figure>
  <img src="screenshots/financeiro/02-contas-pagar-lista.png" alt="Contas a Pagar">
  <figcaption>Lista de documentos de Contas a Pagar (`/financeiro/contas/`), filtrável por período (vencidas/próximas/30 dias/todas).</figcaption>
</figure>

### Tela: Detalhe da Conta a Pagar

<figure>
  <img src="screenshots/financeiro/03-conta-pagar-detalhe.png" alt="Detalhe de uma Conta a Pagar">
  <figcaption>Parcelas, pagamentos registrados, e ações de aprovação, recálculo de juros e quitação de saldo.</figcaption>
</figure>

### Tela: Formulário de Nova Conta a Pagar

<figure>
  <img src="screenshots/financeiro/08-conta-pagar-form.png" alt="Formulário de Nova Conta a Pagar">
  <figcaption>Formulário em 5 abas: Identificação, Valores, Parcelamento Automático, Configurações, Observações.</figcaption>
</figure>

**Como preencher (aba Identificação):**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Número | Sim | Número/referência da conta (ex: número da NF ou do contrato) |
| Fornecedor | Sim | Busca com autocomplete |
| Data de Emissão | Sim | Pré-preenchida com a data atual |
| Empresa | Sim | Pré-preenchida com a empresa do usuário logado |

Na aba **Valores**, informe o valor total da conta e, se aplicável, conta contábil/centro de custo (classificação gerencial manual). Na aba **Parcelamento Automático**, defina em quantas parcelas dividir e a periodicidade — o sistema gera as `ParcelaContaPagar` automaticamente a partir dessa regra, sem precisar criar cada parcela manualmente. **Configurações** define se a conta `requer_aprovacao` antes de poder ser paga. **Observações** é texto livre.

### Fluxo passo a passo — lançar e pagar uma conta manualmente

1. Preencha Identificação + Valores e defina o parcelamento (ex: 3x mensal).
2. Salve — a conta nasce **Aberta**, com as parcelas já geradas conforme o parcelamento.
3. Se a conta exige aprovação, um aprovador precisa **aprovar** antes do próximo passo.
4. Na **Agenda de Pagamentos**, localize a parcela e registre o **pagamento** (valor, data, conta bancária de origem, forma de pagamento).
5. Quando todas as parcelas estiverem pagas, a conta muda automaticamente para **Paga**.

### Tela: Agenda de Pagamentos

<figure>
  <img src="screenshots/financeiro/04-parcelas-lista.png" alt="Agenda de Pagamentos">
  <figcaption>Lista de parcelas (`/financeiro/parcelas/`) — diferente da lista de Contas a Pagar, que mostra os documentos, não as parcelas individuais.</figcaption>
</figure>

Esta é a tela do dia a dia de quem paga contas: mostra cada parcela isoladamente, com data de vencimento, para decidir o que pagar primeiro. Clique numa parcela para **registrar o pagamento** — se ela estiver vencida, use antes o botão de **recalcular juros/multa** para atualizar o valor devido.

### Tela: Contas a Receber

<figure>
  <img src="screenshots/financeiro/05-contas-receber-lista.png" alt="Contas a Receber">
  <figcaption>Lista de Contas a Receber (`/financeiro/contas-receber/`).</figcaption>
</figure>

### Tela: Detalhe da Conta a Receber

<figure>
  <img src="screenshots/financeiro/06-conta-receber-detalhe.png" alt="Detalhe de uma Conta a Receber">
  <figcaption>Parcelas e recebimentos registrados; suporta valores em moeda estrangeira convertidos para BRL.</figcaption>
</figure>

### Tela: Formulário de Nova Conta a Receber

<figure>
  <img src="screenshots/financeiro/09-conta-receber-form.png" alt="Formulário de Nova Conta a Receber">
  <figcaption>Cliente, valor (com suporte a moeda estrangeira) e parcelamento.</figcaption>
</figure>

**Como preencher:** estrutura equivalente à Conta a Pagar, trocando Fornecedor por **Cliente**. Se o valor for em moeda estrangeira, informe a **taxa de câmbio** — o sistema calcula o valor em BRL automaticamente e é esse valor convertido que deve ser usado em qualquer agregação/relatório.

### Tela: Fluxo de Caixa

<figure>
  <img src="screenshots/financeiro/07-fluxo-caixa.png" alt="Fluxo de Caixa">
  <figcaption>Projeção de entradas e saídas por período, cruzando Contas a Pagar e a Receber.</figcaption>
</figure>

### Dicas e erros comuns

- Antes de pagar uma parcela em atraso, use o recálculo de juros/multa — o valor exibido pode estar desatualizado até esse passo.
- Sempre use o valor em **BRL** ao somar contas a receber em moeda estrangeira; o valor na moeda original não é comparável entre contas de moedas diferentes.
- Uma Conta a Pagar com `requer_aprovacao=True` não deixa registrar pagamento antes de ser aprovada.
- Prefira o **Parcelamento Automático** a criar parcelas uma a uma — reduz erro de digitação nas datas de vencimento.

## Plano de Contas (`/plano-contas/`)

### Visão geral

Estrutura hierárquica de contas contábeis (ex: Receitas → Receita de Vendas → Vendas de Frutas) e centros de custo, usada para classificar manualmente lançamentos financeiros e para gerar o balancete. A classificação **não é automática** — o usuário escolhe a conta contábil/centro de custo ao lançar uma Conta a Pagar ou a Receber.

### Tela: Contas Contábeis

<figure>
  <img src="screenshots/plano_contas/01-lista.png" alt="Contas Contábeis">
  <figcaption>Lista de contas cadastradas (`/plano-contas/`).</figcaption>
</figure>

### Tela: Formulário de Nova Conta Contábil

<figure>
  <img src="screenshots/plano_contas/05-conta-form.png" alt="Formulário de Nova Conta Contábil">
  <figcaption>Código, nome, tipo (Receita/Despesa/Ativo/Passivo) e conta pai (para montar a hierarquia).</figcaption>
</figure>

**Como preencher:** informe o **código** (segue a convenção contábil da empresa), **nome** da conta, **tipo** e, se for uma subconta, a **conta pai** — é essa hierarquia que aparece na Árvore do Plano de Contas.

### Tela: Árvore do Plano de Contas

<figure>
  <img src="screenshots/plano_contas/02-arvore.png" alt="Árvore do Plano de Contas">
  <figcaption>Visualização hierárquica das contas contábeis.</figcaption>
</figure>

### Tela: Balancete

<figure>
  <img src="screenshots/plano_contas/03-balancete.png" alt="Balancete">
  <figcaption>Saldo consolidado por conta contábil em um período.</figcaption>
</figure>

### Tela: Centros de Custo

<figure>
  <img src="screenshots/plano_contas/04-centros-custo.png" alt="Centros de Custo">
  <figcaption>Centros de custo cadastrados (`/plano-contas/centros/`), usados para segmentar o resultado por área/projeto.</figcaption>
</figure>

### Tela: Formulário de Novo Centro de Custo

<figure>
  <img src="screenshots/plano_contas/06-centro-custo-form.png" alt="Formulário de Novo Centro de Custo">
  <figcaption>Código e nome do centro de custo.</figcaption>
</figure>

### Dicas e erros comuns

- O plano de contas padrão pode ser gerado via comando `seed_plano_contas` (101 contas de referência) e depois ajustado conforme a necessidade da empresa.
- Defina o plano de contas e os centros de custo **antes** de começar a lançar Contas a Pagar/Receber em volume — reclassificar depois é trabalhoso.

## Contas Bancárias (`/bancario/`)

### Visão geral

Gerencia as contas bancárias da empresa e a conciliação bancária: importação de extrato (OFX/CNAB) e comparação automática com os lançamentos do sistema, com sugestões de correspondência.

### Tela: Contas Bancárias

<figure>
  <img src="screenshots/bancario/01-contas-lista.png" alt="Contas Bancárias">
  <figcaption>Contas bancárias cadastradas (`/bancario/contas/`).</figcaption>
</figure>

### Tela: Formulário de Nova Conta Bancária

<figure>
  <img src="screenshots/bancario/04-conta-form.png" alt="Formulário de Nova Conta Bancária">
  <figcaption>Banco, agência, número da conta e saldo inicial.</figcaption>
</figure>

**Como preencher:** informe o banco, agência, número da conta e o **saldo inicial** (data de referência) — a partir daí, todo pagamento/recebimento vinculado a essa conta e cada item de extrato conciliado ajustam o saldo corrente.

### Tela: Detalhe da Conta Bancária

<figure>
  <img src="screenshots/bancario/02-conta-detalhe.png" alt="Detalhe de uma Conta Bancária">
  <figcaption>Extrato importado e histórico de conciliação da conta.</figcaption>
</figure>

### Fluxo passo a passo — conciliação bancária

1. Na tela da conta, use **Importar Extrato** e selecione o arquivo OFX/CNAB do banco.
2. Abra a **Conciliação** dessa importação — o sistema já sugere pares prováveis entre linhas do extrato e lançamentos do sistema.
3. Para cada sugestão, **confirme** (se estiver correta) ou **ignore** (se não houver correspondência real).
4. Itens sem sugestão automática podem ser conciliados **manualmente**, buscando o lançamento correspondente.
5. Um item confirmado por engano pode ser **desfeito**, voltando para pendente.

### Tela: Relatório de Conciliação

<figure>
  <img src="screenshots/bancario/03-relatorio-conciliacao.png" alt="Relatório de Conciliação">
  <figcaption>Resumo de itens conciliados, pendentes e ignorados por período.</figcaption>
</figure>

### Dicas e erros comuns

- Uma conciliação **desfeita** volta o item para pendente — útil quando uma sugestão automática foi confirmada por engano.

## Adiantamentos Internacionais (`/adiantamentos/`)

### Visão geral

Controla adiantamentos recebidos de clientes internacionais antes do embarque de uma exportação, em moeda estrangeira, com desconto programado a cada embarque (valor fixo ou percentual da invoice) até a quitação. Um adiantamento não descontado até o fim da safra pode ser **migrado** para a safra seguinte.

### Status

```
PENDENTE_EMBARQUE → EM_ANDAMENTO → PARCIALMENTE_QUITADO → QUITADO
```
(ou `MIGRADO` / `CANCELADO`)

### Tela: Lista de Adiantamentos

<figure>
  <img src="screenshots/adiantamentos/01-lista.png" alt="Lista de Adiantamentos Internacionais">
  <figcaption>Adiantamentos registrados (`/adiantamentos/`), por cliente e safra de referência.</figcaption>
</figure>

### Tela: Formulário de Novo Adiantamento

<figure>
  <img src="screenshots/adiantamentos/04-adiantamento-form.png" alt="Formulário de Novo Adiantamento">
  <figcaption>Cliente, safra de referência, valor em moeda estrangeira e regra de desconto por embarque.</figcaption>
</figure>

**Como preencher:**

| Campo | Obrigatório | Descrição |
|---|---|---|
| Cliente | Sim | Cliente internacional |
| Safra (Referência) | Sim | Texto livre, ex: "2026/2027" |
| Número de Referência/Contrato | Sim | Identificação do adiantamento |
| Data do Adiantamento | Sim | |
| Moeda / Valor Estrangeiro | Sim | Valor recebido na moeda original |
| Taxa de Câmbio Acordada | Sim | Usada para calcular o Valor em BRL |
| Tipo de Regra de Desconto | Sim | Valor Fixo por Embarque ou Percentual do Valor da Invoice |
| Valor/Percentual de Desconto | Sim (conforme regra) | Quanto descontar a cada embarque |
| Data Prevista de Reembolso | Não | Estimativa de quando o adiantamento será totalmente descontado |

### Tela: Detalhe do Adiantamento

<figure>
  <img src="screenshots/adiantamentos/02-detalhe.png" alt="Detalhe de um Adiantamento">
  <figcaption>Valor em moeda estrangeira e convertido, regra de desconto e histórico de descontos aplicados por embarque.</figcaption>
</figure>

### Fluxo passo a passo — usar um adiantamento até a quitação

1. Registre o adiantamento recebido, com a regra de desconto (fixo ou percentual).
2. A cada embarque/invoice do cliente, abra o adiantamento e **aplique o desconto** programado — ou **pule** o desconto daquele embarque específico, mantendo o saldo para os próximos.
3. Acompanhe o status: de `EM_ANDAMENTO` evolui para `PARCIALMENTE_QUITADO` conforme os descontos são aplicados, até `QUITADO`.
4. Se a safra terminar com saldo não descontado, use **Migrar** para transferir o saldo para a safra seguinte em vez de deixar em aberto indefinidamente.

### Tela: Relatório de Adiantamentos

<figure>
  <img src="screenshots/adiantamentos/03-relatorio.png" alt="Relatório de Adiantamentos">
  <figcaption>Posição consolidada de adiantamentos por cliente/safra e saldo remanescente.</figcaption>
</figure>

### Dicas e erros comuns

- Um adiantamento não quitado até o fim da safra deve ser **migrado**, não cancelado — isso preserva o saldo e o histórico para a safra seguinte.
- O valor de referência para relatórios é sempre o **convertido em BRL** pela taxa de câmbio acordada, não o valor na moeda estrangeira.
