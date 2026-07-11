# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development server
python manage.py runserver

# Database migrations
python manage.py makemigrations <app_name>
python manage.py migrate

# Tests (Playwright E2E — requires live server)
pytest tests/e2e/                         # all E2E tests
pytest tests/e2e/test_vehicle_flow.py     # single test file
pytest tests/e2e/ -k "test_cfop"         # tests matching keyword

# Unit tests (Django test runner)
python manage.py test cadastros
python manage.py test financeiro.tests

# Static files
python manage.py collectstatic --noinput

# Shell
python manage.py shell
```

### Custom management commands

```bash
# Data seeding
python manage.py seed_plano_contas [--empresa-id N] [--force]
python manage.py seed_roles
python manage.py seed_pragas
python manage.py import_cfop
python manage.py import_ncm
python manage.py popula_categorias_agricolas

# Maintenance
python manage.py recalcular_estoque
python manage.py auditar_estoque
python manage.py atualizar_planos
python manage.py sincronizar_superuser_global

# Generate FIELD_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Architecture

### Multi-tenant isolation

Every model scoped to a company has `empresa = FK('empresas.Empresa')`. All views must filter by `request.user.empresa`. Superusers (`is_superuser=True`) bypass this and see all companies. The middleware stack (`core/middleware/`) enforces access per user type before views are reached.

Tenant enforcement pattern:
```python
@login_required
def my_view(request):
    empresa = request.user.empresa
    qs = MyModel.objects.filter(empresa=empresa)
```

### User types and their access scope

`usuarios.Usuario` extends `AbstractUser` with a `tipo` field: `ADMIN`, `GERENTE`, `FUNC`, `PROD`, `VENDEDOR`, `FINANCEIRO`. Middleware routes `PROD` users to a restricted portal; supplier/client users are limited to their own portal URLs.

### App structure

Each Django app follows the pattern: `models.py → forms.py → views.py → urls.py → templates/<app>/`. URL namespaces are always declared with `app_name = '<app>'` and included in `core/urls.py` as `path('<prefix>/', include(('<app>.urls', '<app>')))`.

There are 27 apps. The canonical, kept-up-to-date list of apps with URL prefixes and descriptions is the "Módulos do Sistema" table in `README.md` (root) — functional documentation per app lives in `docs/2_MODULOS/MODULO_<APP>.md` (see `docs/2_MODULOS/MAPA_COBERTURA_MODULOS.md` for which ones are verified vs. still skeleton). Frequently touched apps:
- `financeiro/` — contas a pagar/receber, parcelas, pagamentos, fluxo de caixa (see `financeiro/CLAUDE.md`)
- `plano_contas/` — contas contábeis hierárquicas, centros de custo
- `faturamento/` — NF-e, Invoice de exportação, CT-e, MDF-e, Packing List
- `compras/` — solicitações, cotações, pedidos, recebimentos, XML NF-e import (see `docs/2_MODULOS/MODULO_COMPRAS.md`)
- `estoque/` — movimentações, lotes, armazéns, inventário cíclico (see `docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md`)
- `cadastros/` — fazendas, clientes, fornecedores, produtores, transportadoras, CFOP, NCM
- `produtos/` — catálogo, categorias/subcategorias, tributação
- `vendas/` — pedidos de venda
- `exportacao/` — bookings, armadores, portos, ordens de coleta
- `embalagem/` — ordens, pallets, romaneios
- `rh/` — funcionários, funções, riscos ambientais (separate app since migration `cadastros/migrations/0112_remove_rh_models.py` — not part of `cadastros` anymore)

### Templates

Global base: `templates/base.html` (Bootstrap 5.3.2 + Bootstrap Icons 1.11.1 + Google Fonts Inter). Sidebar: `templates/sidebar.html`. App-specific templates live in `<app>/templates/<app>/`.

Design system variables (in `static/css/base.css`):
- Primary: `#1a7a3c` (green, matches the sidebar's `--sb-green`), Accent: `#2563eb` (blue)
- Sidebar (`static/css/sidebar-modern.css`) uses a dark near-black/dark-green theme (`--sb-bg: #10231a`) with the same green accent
- Pastel status tokens (`--pastel-{green,blue,orange,red,gray}-{bg,text}`) drive badges (soft pill style) and stat-card icons
- `--radius-card: 14px`, `--shadow-card` neutral (no color tint)
- Font: Inter. No Tailwind — Bootstrap + custom CSS only.

### Forms

All `ModelForm`s accept `empresa=` as a kwarg in `__init__` and filter related querysets by that empresa. Example:
```python
def __init__(self, *args, empresa=None, **kwargs):
    super().__init__(*args, **kwargs)
    if empresa:
        self.fields['fornecedor'].queryset = Fornecedor.objects.filter(empresa=empresa)
```
Widgets always use Bootstrap 5 classes: `form-control`, `form-select`, `form-check-input`.

### Soft-delete

Models use `ativo = BooleanField(default=True)` instead of physical deletion. Toggle views use POST (never HTTP DELETE). Before deactivating, check for dependent active children.

### Migrations

Migration files in `financeiro/` use the prefix `10000_` (to avoid conflicts with the base `0001_` sequence). When creating migrations that depend on `plano_contas`, ensure `dependencies` includes `('plano_contas', '0001_initial')`.

### AJAX

`JsonResponse({'results': [{'id': x, 'text': str}]})` — no DRF for internal autocomplete endpoints. DRF (`rest_framework`) is installed for the external API but not used heavily in internal views.

### Feature flags

```python
from core.feature_flags import is_feature_enabled
if is_feature_enabled('FINANCEIRO_RENEGOCIACAO'):
    ...
```
Flags are defined in `FEATURE_FLAGS` in `settings.py`, controlled via `.env` vars prefixed `FF_`.

### Supabase / Storage

File uploads go to Supabase Storage buckets when `SUPABASE_URL` is set; otherwise fall back to `MEDIA_ROOT`. Use `core.supabase_config` for the client. Do not use `BinaryField` for certificates — see `faturamento/models.py` for the pattern.

### Encryption

Sensitive string fields (API tokens, passwords stored in DB) use Fernet encryption via helpers in `faturamento/encryption.py`. Requires `FIELD_ENCRYPTION_KEY` in `.env`.

## Key .env variables

```
DEBUG=True
SECRET_KEY=...
ALLOWED_HOSTS=localhost,127.0.0.1
PG_NAME=  PG_HOST=  PG_USER=  PG_PASSWORD=  PG_PORT=5432
SUPABASE_URL=  SUPABASE_ANON_KEY=  SUPABASE_SERVICE_ROLE_KEY=
FIELD_ENCRYPTION_KEY=   # generate with Fernet.generate_key()
FF_<FLAG_NAME>=true     # enable feature flags
```

SQLite is used automatically when PostgreSQL env vars are absent (development only).

## Further documentation

Full project documentation lives in `docs/` — see `docs/README.md` for the index and `docs/NAVIGATION.md` for navigation by profile (technical / business / operations). Historical, point-in-time implementation notes for already-completed features are archived under `docs/archive/` (consolidated by topic, not meant to describe current behavior).
