Owner: Processos
Status: Approved
Last Updated: 2026-07-10
Scope: Compras, recebimento e contas a pagar

# Fluxo Compra até Financeiro

Fluxo ponta a ponta desde a criação da compra até a liquidação financeira da conta a pagar gerada.

```
COMPRA ➜ RECEBIMENTO ➜ NOTA FISCAL ➜ CONTA A PAGAR ➜ APROVAÇÃO ➜ PAGAMENTO
 PEDIDO    ESTOQUE      NF na compra   Parcelas         —          Liquidação
```

## Etapa 1 — Compra rápida
`compras/views_simples.py` (`/compras/compra-rapida/`)

Entrada: fornecedor, produtos/quantidades/preços, data de entrega prevista.
Cria `PedidoCompra` com `status='PENDENTE_RECEBIMENTO'`, sem cotação nem proposta de fornecedor vinculada (modo simples — para o fluxo com cotação/proposta, ver `docs/2_MODULOS/MODULO_COMPRAS.md`).

## Etapa 2 — Recebimento e entrada em estoque
`/compras/pedido/<id>/receber/`

Entrada: quantidade recebida (aceita recebimento parcial), local de estoque, número de lote.
Cria `RecebimentoCompra` (`status='PENDENTE_NOTA'`) e, por item, `ItemRecebimento` + `Lote` no estoque com a quantidade recebida.

## Etapa 3 — Registro da nota fiscal
`/compras/recebimento/<id>/fatura/`

Entrada: número/série da NF, data de emissão, CFOP, valor total, condição de pagamento.
`RecebimentoCompra` muda para `status='FINALIZADO'`.

## Etapa 4 — Criação automática da conta a pagar
Quando o recebimento é finalizado **com NF**, o sistema cria automaticamente:
- `ContaPagar` (`financeiro/models.py`), vinculada ao fornecedor do pedido, valor = valor da NF, `requer_aprovacao=True` por padrão
- `ParcelaContaPagar` para cada parcela da condição de pagamento do pedido (ex: "3x 30 dias" → 3 parcelas com vencimentos escalonados)

Recebimento finalizado **sem NF** não gera conta a pagar.

## Etapa 5 — Aprovação
`/financeiro/contas/<id>/aprovar/`

Se a conta requer aprovação, o pagamento fica bloqueado até um usuário com permissão aprovar (`ContaPagar.status`: `ABERTA` → `APROVADA`).

## Etapa 6 — Juros e multa em atraso
`ParcelaContaPagar.save()` recalcula, a cada acesso, os dias de atraso e aplica juros/multa conforme a configuração de juros/multa da empresa (`/configuracao/juros-multa/`: taxa de juros mensal, tipo de multa `PERCENTUAL` ou `POR_DIA`, dias de tolerância) quando a parcela passa do vencimento (`status` vira `VENCIDA`).

## Etapa 7 — Pagamento e compensação
`/financeiro/parcelas/<id>/pagar/`

Entrada: valor a pagar, forma de pagamento (dinheiro, boleto, TED, cartão, cheque, PIX), documento, banco, comprovante.
Cria `PagamentoContaPagar` (`status='PENDENTE'` até compensação bancária). Ao compensar, parcela vira `PAGA`; quando todas as parcelas da conta estão pagas, `ContaPagar.status` vira `PAGA`.

## Tabela de decisão
| Condição | Comportamento |
|---|---|
| Recebimento finalizado sem NF | Não cria conta a pagar |
| Recebimento finalizado com NF | Cria `ContaPagar` + `ParcelaContaPagar` |
| Conta requer aprovação e não aprovada | Impede pagamento |
| Parcela vence sem pagamento | Recalcula juros/multa e marca `VENCIDA` |
| Todas as parcelas de uma conta pagas | `ContaPagar.status = PAGA` |

## Relatórios relacionados (`/financeiro/`)
- Dashboard financeiro: KPIs de total a pagar, pago, juros/multas acumuladas, alertas de vencimento
- Contas a vencer / contas vencidas (com dias de atraso e juros/multa acumulados)
- Fluxo de caixa: previsto vs. pago, por mês e por fornecedor

## Evidências esperadas em auditoria
- Pedido e recebimento vinculados
- Conta e parcelas com referência da NF
- Registro de pagamento com comprovante anexado

## Pendências conhecidas (backlog, não implementado)
- Integração com API bancária para compensação automática
- Geração automática de boleto
- Renegociação de parcelas com novo contrato
- Notificações automáticas por e-mail/WhatsApp antes do vencimento

## Fontes
Consolidado a partir de `FLUXO_COMPRA_FINANCEIRO.md` e `GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md` (originais, ver `docs/6_OPERACIONAL/GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md`), verificado contra `compras/views_simples.py` e `financeiro/models.py` (`ContaPagar`, `ParcelaContaPagar`, `PagamentoContaPagar`).
