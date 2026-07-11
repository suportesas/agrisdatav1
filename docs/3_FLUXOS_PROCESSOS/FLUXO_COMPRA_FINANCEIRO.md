# Fluxo Compra ate Financeiro

Owner: Processos
Status: Draft
Last Updated: 2026-07-01
Scope: Compras, recebimento e contas a pagar

## Objetivo
Documentar o fluxo ponta a ponta desde a compra ate a liquidacao financeira.

## Escopo
Fonte consolidada:
- FLUXO_COMPRA_FINANCEIRO.md
- GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md

## Visao do fluxo
1. Compra rapida
2. Recebimento e entrada em estoque
3. Registro da nota fiscal
4. Criacao automatica de conta a pagar
5. Aprovacao financeira
6. Pagamento e compensacao

## Etapa 1 - Compra rapida
Entrada:
- Fornecedor
- Itens, quantidades e precos

Saida:
- Pedido criado com status pendente de recebimento

## Etapa 2 - Recebimento
Entrada:
- Conferencia de quantidade recebida
- Armazem/local de estoque

Regras:
- Pode haver recebimento parcial
- Entrada gera lote e atualiza saldo

Saida:
- Recebimento com status aguardando nota fiscal

## Etapa 3 - Faturamento de recebimento
Entrada:
- Numero/série NF
- Data emissao
- Valor total
- Condicao de pagamento

Saida:
- Recebimento finalizado

## Etapa 4 - Integracao financeira automatica
Regra:
- Recebimento finalizado com NF deve gerar ContaPagar

Saida:
- ContaPagar criada
- Parcelas criadas conforme condicao de pagamento

## Etapa 5 - Aprovacao
Regra:
- Se a conta requer aprovacao, bloqueia pagamento ate aprovacao

Saida:
- Conta em estado apto para pagamento

## Etapa 6 - Pagamento
Entrada:
- Forma de pagamento
- Documento/comprovante
- Data de compensacao quando aplicavel

Saida:
- Pagamento registrado e parcela liquidada

## Tabela de decisao resumida
| Condicao | Comportamento |
|---|---|
| Recebimento finalizado sem NF | Nao cria conta a pagar |
| Recebimento finalizado com NF | Cria conta e parcelas |
| Conta requer aprovacao e nao aprovada | Impede pagamento |
| Parcela paga com compensacao | Atualiza status de liquidacao |

## Evidencias esperadas
- Pedido e recebimento vinculados
- Conta e parcelas com referencia da NF
- Registro de pagamento com comprovante

## Referencias legadas
- FLUXO_COMPRA_FINANCEIRO.md
- GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md
