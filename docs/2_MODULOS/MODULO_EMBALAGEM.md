# Modulo embalagem

Owner: Time embalagem
Status: In Review
Last Updated: 2026-07-10
Scope: embalagem

## Visao geral
Modulo embalagem mapeado a partir de models e urls do codigo atual.

> Nota: existe um planejamento pré-implementação escrito para o repositório anterior (agrisdatav1), anterior à existência real deste app — arquivado em `docs/archive/embalagem-planejamento-v1/` para referência histórica. Este documento é a fonte de verdade para o estado atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de embalagem com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| TipoEmbalagem | Entidade de dominio do modulo | A validar por campo |
| OrdemEmbalagem | Entidade de dominio do modulo | A validar por campo |
| PalletEmbalado | Entidade de dominio do modulo | A validar por campo |
| ItemPallet | Entidade de dominio do modulo | A validar por campo |
| RomaneioVenda | Entidade de dominio do modulo | A validar por campo |
| ItemRomaneioVenda | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: TipoEmbalagem, OrdemEmbalagem, PalletEmbalado, ItemPallet, RomaneioVenda, ItemRomaneioVenda

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

Rotas de referencia (amostra): /; tipos/; tipos/novo/; tipos/<int:pk>/editar/; ordens/; ordens/nova/; ordens/<int:pk>/; ordens/<int:pk>/gerar-pallets/; ordens/<int:pk>/etiquetas/; pallets/; pallets/<int:pk>/etiqueta/; ordens/<int:ordem_pk>/pallet-misto/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de embalagem.
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
- embalagem/models.py
- embalagem/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md

