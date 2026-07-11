# Modulo frota

Owner: Time frota
Status: In Review
Last Updated: 2026-07-01
Scope: frota

## Visao geral
Modulo frota mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de frota com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| Vehicle | Entidade de dominio do modulo | A validar por campo |
| VehicleValueHistory | Entidade de dominio do modulo | A validar por campo |
| VehiclePlate | Entidade de dominio do modulo | A validar por campo |
| VehicleDocument | Entidade de dominio do modulo | A validar por campo |
| Motorista | Entidade de dominio do modulo | A validar por campo |
| MotoristadoDocumento | Entidade de dominio do modulo | A validar por campo |
| MotoristaVinculoPlaca | Entidade de dominio do modulo | A validar por campo |
| AbastecimentoVeiculo | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: Vehicle, VehicleValueHistory, VehiclePlate, VehicleDocument, Motorista, MotoristadoDocumento, MotoristaVinculoPlaca, AbastecimentoVeiculo, ManutencaoVeiculo, ManutencaoItem, DocumentoManutencao, AlertaManutencao

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

Rotas de referencia (amostra): veiculos/; veiculos/novo/; veiculos/<int:pk>/; veiculos/<int:pk>/editar/; veiculos/<int:pk>/excluir/; veiculos/<int:vehicle_pk>/placas/nova/; veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/editar/; veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/excluir/; api/veiculos/; veiculos/export/csv/; motoristas/; motoristas/criar/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de frota.
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
- frota/models.py
- frota/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
