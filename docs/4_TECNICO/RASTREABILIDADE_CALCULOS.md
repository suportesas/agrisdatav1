# Rastreabilidade de Calculos

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Origem e trilha de resultados

## Objetivo
Explicar como cada resultado numerico critico e formado, persistido e auditado.

## Modelo de trilha
Origem de dados -> Regra aplicada -> Persistencia -> Evidencia de teste/auditoria

## Trilha 1: Compras para Financeiro
1. Origem
- Pedido e recebimento em compras
- Nota fiscal registrada no recebimento

2. Regra aplicada
- Valor final de pedido: total - desconto + frete
- Integracao cria conta a pagar e parcelas conforme condicao

3. Persistencia
- ContaPagar e ParcelaContaPagar no modulo financeiro

4. Evidencia
- Relacao entre recebimento, conta e parcelas
- Logs/historico de alteracao de pagamento quando houver ajuste

## Trilha 2: Fiscal no Faturamento
1. Origem
- Itens de nota: quantidade, valor unitario, descontos e aliquotas

2. Regra aplicada
- ICMS, ST, IPI, PIS, COFINS, FCP

3. Persistencia
- Campos de base e valor tributario por item

4. Evidencia
- Campos de auditoria de criacao/atualizacao
- XML/artefatos de emissao quando aplicavel

## Trilha 3: Estoque e Movimentacao
1. Origem
- Entrada, saida, ajuste e emprestimo/devolucao

2. Regra aplicada
- Atualizacao de quantidade atual por tipo de movimento
- Bloqueio de saida sem saldo

3. Persistencia
- MovimentacaoEstoque como diario de eventos
- Quantidade atual em lote

4. Evidencia
- Registro de data_movimentacao e usuario

## Trilha 4: Operacoes de Campo
1. Origem
- Pesagem de bruto, tara e desconto

2. Regra aplicada
- Peso liquido e peso final com piso zero

3. Persistencia
- Valores armazenados na entidade de pesagem e agregacoes de carga

4. Evidencia
- Motivo de desconto, operador e data

## Checklist de auditoria por resultado
- Qual foi a origem dos dados?
- Qual regra numerica foi aplicada?
- Houve condicional alterando o caminho?
- Onde o resultado foi salvo?
- Qual teste garante esse comportamento?

## Gaps atuais
- Vincular cada trilha a arquivos de teste automatizado especificos.
- Padronizar identificador de correlacao em logs intermodulo.
- Criar API reference com codigos de erro por trilha.
