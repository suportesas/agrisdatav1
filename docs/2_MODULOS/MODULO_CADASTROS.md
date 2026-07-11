Owner: Time cadastros
Status: Approved
Last Updated: 2026-07-10
Scope: cadastros (`/cadastros/`)

# Módulo Cadastros

## Visão geral
Cadastros de apoio usados pelos demais módulos: fazendas, clientes, fornecedores, produtores, transportadoras, CFOP e NCM. Praticamente todo outro módulo depende de entidades daqui (ex: `compras` referencia `Fornecedor`, `faturamento` referencia `CFOP`/`NCM`/`Cliente`).

## Entidades principais
| Entidade | Papel |
|---|---|
| `Fazenda` (+ `EnderecoFazenda`, `ContatoFazenda`, `ContaBancariaFazenda`, `DocumentoFazenda`) | Propriedade rural vinculada à empresa; hub de dados de endereço/contato/documentos |
| `Cliente`, `Fornecedor` (+ `DocumentoFornecedor`) | Cadastros comerciais |
| `Moeda` | Moedas suportadas (usado por `faturamento`/`exportacao` para operações multi-moeda) |
| `NCM` | Nomenclatura Comum do Mercosul, usada na emissão de NF-e |
| CFOP, transportadoras, produtores | Cadastros fiscais/logísticos de apoio |

### NCM (Nomenclatura Comum do Mercosul)
CRUD com validação + comando de importação da tabela oficial:
```bash
python manage.py import_ncm --path /caminho/para/ncm.csv
python manage.py import_ncm --url "https://exemplo.org/ncm.csv"
```
Opções: `--replace` (remove NCMs que não estão no arquivo, sincroniza com a fonte oficial), `--dry-run` (não aplica, só mostra o resultado). CSV esperado com colunas `codigo`, `nome` (opcional `cest`). Fixture de desenvolvimento: `cadastros/fixtures/ncm_small.json` (`python manage.py loaddata ncm_small.json`).

## Rotas de referência (amostra)
`fazendas/`, `fazendas/nova/`, `fazendas/<id>/`, `fazendas/<id>/editar/`, `fazendas/<id>/excluir/`, `fazendas/<fazenda_pk>/enderecos/novo/`, `fazendas/<fazenda_pk>/contatos/novo/`, `api/buscar-cnpj/`, `api/buscar-cep/`, `api/buscar-geolocalizacao/` (autocomplete/consulta externa usados nos formulários de fazenda/cadastro).

## Permissões e isolamento
Filtro por `empresa` obrigatório em toda consulta — ver padrão de tenant enforcement em `CLAUDE.md` raiz ("Multi-tenant isolation").

## Referências
- `cadastros/models.py`, `cadastros/urls.py`
- Comando `import_ncm` (`cadastros/management/commands/import_ncm.py`)
