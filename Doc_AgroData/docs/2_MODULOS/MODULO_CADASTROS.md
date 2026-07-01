# Modulo cadastros

Owner: Time cadastros
Status: In Review
Last Updated: 2026-07-01
Scope: cadastros

## Visao geral
Modulo cadastros mapeado a partir de models e urls do codigo atual.

## Objetivo de negocio
Disponibilizar as funcionalidades de cadastros com isolamento por empresa quando aplicavel e rastreabilidade de operacoes.

## Entidades principais
| Entidade | Papel | Campos criticos |
|---|---|---|
| EmpresaQuerySet | Entidade de dominio do modulo | A validar por campo |
| AreaManager | Entidade de dominio do modulo | A validar por campo |
| TalhaoManager | Entidade de dominio do modulo | A validar por campo |
| Fazenda | Entidade de dominio do modulo | A validar por campo |
| EnderecoFazenda | Entidade de dominio do modulo | A validar por campo |
| ContatoFazenda | Entidade de dominio do modulo | A validar por campo |
| ContaBancariaFazenda | Entidade de dominio do modulo | A validar por campo |
| DocumentoFazenda | Entidade de dominio do modulo | A validar por campo |

Resumo de entidades: EmpresaQuerySet, AreaManager, TalhaoManager, Fazenda, EnderecoFazenda, ContatoFazenda, ContaBancariaFazenda, DocumentoFazenda, DocumentoFornecedor, Cliente, Moeda, NCM

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

Rotas de referencia (amostra): fazendas/; fazendas/nova/; fazendas/<int:pk>/; fazendas/<int:pk>/editar/; fazendas/<int:pk>/excluir/; api/buscar-cnpj/; api/buscar-cep/; api/buscar-geolocalizacao/; fazendas/<int:fazenda_pk>/enderecos/novo/; fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/editar/; fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/excluir/; fazendas/<int:fazenda_pk>/contatos/novo/

## Estados e transicoes
| Estado atual | Evento | Proximo estado | Restricoes |
|---|---|---|---|
| Draft/Inicial | Criacao | Ativo/Em processamento | Validacoes obrigatorias |
| Ativo | Acao de negocio | Concluido/Cancelado | Permissao e consistencia |

## Calculos e condicionais vinculados
- Consultar docs/4_TECNICO/CALCULOS_CENTRALIZADOS.md
- Consultar docs/4_TECNICO/CONDICIONAIS_CRITICAS.md

## Permissoes e isolamento
- Aplicar filtro por empresa em consultas sensiveis de cadastros.
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
- cadastros/models.py
- cadastros/urls.py
- docs/TEMPLATES/TEMPLATE_MODULO.md
