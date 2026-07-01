# Calculos Centralizados

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Regras de calculo do sistema

## Objetivo
Centralizar formulas, entradas, condicionais e rastreabilidade dos calculos criticos do ERP.

## Metodo de documentacao
Para cada calculo, documentar obrigatoriamente:
1. Formula matematica
2. Entradas e validacoes
3. Condicionais que alteram o resultado
4. Arredondamento e limites
5. Exemplo numerico reproduzivel
6. Origem -> regra -> persistencia -> teste

## Dominios a cobrir
- Fiscal (ICMS, ST, IPI, PIS, COFINS, FCP)
- Financeiro (juros, multa, parcelas, renegociacao)
- Compras (valor final de pedido e recebimento)
- Estoque (consumo, ocupacao, saldo)
- Vendas (total, desconto, cambio)
- Operacoes de campo (pesagem e consolidacao)
- Adiantamentos (conversao de moeda e descontos)

## Catalogo de calculos documentados

### 1. Fiscal: ICMS com reducao de base
- Formula: BC = valor_total x (100 - reducao_bc) / 100
- Formula: valor_icms = BC x aliquota_icms / 100
- Entradas: quantidade, valor_unitario, desconto, reducao_bc, aliquota_icms
- Condicional: so aplica reducao se reducao_bc > 0 e aliquota_icms > 0
- Excecoes/fallback: valores invalidos devem ser rejeitados na validacao
- Codigo fonte: faturamento/models.py (ItemNotaFiscal.save)

### 2. Fiscal: ICMS ST
- Formula: BC_ST = valor_total x (100 + MVA) / 100 x (100 - reducao_st) / 100
- Formula: valor_icms_st = max(BC_ST x aliquota_st / 100 - valor_icms, 0)
- Entradas: mva, reducao_st, aliquota_st
- Condicional: se aliquota_st <= 0, manter campos ST zerados
- Codigo fonte: faturamento/models.py (ItemNotaFiscal.save)

### 3. Fiscal: IPI, PIS, COFINS, FCP
- Formula: valor_ipi = valor_total x aliquota_ipi / 100
- Formula: valor_pis = valor_total x aliquota_pis / 100
- Formula: valor_cofins = valor_total x aliquota_cofins / 100
- Formula: fcp_valor = fcp_base x aliquota_fcp / 100 (quando aliquota_fcp > 0)
- Condicional: FCP/FCP ST somente quando aliquota correspondente > 0
- Codigo fonte: faturamento/models.py (ItemNotaFiscal.save)

### 4. Financeiro: valor ajustado da conta a pagar
- Formula: valor_ajustado = valor_total - desconto_negociado
- Entradas: valor_total, desconto_negociado
- Validacoes: valor_total >= 0.01 e desconto >= 0
- Codigo fonte: financeiro/models.py (ContaPagar.calcular_valor_ajustado)

### 5. Financeiro: total de parcela
- Formula: valor_total_parcela = valor_parcela + juros_parcela + multa_parcela
- Entradas: valor_parcela, juros_parcela, multa_parcela
- Validacoes: todos nao negativos
- Codigo fonte: financeiro/models.py (ParcelaContaPagar.recalcular_total)

### 6. Financeiro: dias de atraso
- Formula: dias_atraso = max(0, hoje - data_vencimento)
- Condicional: se status == PAGA, dias_atraso = 0
- Codigo fonte: financeiro/models.py (ParcelaContaPagar.calcular_dias_atraso)

### 7. Compras: valor final do pedido
- Formula: valor_final = valor_total - valor_desconto + valor_frete
- Entradas: valor_total, valor_desconto, valor_frete
- Codigo fonte: compras/models.py (PedidoCompra.save)

### 8. Compras: preco total do item
- Formula: preco_total = max(0, preco_unitario x quantidade - desconto)
- Excecao/fallback: nunca permitir total negativo
- Codigo fonte: compras/models.py (ItemPedidoCompra.save)

### 9. Compras: percentual cotado
- Formula: percentual = (itens_cotados / total_itens) x 100
- Condicional: se total_itens == 0, retornar 0
- Codigo fonte: compras/models.py (SolicitacaoCompra.calcular_percentual_cotado)

### 10. Estoque: percentual de consumo do lote
- Formula: percentual_consumo = ((inicial - atual) / inicial) x 100
- Condicional: se inicial == 0, retornar 0
- Codigo fonte: estoque/models.py (Lote.get_percentual_consumo)

### 11. Estoque: percentual de ocupacao de armazem
- Formula: percentual_ocupacao = (ocupacao_kg / capacidade_kg) x 100
- Condicional: se capacidade_kg ausente/zero, retornar 0
- Codigo fonte: estoque/models.py (Armazem.get_percentual_ocupacao)

### 12. Operacoes de campo: pesagem
- Formula: peso_liquido = max(peso_bruto - tara, 0)
- Formula: peso_final = max(peso_liquido - desconto, 0)
- Validacao: tara nao pode ser maior que bruto
- Codigo fonte: operacoes_campo/models.py (CarrocaoPesagem.save)

### 13. Adiantamentos: conversao cambial
- Formula: valor_brl = valor_estrangeiro x taxa_cambio
- Validacao: taxa_cambio > 0
- Codigo fonte: adiantamentos/models.py (Adiantamento.save)

### 14. Vendas: total do pedido
- Formula: valor_total = valor_produtos + valor_frete - valor_desconto
- Condicional exportacao: valor_moeda_estrangeira = valor_total / taxa_cambio
- Codigo fonte: vendas/models.py (PedidoVenda.calcular_total)

## Exemplo numerico de referencia
Caso compras:
- valor_total = 10000.00
- valor_desconto = 500.00
- valor_frete = 300.00
- resultado: valor_final = 9800.00

Caso financeiro:
- valor_parcela = 3000.00
- juros_parcela = 60.00
- multa_parcela = 30.00
- resultado: valor_total_parcela = 3090.00

## Matriz de status
| Dominio | Quantidade de calculos mapeados | Quantidade documentada | Cobertura |
|---|---:|---:|---:|
| Fiscal | 4 | 4 | 100% |
| Financeiro | 3 | 3 | 100% |
| Compras | 3 | 3 | 100% |
| Estoque | 2 | 2 | 100% |
| Vendas | 1 | 1 | 100% |
| Operacoes de campo | 1 | 1 | 100% |
| Adiantamentos | 1 | 1 | 100% |

## Observacoes de precisao
- Priorizar Decimal para calculos monetarios e fiscais.
- Evitar float em operacoes de dinheiro.
- Quando necessario, padronizar quantize para 2 casas no ponto de persistencia.
