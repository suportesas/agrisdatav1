# Modulo financeiro

Owner: Time financeiro
Status: In Review
Last Updated: 2026-07-01
Scope: financeiro

## Visao geral
Modulo financeiro mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de financeiro com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| FormaPagemento | Entidade de dominio do modulo | A validar por campo |
| ConfiguracaoJurosMulta | Entidade de dominio do modulo | A validar por campo |
| ContaPagar | Entidade de dominio do modulo | A validar por campo |
| ParcelaContaPagar | Entidade de dominio do modulo | A validar por campo |
| PagamentoContaPagar | Entidade de dominio do modulo | A validar por campo |
| LogAlteracaoPagamento | Entidade de dominio do modulo | A validar por campo |
| AjusteContaPagar | Entidade de dominio do modulo | A validar por campo |
| ContaReceber | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: FormaPagemento, ConfiguracaoJurosMulta, ContaPagar, ParcelaContaPagar, PagamentoContaPagar, LogAlteracaoPagamento, AjusteContaPagar, ContaReceber, ParcelaContaReceber, RecebimentoContaReceber

## Funcionalidades
| Funcionalidade | Entrada | Regra principal | Saida |
|---|---|---|---|
| Listagem e consulta | Filtros por tela | Respeitar escopo de empresa/permissao | Dados exibidos por perfil |
| Cadastro e edicao | Formulario de negocio | Validacoes de dominio | Registro persistido |
| Acao operacional | Evento de usuario | Regras de status e consistencia | Estado atualizado |

## Fluxos principais
- Entrada via rotas do modulo e processamento em views.
- Persistencia nas entidades de dominio listadas acima.
- Integracao com outros modulos conforme regras de negocio.

Rotas de referencia (amostra): /; contas/; contas/<int:pk>/; contas/criar/; contas/<int:pk>/editar/; contas/<int:pk>/aprovar/; parcelas/; contas/<int:conta_pk>/parcelas/criar/; parcelas/<int:parcela_pk>/pagar/; pagamentos/<int:pk>/retornar-pendente/; contas/<int:pk>/quitar-saldo/; contas/<int:pk>/ajuste/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de financeiro.
- Garantir autorizacao por perfil antes de alterar estado.

## Integracoes
- Integracao por URL include com core/urls.py.
- Eventos podem alimentar financeiro, estoque, faturamento e relatorios conforme modulo.

## Evidencias de teste
| Regra | Teste existente | Gap |
|---|---|---|
| Escopo por empresa | A mapear por modulo | Sim |
| Transicao de status | A mapear por modulo | Sim |
| Fluxo principal | A mapear por modulo | Sim |

## Referencias
- financeiro/models.py
- financeiro/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md

