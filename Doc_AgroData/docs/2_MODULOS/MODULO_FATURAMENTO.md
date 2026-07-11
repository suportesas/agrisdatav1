# Modulo faturamento

Owner: Time faturamento
Status: In Review
Last Updated: 2026-07-01
Scope: faturamento

## Visao geral
Modulo faturamento mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de faturamento com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| FaturamentoBaseModel | Entidade de dominio do modulo | A validar por campo |
| ConfiguracaoFiscal | Entidade de dominio do modulo | A validar por campo |
| NotaFiscal | Entidade de dominio do modulo | A validar por campo |
| ItemNotaFiscal | Entidade de dominio do modulo | A validar por campo |
| PagamentoNF | Entidade de dominio do modulo | A validar por campo |
| DuplicataNF | Entidade de dominio do modulo | A validar por campo |
| CartaCorrecaoNFe | Entidade de dominio do modulo | A validar por campo |
| InutilizacaoNFe | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: FaturamentoBaseModel, ConfiguracaoFiscal, NotaFiscal, ItemNotaFiscal, PagamentoNF, DuplicataNF, CartaCorrecaoNFe, InutilizacaoNFe, NFeReferenciada, InvoiceExportacao, ItemInvoice, PackingList

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

Rotas de referencia (amostra): /; notas-fiscais/; notas-fiscais/nova/; notas-fiscais/<int:pk>/; notas-fiscais/<int:pk>/editar/; notas-fiscais/<int:pk>/emitir/; notas-fiscais/<int:pk>/emitir/ajax/; notas-fiscais/<int:pk>/debug-payload/; notas-fiscais/<int:pk>/cancelar/; notas-fiscais/<int:pk>/consultar/; notas-fiscais/<int:pk>/consultar/ajax/; notas-fiscais/<int:pk>/recuperar/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de faturamento.
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
- faturamento/models.py
- faturamento/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md

