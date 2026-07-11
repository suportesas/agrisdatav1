Owner: Time patrimonio
Status: Draft — a expandir
Last Updated: 2026-07-10
Scope: patrimonio (`/patrimonio/`)

## Visão geral
Controle patrimonial: cadastro de bens, depreciação, movimentação entre localizações/responsáveis e auditoria física periódica. Pode originar um item de patrimônio a partir de um veículo da frota (`patrimonio_from_veiculo`).

## Entidades principais
| Entidade | Papel |
|---|---|
| `Patrimonio` | Bem patrimonial |
| `PatrimonioDepreciacaoHistorico` | Histórico de cálculo de depreciação do bem |
| `PatrimonioMovimentacao` | Movimentação (transferência de local/responsável) |
| `PatrimonioAuditoria` / `PatrimonioAuditoriaItem` | Auditoria física periódica e seus itens conferidos |

## Rotas principais (`/patrimonio/`)
`novo/`, `<pk>/`, `<pk>/editar/`, `<pk>/excluir/`, `veiculo/<vehicle_pk>/exportar/` (cria patrimônio a partir de veículo — ver `docs/2_MODULOS/MODULO_FROTA.md`), `<pk>/movimentacao/nova/`, `relatorio/` (+ `pdf/`, `excel/`), `auditorias/`, `auditorias/nova/`.

## Integrações
- `frota` — exportação de veículo para patrimônio.

## A expandir
Regra de cálculo de depreciação (método, periodicidade) e fluxo completo de auditoria (divergências, conciliação) ainda não documentados aqui.

## Referências
- `patrimonio/models.py`, `patrimonio/urls.py`
