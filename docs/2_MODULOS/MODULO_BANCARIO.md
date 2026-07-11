# Modulo bancario

Owner: Time bancario
Status: In Review
Last Updated: 2026-07-01
Scope: bancario

## Visao geral
Modulo bancario mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de bancario com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| ContaBancaria | Entidade de dominio do modulo | A validar por campo |
| ImportacaoExtrato | Entidade de dominio do modulo | A validar por campo |
| ExtratoLancamento | Entidade de dominio do modulo | A validar por campo |
| ConciliacaoLancamento | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: ContaBancaria, ImportacaoExtrato, ExtratoLancamento, ConciliacaoLancamento

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

Rotas de referencia (amostra): contas/; contas/nova/; contas/<int:pk>/; contas/<int:pk>/editar/; contas/<int:pk>/toggle/; contas/<int:pk>/importar/; importacoes/<int:pk>/; importacoes/<int:pk>/deletar/; conciliacao/confirmar/; conciliacao/ignorar/; conciliacao/desfazer/; conciliacao/manual/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de bancario.
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
- bancario/models.py
- bancario/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
