# Modulo produtos

Owner: Time produtos
Status: In Review
Last Updated: 2026-07-01
Scope: produtos

## Visao geral
Modulo produtos mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de produtos com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| TipoProduto | Entidade de dominio do modulo | A validar por campo |
| UnidadeMedida | Entidade de dominio do modulo | A validar por campo |
| Categoria | Entidade de dominio do modulo | A validar por campo |
| SubCategoria | Entidade de dominio do modulo | A validar por campo |
| NaturezaOperacao | Entidade de dominio do modulo | A validar por campo |
| Produto | Entidade de dominio do modulo | A validar por campo |
| ProdutoFornecedor | Entidade de dominio do modulo | A validar por campo |
| ProdutoTributacao | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: TipoProduto, UnidadeMedida, Categoria, SubCategoria, NaturezaOperacao, Produto, ProdutoFornecedor, ProdutoTributacao, ProdutoDefensivoCultura, ProdutoDocumento, DimensaoVariante, ProdutoAtributo

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

Rotas de referencia (amostra): dashboard/; tipos-produto/; tipos-produto/cadastrar/; tipos-produto/<int:pk>/editar/; tipos-produto/<int:pk>/excluir/; tipos-produto/ajax/listar/; unidades/; unidades/cadastrar/; unidades/<int:pk>/editar/; unidades/<int:pk>/excluir/; unidades/ajax/criar/; ncm/buscar/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de produtos.
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
- produtos/models.py
- produtos/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
