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

A maior parte das Contas a Pagar nasce automaticamente do módulo de **Compras**, no momento em que a nota fiscal do fornecedor é registrada no Recebimento — por isso este módulo funciona como o destino natural do fluxo de compras.

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

Uma conta com saldo residual pequeno pode ser **quitada** diretamente (ação de renegociação), ajustando o valor e mudando o status para `RENEGOCIADA`, em vez de manter uma parcela pendente por centavos.

### Tela: Agenda de Pagamentos

<figure>
  <img src="screenshots/financeiro/04-parcelas-lista.png" alt="Agenda de Pagamentos">
  <figcaption>Lista de parcelas (`/financeiro/parcelas/`) — diferente da lista de Contas a Pagar, que mostra os documentos, não as parcelas individuais.</figcaption>
</figure>

Esta é a tela do dia a dia de quem paga contas: mostra cada parcela isoladamente, com data de vencimento, para decidir o que pagar primeiro.

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

### Tela: Fluxo de Caixa

<figure>
  <img src="screenshots/financeiro/07-fluxo-caixa.png" alt="Fluxo de Caixa">
  <figcaption>Projeção de entradas e saídas por período, cruzando Contas a Pagar e a Receber.</figcaption>
</figure>

### Dicas e erros comuns

- Antes de pagar uma parcela em atraso, use o recálculo de juros/multa — o valor exibido pode estar desatualizado até esse passo.
- Sempre use o valor em **BRL** ao somar contas a receber em moeda estrangeira; o valor na moeda original não é comparável entre contas de moedas diferentes.
- Uma Conta a Pagar com `requer_aprovacao=True` não deixa registrar pagamento antes de ser aprovada.

## Plano de Contas (`/plano-contas/`)

### Visão geral

Estrutura hierárquica de contas contábeis (ex: Receitas → Receita de Vendas → Vendas de Frutas) e centros de custo, usada para classificar manualmente lançamentos financeiros e para gerar o balancete. A classificação **não é automática** — o usuário escolhe a conta contábil/centro de custo ao lançar uma Conta a Pagar ou a Receber.

### Tela: Contas Contábeis

<figure>
  <img src="screenshots/plano_contas/01-lista.png" alt="Contas Contábeis">
  <figcaption>Lista de contas cadastradas (`/plano-contas/`).</figcaption>
</figure>

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

### Dicas e erros comuns

- O plano de contas padrão pode ser gerado via comando `seed_plano_contas` (101 contas de referência) e depois ajustado conforme a necessidade da empresa.

## Contas Bancárias (`/bancario/`)

### Visão geral

Gerencia as contas bancárias da empresa e a conciliação bancária: importação de extrato (OFX/CNAB) e comparação automática com os lançamentos do sistema, com sugestões de correspondência.

### Tela: Contas Bancárias

<figure>
  <img src="screenshots/bancario/01-contas-lista.png" alt="Contas Bancárias">
  <figcaption>Contas bancárias cadastradas (`/bancario/contas/`).</figcaption>
</figure>

### Tela: Detalhe da Conta Bancária

<figure>
  <img src="screenshots/bancario/02-conta-detalhe.png" alt="Detalhe de uma Conta Bancária">
  <figcaption>Extrato importado e histórico de conciliação da conta.</figcaption>
</figure>

A importação do extrato (botão na própria conta) aceita arquivos OFX/CNAB; após importar, a **conciliação** compara cada linha do extrato com os lançamentos do sistema e sugere pares prováveis, que podem ser confirmados, ignorados ou desfeitos.

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

### Tela: Detalhe do Adiantamento

<figure>
  <img src="screenshots/adiantamentos/02-detalhe.png" alt="Detalhe de um Adiantamento">
  <figcaption>Valor em moeda estrangeira e convertido, regra de desconto e histórico de descontos aplicados por embarque.</figcaption>
</figure>

A cada embarque/invoice do cliente, é possível **aplicar o desconto** programado (valor fixo ou percentual) ou **pular** o desconto daquele embarque específico, mantendo o saldo do adiantamento para os próximos.

### Tela: Relatório de Adiantamentos

<figure>
  <img src="screenshots/adiantamentos/03-relatorio.png" alt="Relatório de Adiantamentos">
  <figcaption>Posição consolidada de adiantamentos por cliente/safra e saldo remanescente.</figcaption>
</figure>

### Dicas e erros comuns

- Um adiantamento não quitado até o fim da safra deve ser **migrado**, não cancelado — isso preserva o saldo e o histórico para a safra seguinte.
- O valor de referência para relatórios é sempre o **convertido em BRL** pela taxa de câmbio acordada, não o valor na moeda estrangeira.
