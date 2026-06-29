# Módulo Financeiro — Guia para Desenvolvedores

## Visão geral

O módulo financeiro cobre o ciclo completo de **contas a pagar (AP)** e **contas a receber (AR)**. Os submodelos implementam parcelamento, registro de pagamentos e recebimentos, ajustes e renegociação.

---

## Hierarquia de modelos

```
ContaPagar
  └─ ParcelaContaPagar (1..N)
       └─ PagamentoContaPagar (0..N)

ContaReceber
  └─ ParcelaContaReceber (1..N)
       └─ RecebimentoContaReceber (0..N)
```

### ContaPagar
Representa o documento financeiro a pagar (boleto, NF de fornecedor, etc.).
- Gerada manualmente ou via `RecebimentoCompra` (OneToOne opcional → `compras.RecebimentoCompra`).
- Campos monetários: `valor_total`, `valor_ajustado`, `desconto_negociado`, `juros_acumulados`, `multa_acumulada`.
- Status: `ABERTA → APROVADA → PAGA | CANCELADA | RENEGOCIADA`
- `requer_aprovacao`: quando `True`, a conta precisa ser aprovada antes de poder ser paga.
- `conta_contabil` / `centro_custo`: FK opcional para `plano_contas.ContaContabil` / `plano_contas.CentroCusto`. Preenchidos manualmente — **não são automáticos**.

### ParcelaContaPagar
Cada linha de vencimento de uma `ContaPagar`. Uma conta pode ter N parcelas.
- Campos: `numero_parcela`, `valor_parcela`, `data_vencimento`, `valor_total_parcela`.
- Juros e multas **não são automáticos** — chamar `parcela.recalcular_total()` antes de exibir valores atualizados, ou acionar via view `recalcular_juros` (URL `financeiro:recalcular_juros`).
- Status: `ABERTA | VENCIDA | PAGA | RENEGOCIADA | CANCELADA`

### PagamentoContaPagar
Registro de cada pagamento aplicado a uma parcela.
- `forma_pagamento` é CharField (não FK) — limitação conhecida.
- `conta_bancaria`: FK opcional para `bancario.ContaBancaria`.

### ContaReceber
Representa valores a receber do cliente.
- Criada a partir de: `vendas.PedidoVenda` (OneToOne opcional), `faturamento.NotaFiscal`, `faturamento.InvoiceExportacao` ou manualmente.
- Dual-currency: `valor_moeda` + `taxa_cambio` → `valor_brl`. **Sempre usar `valor_brl` para agregações**.
- Status: `ABERTA | PARCIALMENTE_PAGA | PAGA | VENCIDA | CANCELADA`
- `conta_contabil` / `centro_custo`: FK opcional — mesma limitação de CP.

---

## O que é a "Agenda de Pagamentos"

A página **Agenda de Pagamentos** (`financeiro:parcela_list`) lista as `ParcelaContaPagar`. É diferente de "Contas a Pagar" (`financeiro:conta_pagar_list`) que lista os documentos (`ContaPagar`). Use a Agenda para:
- Ver o que vence hoje / essa semana.
- Registrar o pagamento de uma parcela individual.

---

## Fluxo de uso típico

1. Chega NF do fornecedor → criar `ContaPagar` → sistema cria parcelas automaticamente.
2. Próximo do vencimento → ver na **Agenda de Pagamentos** (filtrar por `?vencimento=proximas_7`).
3. Registrar pagamento → `parcela_pagar` → cria `PagamentoContaPagar` e atualiza status da parcela.
4. Quando todas parcelas estão pagas → status da `ContaPagar` muda para `PAGA`.

---

## Plano de Contas e Centro de Custo

- `ContaContabil` e `CentroCusto` são cadastrados em `plano_contas/`.
- `ContaPagar` e `ContaReceber` têm FK **opcional** para ambos. O usuário preenche manualmente na criação/edição da conta.
- **Gap conhecido**: `PedidoVenda` e `PedidoCompra` **não possuem** FK para `CentroCusto` nem `ContaContabil`. Não há classificação automática por centro de custo na operação comercial. Para relatórios gerenciais, o preenchimento deve ser feito nas CPs/CRs geradas.

---

## Juros e Multas

Calculados em `ParcelaContaPagar.recalcular_total()`:
- Não são recalculados automaticamente a cada requisição.
- A view `recalcular_juros_multas` (URL `financeiro:recalcular_juros`, POST) recalcula para uma conta específica.
- Para exibir valores corretos, chamar antes de renderizar (ou confiar no valor armazenado que é recalculado quando a parcela é aberta para edição).

---

## Renegociação

`ContaPagar` pode ser renegociada via `conta_quitar_saldo` (URL `financeiro:conta_quitar_saldo`), que quita o saldo com ajuste de valor. Status muda para `RENEGOCIADA`.

---

## Convenções de migration

Migrations do módulo `financeiro` usam prefixo `10000_` para evitar conflito de numeração com o arquivo inicial `0001_initial.py` que veio de outros apps. Exemplo: `10000_add_campo_x.py`.

Migrations que dependem de `plano_contas` devem incluir:
```python
dependencies = [
    ('plano_contas', '0001_initial'),
]
```

---

## Mapa de URLs

| URL name | Método | Propósito |
|---|---|---|
| `financeiro:dashboard` | GET | Hub central — AP + AR + posição líquida |
| `financeiro:conta_pagar_list` | GET | Lista de ContaPagar com filtros (`?periodo=vencidas\|proximas\|30dias\|todos`) |
| `financeiro:conta_pagar_detail` | GET | Detalhe com parcelas e pagamentos |
| `financeiro:conta_pagar_create` | GET/POST | Criar nova CP |
| `financeiro:conta_pagar_edit` | GET/POST | Editar CP (só status ABERTA) |
| `financeiro:conta_pagar_aprovar` | POST | Aprovar CP (requer_aprovacao=True) |
| `financeiro:parcela_list` | GET | Agenda de Pagamentos (ParcelaContaPagar) |
| `financeiro:parcela_criar` | GET/POST | Criar parcelas manualmente para uma CP |
| `financeiro:parcela_pagar` | GET/POST | Registrar pagamento de uma parcela |
| `financeiro:pagamento_retornar_pendente` | POST | Reverter pagamento para pendente |
| `financeiro:conta_quitar_saldo` | GET/POST | Quitar saldo restante (renegociação) |
| `financeiro:ajuste_criar` | GET/POST | Criar ajuste de valor em CP |
| `financeiro:recalcular_juros` | POST | Recalcular juros/multas de uma CP |
| `financeiro:relatorio_contas_vencer` | GET | Relatório detalhado de parcelas a vencer (30d) |
| `financeiro:relatorio_contas_vencidas` | GET | Relatório detalhado de parcelas vencidas |
| `financeiro:relatorio_fluxo_caixa` | GET | Fluxo de caixa projetado |
| `financeiro:conta_receber_list` | GET | Lista de ContaReceber |
| `financeiro:conta_receber_create` | GET/POST | Criar nova CR manualmente |
| `financeiro:conta_receber_detail` | GET | Detalhe com parcelas de CR |
| `financeiro:conta_receber_cancelar` | POST | Cancelar CR |
| `financeiro:parcela_receber_registrar` | GET/POST | Registrar recebimento de parcela de CR |
