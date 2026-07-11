# Migracao de Conteudo Legado

Owner: Documentacao
Status: Approved
Last Updated: 2026-07-10
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

## Execucao (2026-07-10)
Migracao executada: os ~130 documentos soltos da raiz e dos apps foram movidos para as pastas numeradas acima ou consolidados por tema em `docs/archive/` (documentos historicos de features ja concluidas, ver `docs/archive/README.md`). `docs/ROLES.md` foi mesclado em `6_OPERACIONAL/ROLES_PERMISSOES.md`. Apenas `README.md` e `CLAUDE.md` permanecem na raiz do repositorio.

## Proximo passo
Detalhar os modulos ainda em esqueleto (`2_MODULOS/MAPA_COBERTURA_MODULOS.md`) e revisar periodicamente `docs/archive/` para aposentar de vez conteudo sem valor de referencia.
