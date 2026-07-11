Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Índice da documentação histórica

# Documentação Histórica

Registros de features já concluídas, consolidados por tema a partir de dezenas de documentos soltos que existiam na raiz do repositório antes da reorganização em `docs/`. **Nada aqui deve ser tratado como descrição do comportamento atual do sistema** — para o estado atual, use `docs/2_MODULOS/`, `docs/3_FLUXOS_PROCESSOS/`, `docs/4_TECNICO/` etc. Cada pasta abaixo tem um `README.md` (ou `INDEX.md`) consolidado e, quando aplicável, uma subpasta `fontes/` com os arquivos originais preservados via `git mv`.

| Pasta | Tema |
|---|---|
| [`rf-055/`](rf-055/README.md) | RF-055 (alertas de estoque min/max em 3 níveis) e RF-056 (inventário cíclico ABC) |
| [`seed-pragas/`](seed-pragas/README.md) | Seed automático de pragas por empresa (signal + comando `seed_pragas`) |
| [`modos-operacao-compra/`](modos-operacao-compra/README.md) | Modos SIMPLES/FORMAL/HIBRIDO em compras e estoque |
| [`api-keys-seguranca/`](api-keys-seguranca/README.md) | Correção de chaves Supabase expostas no frontend + rollout parcial de RLS |
| [`mip/`](mip/README.md) | Monitoramento Integrado de Pragas — inclui TODO não resolvido (NED hardcoded) |
| [`fase3-relatorios/`](fase3-relatorios/README.md) | Relatórios avançados de estoque ("Fase 3") |
| [`estoque-unidades-medida/`](estoque-unidades-medida/README.md) | Bug de autofill de unidade de medida em compras |
| [`parcelamento-inteligente/`](parcelamento-inteligente/README.md) | Geração automática de parcelas em Contas a Pagar |
| [`defensivos-pragas/`](defensivos-pragas/README.md) | Seed de defensivos + propostas de motor de recomendação (parcialmente não implementadas) |
| [`supabase-storage-frontend/`](supabase-storage-frontend/README.md) | Auth frontend Supabase + Storage para imagens de safra |
| [`estoque-relatorios/`](estoque-relatorios/README.md) | Refactor de movimentação de estoque (lote vs. sem lote) + relatórios PDF/Excel/e-mail |
| [`armador-navio-logistica-maritima/`](armador-navio-logistica-maritima/README.md) | Cadastro de Armador/Navio e reorganização do menu "Logística Marítima" |
| [`rh-legado-cadastros/`](rh-legado-cadastros/README.md) | RH como era implementado dentro de `cadastros`, antes da extração para o app `rh/` |
| [`embalagem-planejamento-v1/`](embalagem-planejamento-v1/INDEX.md) | Planejamento pré-implementação do módulo embalagem, escrito para o repositório anterior (agrisdatav1) |
| [`diversos/`](diversos/README.md) | Documentos históricos avulsos sem cluster próprio (inclui nota sobre `ANALISE_STATUS_PRD.md`, desatualizado) |

## Regra
Documentos aqui têm `Status: Deprecated` e não são atualizados para refletir o código atual — servem como registro do que foi decidido/construído em um dado momento. Se uma informação aqui ainda for relevante hoje, ela deve estar (ou ser adicionada) em um documento `Approved`/`In Review` fora de `archive/`.
