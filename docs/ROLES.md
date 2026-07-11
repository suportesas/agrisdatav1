# Roles e Gerenciamento de Permissões

Visão geral do novo módulo de Roles (Funções) por Empresa e como usá-lo.

## O que foi adicionado
- Modelo `Role` em `empresas.models`, vinculado a uma `Empresa` e a um `auth.Group` do Django.
- Campo `roles` (ManyToMany) em `usuarios.models.Usuario` para atribuição de funções.
- Management command `manage.py seed_roles` para criar funções padrão (Proprietário, Almoxarife, Operacional do Campo, Financeiro, Gerente, Vendedor) para todas as empresas.
- Views e endpoints JSON para listar roles e ler/atualizar permissões (`empresas.views.role_list` e `empresas.views.role_permissions`).
- Templates MVP: `empresas/roles_list.html` e partial `_roles_table.html` com JS para carregar e salvar permissões via AJAX.

## Passos para instalar / migrar
1. Criar migrações e aplicá-las:

```bash
python manage.py makemigrations
python manage.py migrate
```

2. Executar seed inicial de roles (cria roles padrão para cada empresa existente):

```bash
python manage.py seed_roles
```

3. Acessar a interface de Roles (usuário admin da empresa):
- URL: `/empresas/roles/` (necessário estar logado e ter uma empresa)
   - A partir de `Minha Empresa` há um botão **Gerenciar Funções (Permissões)** que abre a tela de roles.   - A lista utiliza um layout em cartões (estilo similar a `Fornecedores`) com filtros e busca; cada cartão exibe nome, descrição, data de criação e ações (Editar / Permissões).   - É possível **Criar** novas funções via UI (`/empresas/roles/novo/`) e então editar permissões.
## Uso (MVP)
- Escolha uma função na lista.
- Clique na função para carregar a tabela de permissões (Módulo | Cadastrar | Editar | Excluir | Visualizar).
- Marque/desmarque checkboxes e clique em **Salvar** para aplicar as permissões à função.

As permissões são armazenadas no `auth.Group` associado à `Role`. Quando um usuário recebe a `Role` a partir do campo `roles`, ele herda as permissões do `Group`.

## Observações e próximos passos recomendados
- Atualmente o frontend é um MVP; adicionamos suporte a **Templates de Permissões** (salvar/exportar e aplicar templates) e **Aplicação em Massa (bulk)** via endpoints JSON, além do registro de auditoria para aplicações.
- Endpoints implementados (exemplos):
  - `POST /empresas/roles/<role_id>/permissions/save-template/` — salva um template a partir das permissões atuais da role.
  - `GET /empresas/roles/templates/` — lista templates da empresa.
  - `POST /empresas/roles/<role_id>/permissions/apply-template/` — aplica um template a uma role.
  - `POST /empresas/roles/templates/apply-bulk/` — aplica um template a múltiplas roles.

- Considerar adicionar UI para importação de JSON com validação e pagina para gerenciar templates (CRUD) via frontend.

**Rodando E2E localmente / em CI**

- Para executar os testes E2E localmente com Playwright:
  1. Instale dependências: `pip install -r requirements.txt` (inclui `playwright` e `pytest-playwright`).
  2. Instale navegadores Playwright: `python -m playwright install --with-deps`.
  3. Execute os testes E2E com a variável de ambiente necessária (permite operações de banco durante o live_server):
     - PowerShell: `$env:DJANGO_ALLOW_ASYNC_UNSAFE='1'; pytest tests/e2e -q`
     - Bash: `DJANGO_ALLOW_ASYNC_UNSAFE=1 pytest tests/e2e -q`

- CI: adicionei o workflow GitHub Actions `.github/workflows/e2e-playwright.yml` que instala dependências, executa migrações e roda os testes unitários e E2E (configura `DJANGO_ALLOW_ASYNC_UNSAFE: '1'`).


### Usando PostgreSQL para pesquisa sem acentos (recomendado)

Para tirar proveito do `unaccent` (buscas insensíveis a acentos) e dos índices de expressão, recomendamos usar PostgreSQL em desenvolvimento e produção.

Opções locais:
- Instalar Postgres no Windows: https://www.postgresql.org/download/windows/ ou via choco: `choco install postgresql`.
- Usar Docker (recomendado se não quiser instalar localmente):
  - `docker run --name erp-postgres -e POSTGRES_USER=erp_user -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=erp_agricola -p 5432:5432 -d postgres:16`

Depois, a aplicação detecta Postgres via variável de ambiente `PG_NAME` (ou `PG_USER`, `PG_PASSWORD` etc.). Exemplo de variáveis para dev (PowerShell):

```powershell
$env:PG_NAME='erp_agricola'
$env:PG_USER='erp_user'
$env:PG_PASSWORD='secret'
$env:PG_HOST='127.0.0.1'
$env:PG_PORT='5432'
```

Recomendações de migração de dados:
- Pequeno dataset: usar `python manage.py dumpdata > data.json`, apontar Django para Postgres, rodar migrations e `python manage.py loaddata data.json`.
- Dataset maior: usar `pgloader` ou outra ferramenta dedicada para migrar do SQLite/MySQL para Postgres.

Notas:
- A migration que criei (`cadastros/migrations/0032_unaccent_and_indexes.py`) habilita `unaccent` e cria índices `lower(unaccent(descricao))` para acelerar buscas.
- Em produção, crie um backup do banco antes da migração e agende janela de manutenção para aplicar índices concurrentes sem bloquear o banco.


**Se quiser, prossigo agora com:** depurar os erros de E2E que identifiquei (elementos não visíveis / erros JS), ou melhorar o workflow para rodar apenas os E2E em PRs para a branch `feature/roles-permissions`.