# Migracao de Conteudo Legado

Owner: Documentacao
Status: Draft
Last Updated: 2026-07-01
Scope: Consolidacao de arquivos antigos

## Objetivo
Mapear documentos ja existentes para a nova estrutura, sem perda de historico.

## Regras de migracao
- Nao apagar arquivos legados no inicio.
- Priorizar mover ou referenciar por link.
- Quando consolidar conteudo, manter referencia de origem.

## Mapeamento inicial
| Origem atual | Destino recomendado |
|---|---|
| docs/fase0 | docs/10_FASES_ROADMAP |
| docs/fase1 | docs/10_FASES_ROADMAP |
| docs/fase2 | docs/10_FASES_ROADMAP |
| docs/ROLES.md | docs/6_OPERACIONAL |
| ARQUITETURA_*.md na raiz | docs/1_ARQUITETURA |
| FLUXO_*.md na raiz | docs/3_FLUXOS_PROCESSOS |
| GUIA_*.md na raiz | docs/6_OPERACIONAL |
| TESTES_*.md na raiz | docs/5_DESENVOLVIMENTO |
| DEPLOY_*.md na raiz | docs/9_DEPLOYMENT |

## Proximo passo
Executar consolidacao por lotes pequenos e validar links apos cada lote.
