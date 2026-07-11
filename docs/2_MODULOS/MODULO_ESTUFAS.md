Owner: Time estufas
Status: Draft — a expandir
Last Updated: 2026-07-10
Scope: estufas (`/estufas/`)

## Visão geral
Gestão de estufas/viveiros: lotes de mudas, transplantio para talhão, aplicações e monitoramento fitossanitário dentro da estufa, e controle de perdas.

## Entidades principais
| Entidade | Papel |
|---|---|
| `Estufa` | Unidade física de estufa/viveiro |
| `LoteMuda` | Lote de mudas em produção na estufa, com status progressivo (`avancar-status`) |
| `PerdaEstufa` | Registro de perda dentro de um lote |
| `AplicacaoEstufa` | Aplicação (defensivo/nutriente) em um lote |
| `MonitoramentoEstufa` | Monitoramento periódico da estufa |
| `Transplantio` / `ReplantioTalhao` | Movimentação da muda da estufa para o talhão definitivo (ou replantio) |

## Rotas principais (`/estufas/`)
`nova/`, `<pk>/`, `<pk>/editar/`, `dashboard/`, `lotes/`, `lotes/novo/`, `lotes/<pk>/`, `lotes/<pk>/avancar-status/`, `lotes/<lote_pk>/perdas/nova/`.

## Integrações
- `cadastros.Fazenda`/talhão — destino do transplantio.
- `mip` — monitoramento fitossanitário pode se relacionar com pragas/defensivos cadastrados lá.

## A expandir
Estados/transições completos de `LoteMuda`, regras de cálculo de perda vs. produção, ainda não documentados aqui.

## Referências
- `estufas/models.py`, `estufas/urls.py`
