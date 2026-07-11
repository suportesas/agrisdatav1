Owner: Time drawback
Status: Draft — a expandir
Last Updated: 2026-07-10
Scope: drawback (`/drawback/`)

## Visão geral
Controle do regime aduaneiro de Drawback (suspensão/isenção de tributos na importação de insumos usados em produção destinada à exportação): Atos Concessórios, entradas e saídas de mercadoria vinculadas ao Ato. Ver `docs/1_ARQUITETURA/prd_drawback.md` para o PRD completo do módulo.

## Entidades principais
| Entidade | Papel |
|---|---|
| `AtoConcessorio` | Ato Concessório de Drawback — documento raiz do regime |
| `DrawbackProdutoAC` | Produto vinculado a um Ato Concessório (quantidade autorizada) |
| `EntradaDrawback` | Entrada de mercadoria sob o Ato (com opção de anulação) |
| `SaidaDrawback` | Saída de mercadoria sob o Ato (com opção de anulação) |

## Rotas principais (`/drawback/`)
`ac/novo/`, `ac/<pk>/`, `ac/<pk>/editar/`, `ac/<ac_pk>/entrada/nova/`, `entrada/<pk>/anular/`, `ac/<ac_pk>/saida/nova/`, `saida/<pk>/anular/`, `ac/<ac_pk>/importar/` (+ `importar/confirmar/`, `modelo/<tipo>/` — importação via XLSX).

## A expandir
Regras de saldo/consumo do Ato Concessório, prazos legais e integração com `faturamento`/`exportacao` ainda não documentados aqui — consultar `drawback/models.py` e o PRD antes de qualquer alteração de regra fiscal.

## Referências
- `drawback/models.py`, `drawback/urls.py`
- `docs/1_ARQUITETURA/prd_drawback.md`
