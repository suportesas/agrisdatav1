Owner: Time embalagem
Status: Draft — a expandir
Last Updated: 2026-07-10
Scope: etiquetas_avulsas (`/etiquetas-avulsas/`)

## Visão geral
Geração e impressão de etiquetas avulsas (fora do fluxo normal de pallet de uma ordem de embalagem), organizadas em lotes. Complementa `embalagem` (ver `docs/2_MODULOS/MODULO_EMBALAGEM.md`) para casos em que a etiqueta precisa ser reimpressa ou emitida avulsa. Também expõe uma API própria (`etiquetas/v1/`, ver `etiquetas_avulsas/api/urls.py`).

## Entidades principais
| Entidade | Papel |
|---|---|
| `LoteEtiquetaAvulsa` | Lote de etiquetas avulsas geradas de uma vez |
| `EtiquetaAvulsa` | Etiqueta individual dentro do lote; pode ser editada ou cancelada |

## Rotas principais (`/etiquetas-avulsas/`)
`lotes/`, `lotes/novo/`, `lotes/<pk>/`, `lotes/<pk>/adicionar/` (adicionar pallets ao lote), `lotes/<pk>/concluir/`, `lotes/<pk>/imprimir/` (PDF do lote), `etiquetas/<pk>/pdf/` (PDF individual), `etiquetas/<pk>/editar/`, `etiquetas/<pk>/cancelar/`.

## Referências
- `etiquetas_avulsas/models.py`, `etiquetas_avulsas/urls.py`, `etiquetas_avulsas/api/urls.py`
- Também referenciado como fonte do planejamento de etiquetas: `docs/PLANO_ETIQUETAS_PALLETS.md`
