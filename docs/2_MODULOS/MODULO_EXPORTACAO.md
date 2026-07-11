# Modulo exportacao

Owner: Time exportacao
Status: In Review
Last Updated: 2026-07-01
Scope: exportacao

## Visao geral
Modulo exportacao mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de exportacao com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| ExportacaoBaseModel | Entidade de dominio do modulo | A validar por campo |
| SolicitacaoBooking | Entidade de dominio do modulo | A validar por campo |
| Booking | Entidade de dominio do modulo | A validar por campo |
| BookingContainer | Entidade de dominio do modulo | A validar por campo |
| BookingContainerHistory | Entidade de dominio do modulo | A validar por campo |
| OrdemColeta | Entidade de dominio do modulo | A validar por campo |
| FotoOrdemColeta | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: ExportacaoBaseModel, SolicitacaoBooking, Booking, BookingContainer, BookingContainerHistory, OrdemColeta, FotoOrdemColeta

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

Rotas de referencia (amostra): solicitacoes/; solicitacoes/nova/; solicitacoes/<int:pk>/; solicitacoes/<int:pk>/editar/; solicitacoes/<int:pk>/pdf/; bookings/; bookings/novo/; bookings/<int:pk>/; bookings/<int:pk>/editar/; bookings/<int:booking_pk>/containers/; containers/; bookings/<int:booking_pk>/containers/novo/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de exportacao.
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
- exportacao/models.py
- exportacao/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
