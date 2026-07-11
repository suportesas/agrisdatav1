# Modulo estoque

Owner: Time estoque
Status: In Review
Last Updated: 2026-07-10
Scope: estoque

## Visao geral
Modulo estoque mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de estoque com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| EmpresaQuerySet | Entidade de dominio do modulo | A validar por campo |
| ArmazemManager | Entidade de dominio do modulo | A validar por campo |
| Armazem | Entidade de dominio do modulo | A validar por campo |
| LocalEstocagem | Entidade de dominio do modulo | A validar por campo |
| Lote | Entidade de dominio do modulo | A validar por campo |
| MovimentacaoEstoque | Entidade de dominio do modulo | A validar por campo |
| InventarioCiclicoSchedule | Entidade de dominio do modulo | A validar por campo |
| InventarioCiclico | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: EmpresaQuerySet, ArmazemManager, Armazem, LocalEstocagem, Lote, MovimentacaoEstoque, InventarioCiclicoSchedule, InventarioCiclico, InventarioCiclicoItem

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

Rotas de referencia (amostra): entrada-rapida/; saida-rapida/; ajuste-rapido/; escolher-modo-estoque/; ; armazens/; armazens/create/; armazens/<int:pk>/; armazens/<int:pk>/edit/; armazens/<int:pk>/delete/; locais/; locais/create/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de estoque.
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
- estoque/models.py
- estoque/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
- Estratégia de atualização de estoque (dois fluxos: com lote / entrada rápida sem lote), código-chave e debugging: `docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md`
- Fluxogramas detalhados de entrada/saída: `docs/4_TECNICO/FLUXOGRAMAS_ESTOQUE.md`
