# Modulo rh

Owner: Time rh
Status: In Review
Last Updated: 2026-07-01
Scope: rh

## Visao geral
Modulo rh mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de rh com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| HistoricoFuncionario | Entidade de dominio do modulo | A validar por campo |
| FuncaoFuncionario | Entidade de dominio do modulo | A validar por campo |
| CategoriaRiscoAmbiental | Entidade de dominio do modulo | A validar por campo |
| RiscoAmbientalFuncao | Entidade de dominio do modulo | A validar por campo |
| RiscoAmbientalCatalogo | Entidade de dominio do modulo | A validar por campo |
| VinculoContrato | Entidade de dominio do modulo | A validar por campo |
| Funcionario | Entidade de dominio do modulo | A validar por campo |
| DocumentoFuncionario | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: HistoricoFuncionario, FuncaoFuncionario, CategoriaRiscoAmbiental, RiscoAmbientalFuncao, RiscoAmbientalCatalogo, VinculoContrato, Funcionario, DocumentoFuncionario, FeriasFuncionario, AfastamentoFuncionario, LaudoRisco, TipoExameASO

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

Rotas de referencia (amostra): funcoes/; funcoes/novo/; funcoes/criar-ajax/; funcoes/get-salario/; funcoes/<int:pk>/editar/; funcoes/<int:pk>/excluir/; riscos-ambientais/; riscos-ambientais/novo/; riscos-ambientais/<int:pk>/editar/; riscos-ambientais/<int:pk>/excluir/; funcionarios/; funcionarios/novo/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de rh.
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
- rh/models.py
- rh/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
