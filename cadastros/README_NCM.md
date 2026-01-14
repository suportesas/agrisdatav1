# NCM (Nomenclatura Comum do Mercosul)

Este módulo adiciona o cadastro de NCMs (usados na emissão de notas fiscais) com CRUD, validação e comando para importar a tabela oficial.

Comando para importar CSV:

python manage.py import_ncm --path /caminho/para/ncm.csv

ou baixar via URL:

python manage.py import_ncm --url "https://exemplo.org/ncm.csv"

Opções:

- `--replace` : remove NCMs que não estão no arquivo (útil para sincronizar com a fonte oficial)
- `--dry-run` : não aplica alterações, apenas mostra resultados

Formato esperado do CSV: colunas `codigo` e `nome` (opcional `cest`).

Fixtures de desenvolvimento:

- `cadastros/fixtures/ncm_small.json` — pequeno conjunto para carregar em ambiente de desenvolvimento (`python manage.py loaddata ncm_small.json`).

Integração com produtos e validações de NF-e pode ser adicionada numa etapa posterior, conforme você solicitou.
