# Condicionais Criticas

Owner: Engenharia
Status: Draft
Last Updated: 2026-07-01
Scope: Regras condicionais de alto impacto

## Objetivo
Documentar condicionais que mudam comportamento do sistema e podem gerar regressao.

## Metodo
Cada condicional deve ser descrita por tabela de decisao, com cobertura de teste.

## Tabela padrao
| Contexto | Condicao | Comportamento | Risco | Codigo fonte | Teste |
|---|---|---|---|---|---|
| Pedido de compra | status antigo ENVIADO e novo PENDENTE | Bloqueia downgrade e mantem ENVIADO | alto | compras/models.py (PedidoCompra.save) | a mapear |
| Pagamento financeiro | conta PAGA ou CANCELADA | Impede pagamento | alto | financeiro/models.py (ContaPagar.pode_pagar) | a mapear |
| Pagamento financeiro | requer_aprovacao=True e status ABERTA | Impede pagamento ate aprovar | alto | financeiro/models.py (ContaPagar.pode_pagar) | a mapear |
| Parcela em atraso | status PAGA | dias_atraso = 0 | medio | financeiro/models.py (ParcelaContaPagar.calcular_dias_atraso) | a mapear |
| Solicitacao de compra | total_itens == 0 | percentual cotado retorna 0 | medio | compras/models.py (calcular_percentual_cotado) | a mapear |
| Consumo de lote | quantidade_inicial == 0 | percentual consumo retorna 0 | medio | estoque/models.py (Lote.get_percentual_consumo) | a mapear |
| Ocupacao de armazem | capacidade_kg ausente/zero | percentual ocupacao retorna 0 | medio | estoque/models.py (Armazem.get_percentual_ocupacao) | a mapear |
| Movimentacao estoque | quantidade de saida > saldo atual | aborta com ValidationError | alto | estoque/models.py (MovimentacaoEstoque.save) | a mapear |
| Pesagem campo | tara > peso bruto | aborta com ValidationError | alto | operacoes_campo/models.py (CarrocaoPesagem.save) | a mapear |
| Fiscal FCP | aliquota_fcp <= 0 | nao calcula valor de FCP | medio | faturamento/models.py (ItemNotaFiscal.save) | a mapear |
| Fiscal ST | aliquota_st <= 0 | nao calcula ST | medio | faturamento/models.py (ItemNotaFiscal.save) | a mapear |
| Feature flag | COMPRAS_XML_IMPORT desativada | bloqueia fluxo de importacao XML | medio | core/feature_flags.py + uso em compras | a mapear |

## Categorias iniciais
- Transicao de status (nao permitir downgrade indevido)
- Aprovacoes financeiras (bloqueios por estado)
- Validacoes de saldo e quantidade (nao negativo)
- Divisao por zero e null guards
- Feature flags
- Permissoes por perfil e empresa

## Tabela de decisao resumida
| Categoria | Condicao | Acao |
|---|---|---|
| Status protegido | tentativa de retorno de ENVIADO para PENDENTE | manter ENVIADO |
| Aprovacao financeira | conta aberta com aprovacao obrigatoria | negar pagamento |
| Estoque | saida maior que saldo | negar movimentacao |
| Guard matematico | divisor igual a zero | retornar 0 ou bloquear |
| Flag de funcionalidade | flag false | esconder/bloquear funcionalidade |

## Checklist por condicional
- Existe descricao de negocio?
- Existe tabela de decisao?
- Existe referencia de codigo?
- Existe teste positivo?
- Existe teste de borda?
- Existe teste de regressao?

## Prioridade de cobertura de testes
1. Alto risco: status, aprovacao e saldo de estoque.
2. Medio risco: guards matematicos e flags.
3. Baixo risco: refinamentos de exibicao/UX.
