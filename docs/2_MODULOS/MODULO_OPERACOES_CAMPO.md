# Modulo operacoes_campo

Owner: Time operacoes_campo
Status: In Review
Last Updated: 2026-07-01
Scope: operacoes_campo

## Visao geral
Modulo operacoes_campo mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de operacoes_campo com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| CustoHoraMaquina | Entidade de dominio do modulo | A validar por campo |
| TipoServicoOS | Entidade de dominio do modulo | A validar por campo |
| SubtipoServicoOS | Entidade de dominio do modulo | A validar por campo |
| ModalidadeExecucaoOS | Entidade de dominio do modulo | A validar por campo |
| OrdemServico | Entidade de dominio do modulo | A validar por campo |
| OrdemServicoInsumo | Entidade de dominio do modulo | A validar por campo |
| OSFuncionario | Entidade de dominio do modulo | A validar por campo |
| OSIntervalo | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: CustoHoraMaquina, TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS, OrdemServico, OrdemServicoInsumo, OSFuncionario, OSIntervalo, OSMaquina, CustoTalhao, EtapaColheita, FrotaColheita

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

Rotas de referencia (amostra): ordens-servico/; ordens-servico/nova/; ordens-servico/custos-talhao/; ordens-servico/<int:pk>/; ordens-servico/<int:pk>/editar/; ordens-servico/<int:pk>/excluir/; ordens-servico/<int:pk>/aprovar/; ordens-servico/<int:pk>/iniciar/; ordens-servico/<int:pk>/concluir/; ordens-servico/<int:pk>/recalcular-custos/; ordens-servico/<int:pk>/pausar/; ordens-servico/<int:pk>/retomar/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de operacoes_campo.
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
- operacoes_campo/models.py
- operacoes_campo/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
