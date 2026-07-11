Owner: Time produtos
Status: Approved
Last Updated: 2026-07-10
Scope: produtos (`/produtos/`)

# Módulo Produtos

## Visão geral
Catálogo de produtos com hierarquia Categoria → Subcategoria, unidades de medida, tributação e vínculo com fornecedores/defensivos por cultura.

## Entidades principais
| Entidade | Papel |
|---|---|
| `TipoProduto`, `UnidadeMedida` | Classificação e unidade base |
| `Categoria` → `SubCategoria` (FK `categoria`) | Hierarquia de classificação (ex: Fertilizante → Químico/Orgânico/Foliar/Mineral; Defensivo → Herbicida/Inseticida/Fungicida/Acaricida) |
| `Produto` | Entidade central; liga a categoria/subcategoria, unidade, NCM |
| `ProdutoFornecedor` | Vínculo produto ↔ fornecedor |
| `ProdutoTributacao` | Dados fiscais do produto |
| `ProdutoDefensivoCultura` | Vínculo defensivo ↔ cultura (usado por `mip`/receituário agronômico) |
| `ProdutoDocumento` | Anexos do produto |
| `DimensaoVariante`, `ProdutoAtributo` | Variantes/atributos do produto |

### Hierarquia Categoria → Subcategoria
No formulário de produto, selecionar uma Categoria filtra dinamicamente (via JavaScript, usando atributo `data-categoria-id` no widget customizado `SubCategoriaSelect`) as opções de Subcategoria para mostrar só as pertencentes àquela categoria. Criar uma Subcategoria exige selecionar a categoria pai. Listagem em `/produtos/subcategorias/` mostra categoria, código, nome e status de cada subcategoria. `categoria.subcategorias.all()` retorna as subcategorias de uma categoria (related_name).

## Rotas de referência (amostra)
`dashboard/`, `tipos-produto/`, `tipos-produto/cadastrar/`, `tipos-produto/<id>/editar/`, `unidades/`, `unidades/cadastrar/`, `unidades/ajax/criar/`, `ncm/buscar/`.

## Integrações
- `cadastros.NCM` — vínculo fiscal do produto (ver `docs/2_MODULOS/MODULO_CADASTROS.md`).
- `estoque` — `Produto.estoque_atual` calculado a partir de lotes/movimentações (ver `docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md`).
- `mip` — `ProdutoDefensivoCultura` alimenta recomendações de defensivo por cultura.

## Permissões e isolamento
Filtro por `empresa` obrigatório em toda consulta de produto/categoria/subcategoria.

## Referências
- `produtos/models.py`, `produtos/urls.py`, `produtos/widgets.py` (`SubCategoriaSelect`)
