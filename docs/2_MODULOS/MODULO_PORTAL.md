Owner: Time portal
Status: Draft — a expandir
Last Updated: 2026-07-10
Scope: portal (`/portal/cliente/`)

## Visão geral
App `portal` implementa especificamente o **portal do cliente** (`app_name = 'portal_cliente'`): login próprio, dashboard, consulta de financeiro (contas a receber) e documentos. Não define `models.py` próprio — consome dados de outros apps (`financeiro`, `faturamento`, etc.) filtrados pelo cliente autenticado.

Não confundir com os demais portais de usuário restrito do sistema, que vivem em outros apps e são incluídos separadamente em `core/urls.py`:
| Prefixo | App que implementa | Público |
|---|---|---|
| `/portal/cliente/` | `portal` | Clientes |
| `/portal/fornecedor/` | `compras` (`compras.portal_fornecedor_urls`) | Fornecedores |
| `/portal/produtor/` | `cadastros` (`cadastros.portal_produtor_urls`) | Produtores rurais |
| `/portal/motorista/` | `frota` (`frota.portal_motorista_urls`) | Motoristas |
| `/portal/campo/` | `cadastros` (`cadastros.portal_campo_urls`) | Usuários `PROD` (portal do campo / PWA) |

## Rotas principais (`/portal/cliente/`)
`login/`, `logout/`, `` (dashboard), `financeiro/`, `financeiro/<pk>/`, `documentos/`.

## Referências
- `portal/views.py`, `portal/urls.py`
- `core/urls.py` (mapa completo dos portais de usuário restrito)
