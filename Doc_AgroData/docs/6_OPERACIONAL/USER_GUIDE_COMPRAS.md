# Guia Operacional de Compras

Owner: Operacao Compras
Status: Draft
Last Updated: 2026-07-01
Scope: Compra rapida ate pagamento

## Objetivo
Orientar o usuario de negocio no fluxo de compra, recebimento, nota fiscal e pagamento.

## Fonte consolidada
- GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md

## Passo 1 - Criar compra rapida
- Selecionar fornecedor.
- Inserir produtos, quantidades e precos.
- Confirmar criacao do pedido.

Resultado esperado:
- Pedido criado e pendente de recebimento.

## Passo 2 - Registrar recebimento
- Conferir mercadoria.
- Informar local/armazem.
- Confirmar entrada no estoque.

Resultado esperado:
- Recebimento criado e lote gerado automaticamente.

## Passo 3 - Registrar nota fiscal
- Informar numero, serie, data e valor da NF.
- Definir condicao de pagamento (parcelamento).
- Confirmar criacao da conta a pagar.

Resultado esperado:
- Conta e parcelas geradas no financeiro.

## Passo 4 - Aprovar e pagar
- Aprovar conta quando exigido.
- Registrar pagamento da parcela com comprovante.

Resultado esperado:
- Parcela liquidada e historico registrado.

## Erros comuns
- NF nao informada: conta nao e criada.
- Conta sem aprovacao: pagamento bloqueado.
- Divergencia de valor: revisar recebimento e ajustes.

## Referencia legada
- GUIA_COMPRA_RAPIDA_ATE_PAGAMENTO.md
