Owner: Time financeiro
Status: Approved
Last Updated: 2026-07-10
Scope: financeiro (`/financeiro/`)

# Módulo Financeiro

## Visão geral
Ciclo completo de **contas a pagar (AP)** e **contas a receber (AR)**: parcelamento, registro de pagamentos/recebimentos, ajustes e renegociação. Guia técnico completo para desenvolvedores em `financeiro/CLAUDE.md` — este documento resume o essencial; consulte o CLAUDE.md do app para detalhes de implementação.

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
Documento financeiro a pagar. Gerada manualmente ou via `RecebimentoCompra` (FK OneToOne opcional → `compras.RecebimentoCompra`, ver `docs/2_MODULOS/MODULO_COMPRAS.md` e `docs/3_FLUXOS_PROCESSOS/FLUXO_COMPRA_FINANCEIRO.md`).
- Status: `ABERTA → APROVADA → PAGA | CANCELADA | RENEGOCIADA`
- `requer_aprovacao=True` bloqueia pagamento até aprovação.
- `conta_contabil`/`centro_custo` (FK opcional para `plano_contas`) são **preenchidos manualmente** — não há classificação automática por centro de custo vinda da operação comercial (`PedidoVenda`/`PedidoCompra` não têm essas FKs).

### ParcelaContaPagar
Linha de vencimento de uma `ContaPagar`. Juros/multa **não recalculam automaticamente a cada request** — chamar `parcela.recalcular_total()` ou a view `financeiro:recalcular_juros` (POST). Status: `ABERTA | VENCIDA | PAGA | RENEGOCIADA | CANCELADA`.

### PagamentoContaPagar
Registro de pagamento aplicado a uma parcela. `forma_pagamento` é `CharField` (não FK — limitação conhecida). `conta_bancaria` é FK opcional para `bancario.ContaBancaria`.

### ContaReceber
Valores a receber do cliente — criada a partir de `vendas.PedidoVenda`, `faturamento.NotaFiscal`, `faturamento.InvoiceExportacao` ou manualmente. Suporta moeda dupla: `valor_moeda` + `taxa_cambio` → `valor_brl` (**sempre usar `valor_brl` em agregações**). Status: `ABERTA | PARCIALMENTE_PAGA | PAGA | VENCIDA | CANCELADA`.

## Fluxo típico
1. NF do fornecedor chega → `ContaPagar` criada (manual ou automática) → parcelas geradas.
2. Vencimento próximo → **Agenda de Pagamentos** (`financeiro:parcela_list`, lista `ParcelaContaPagar` — diferente de "Contas a Pagar" que lista os documentos `ContaPagar`).
3. Pagamento registrado (`parcela_pagar`) → cria `PagamentoContaPagar`, atualiza status da parcela.
4. Todas as parcelas pagas → `ContaPagar.status = PAGA`.

## Renegociação
`conta_quitar_saldo` (`financeiro:conta_quitar_saldo`) quita o saldo remanescente com ajuste de valor; status muda para `RENEGOCIADA`.

## Rotas principais (`/financeiro/`)
| URL name | Método | Propósito |
|---|---|---|
| `dashboard` | GET | Hub central — AP + AR + posição líquida |
| `conta_pagar_list` | GET | Lista de CP (`?periodo=vencidas\|proximas\|30dias\|todos`) |
| `conta_pagar_create` / `conta_pagar_edit` | GET/POST | Criar/editar CP (edição só em `ABERTA`) |
| `conta_pagar_aprovar` | POST | Aprovar CP (`requer_aprovacao=True`) |
| `parcela_list` | GET | Agenda de Pagamentos |
| `parcela_pagar` | GET/POST | Registrar pagamento de parcela |
| `pagamento_retornar_pendente` | POST | Reverter pagamento |
| `conta_quitar_saldo` | GET/POST | Renegociação |
| `ajuste_criar` | GET/POST | Ajuste de valor em CP |
| `recalcular_juros` | POST | Recalcula juros/multas de uma CP |
| `relatorio_contas_vencer` / `relatorio_contas_vencidas` / `relatorio_fluxo_caixa` | GET | Relatórios |
| `conta_receber_list` / `conta_receber_create` / `conta_receber_detail` / `conta_receber_cancelar` | — | CRUD de CR |
| `parcela_receber_registrar` | GET/POST | Registrar recebimento de parcela de CR |

## Convenções de migration
Migrações do app usam prefixo `10000_` (evita conflito com `0001_initial.py`). Migrações que dependem de `plano_contas` devem declarar `dependencies = [('plano_contas', '0001_initial')]`.

## Gaps conhecidos
- `PedidoVenda`/`PedidoCompra` sem FK de centro de custo/conta contábil — classificação gerencial só existe pós-geração da CP/CR.
- Juros/multa exigem recálculo explícito (não são "sempre corretos" sem chamar a rotina).
- `PagamentoContaPagar.forma_pagamento` não é normalizado (FK), é texto livre.

## Referências
- `financeiro/models.py`, `financeiro/urls.py`, `financeiro/CLAUDE.md` (guia completo para desenvolvedores, mantido no app)
- `docs/3_FLUXOS_PROCESSOS/FLUXO_COMPRA_FINANCEIRO.md`
