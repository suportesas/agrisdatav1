Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: comando seed_pragas e pre-cadastro automatico de pragas por empresa

Este é um registro histórico consolidado, mesclado a partir de 8 arquivos originais: `SEED_PRAGAS_DOCS.md`, `SEED_PRAGAS_README.md`, `SUMARIO_EXECUTIVO_SEED_PRAGAS.md`, `GUIA_USO_SEED_PRAGAS.md`, `DIAGRAMA_SEED_PRAGAS.md`, `CHECKLIST_SEED_PRAGAS.md`, `RESUMO_SEED_PRAGAS.md` e `IMPLEMENTACAO_COMPLETA_SEED_PRAGAS.md` (preservados em `fontes/`). Todos descrevem a mesma feature sob ângulos diferentes (técnico, executivo, guia de uso, diagrama, checklist).

## O que foi implementado

Sistema de pré-cadastro automático de pragas agrícolas para o modelo `cadastros.Praga`, multi-tenant (uma cópia de dados por `empresa`, sem compartilhamento).

- **Automação via signal Django**: em `empresas/signals.py`, um handler `seed_pragas_on_create()` (`@receiver(post_save, sender=Empresa)`) chama `seed_pragas_for_company(instance)` de `cadastros/pragas_seed.py` sempre que uma nova `Empresa` é criada (`created=True`). Envolvido em `try/except` — se falhar, não bloqueia a criação da empresa.
- **Lista de seed**: `cadastros/pragas_seed.py` contém a constante `PRAGAS_SEED`, uma lista de dicts com `nome_comum` e `nome_cientifico` (o campo `tipo` foi usado numa versão inicial e depois removido — ver "Divergência entre fontes" abaixo).
- **Idempotência**: a criação usa `UniqueConstraint(fields=['empresa', 'nome_comum'], name='unique_praga_empresa')` no modelo `Praga`, então rodar o seed de novo não duplica registros.
- **Management command manual**: `python manage.py seed_pragas` com opções `--empresa-id <id>`, `--all`, `--list` (e, numa das fontes, `--skip-existing False` para forçar recriação).
- **Isolamento multi-tenant**: `Praga.empresa` é `ForeignKey('empresas.Empresa', on_delete=CASCADE)`; editar/deletar pragas em uma empresa não afeta outras.
- **Interface**: botão "Como Fazer?" com modal de 5 passos adicionado em `cadastros/templates/cadastros/praga/praga_list.html` para orientar novos usuários.
- **Scripts de validação** (fora do Django, na raiz do projeto na época): `verificar_seed_pragas.py` e `testar_seed_pragas.py` — não fazem parte do management command, eram scripts ad-hoc de verificação/teste manual.

### Composição final do seed: 88 pragas

| Categoria | Quantidade |
|---|---|
| Insetos | 42 |
| Fungos | 20 |
| Vírus | 8 |
| Bactérias | 6 |
| Ácaros | 5 |
| Nematoides | 3 |
| Moluscos | 3 |
| Outros | 4 |

## Divergência entre fontes (contexto histórico)

`SEED_PRAGAS_README.md` descreve uma versão anterior/diferente do seed: ~40 pragas, com um campo `tipo` (Inseto, Fungo, Vírus, etc.) por praga, e data **2026-02-04**. Os demais 7 arquivos descrevem a versão final: 88 pragas, **sem** campo `tipo` no seed (removido — "Remover campo 'tipo' não utilizado do seed" aparece no checklist), datados **2025-02-04**. As datas nas próprias fontes são inconsistentes entre si (2025 vs 2026 para o "mesmo" trabalho) — preservadas aqui como registradas nos originais, sem tentativa de correção. A leitura mais provável é que `SEED_PRAGAS_README.md` documenta um estado intermediário/anterior do sistema, e os demais documentam a expansão final para 88 pragas. Se for necessário confirmar o estado atual do seed, verificar diretamente `cadastros/pragas_seed.py`.

## Quando foi feito

Implementação e documentação registradas majoritariamente em **04/02** (ano inconsistente entre fontes — ver acima).

## Status final

Todos os documentos convergem em: sistema **100% implementado e pronto para produção**, testado via scripts de verificação (`verificar_seed_pragas.py` retornando "TODAS AS VERIFICAÇÕES PASSARAM"), com isolamento multi-tenant validado manualmente (edição/deleção em uma empresa não vaza para outra).

## Pendências / avisos ainda relevantes

Melhorias futuras listadas nos documentos-fonte como **não implementadas** (Phase 2/3/4, mencionadas de forma consistente em `SUMARIO_EXECUTIVO_SEED_PRAGAS.md`, `GUIA_USO_SEED_PRAGAS.md` e `IMPLEMENTACAO_COMPLETA_SEED_PRAGAS.md`):

- Importação/exportação de pragas via CSV.
- Recomendações de controle por praga (dependência cruzada com o cluster MIP — ver `docs/archive/mip/README.md`, que também tem um TODO pendente de integração com `RecomendacaoDefensivo`).
- Alertas sazonais automáticos.
- Histórico de alterações de pragas.
- Relatórios de pragas por talhão.
- Integração com operações/controle de pragas.
- Painel de configuração para seed customizado por plano (Pequeno/Médio/Grande) — mencionado como ideia não implementada.

Os scripts `verificar_seed_pragas.py` e `testar_seed_pragas.py` citados nas fontes não foram localizados/verificados como parte deste trabalho de consolidação — confirmar se ainda existem no repo antes de depender deles.

Detalhes de UI, exemplos de shell e diagramas ASCII completos (redundantes entre os 8 arquivos) permanecem nos originais em `fontes/`, especialmente `DIAGRAMA_SEED_PRAGAS.md` para o fluxo visual completo e `SEED_PRAGAS_DOCS.md` para a lista completa de pragas por categoria.
