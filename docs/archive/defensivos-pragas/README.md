Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Seed de defensivos agrícolas (MAPA) por empresa e análises/propostas de recomendação automática de defensivos por praga (receituário agronômico)

# Defensivos agrícolas: seed automático e propostas de recomendação

Registro histórico consolidado, mesclado a partir de 6 arquivos originais:
- `ANALISE_RECEITUARIO_AGRONOMICO.md`
- `ANALISE_RECOMENDACOES_DEFENSIVOS.md`
- `IMPLEMENTACAO_DEFENSIVOS.md`
- `RESUMO_DEFENSIVOS.md`
- `RESUMO_COMPLETO_PRAGAS_DEFENSIVOS.md`
- `GUIA_RAPIDO_PRAGAS_DEFENSIVOS.md`

Estes arquivos misturam dois assuntos distintos que compartilham o mesmo domínio (defensivos/pragas): (A) o sistema de **seed automático de 88 defensivos por empresa**, que foi efetivamente implementado; e (B) **análises/propostas** de um sistema de **recomendação automática de defensivo por praga** e de **receituário agronômico**, que eram brainstorms de arquitetura no momento em que os documentos foram escritos (perguntas em aberto do tipo "qual opção você prefere?" ao final de cada um).

## A. Seed automático de defensivos (implementado — 2025-02-04)

Sistema que popula automaticamente cada empresa com **88 defensivos agrícolas** reais registrados no MAPA (Ministério da Agricultura), replicando o mesmo padrão já usado para o seed de pragas (ver cluster `docs/archive/seed-pragas/`, tratado separadamente).

### O que foi implementado
- `produtos/defensivos_seed.py` — lista `DEFENSIVOS_SEED` com 88 defensivos (Herbicidas 25, Inseticidas 25, Fungicidas 20, Acaricidas 10, Nematicidas 5, Formicidas 3, Rodenticidas 2, Bactericidas 3), cada um com nome comercial, ingrediente ativo, classe agronômica, classe toxicológica, classe ambiental, modo de aplicação, fabricante e número de registro MAPA; função `seed_defensivos_for_empresa(empresa)` (idempotente via `get_or_create`) e `listar_defensivos_seed()`.
- `empresas/signals.py` — signal `post_save` em `Empresa` (`seed_defensivos_on_create`) que dispara o seed automaticamente para empresas novas, com falha silenciosa (não bloqueia a criação da empresa se o seed falhar).
- `produtos/management/commands/seed_defensivos.py` — comando `python manage.py seed_defensivos` com flags `--all`, `--empresa-id <id>`, `--list`.
- Scripts auxiliares (à época, na raiz do repo, não confirmados como ainda existentes): `importar_defensivos_empresas_existentes.py`, `verificar_defensivos.py`.
- Isolamento multi-tenant garantido por `Produto.empresa` (FK obrigatória, CASCADE) — cada empresa tem seu próprio conjunto de 88 defensivos, sem overlap.

### Como usar (referência histórica)
```bash
python manage.py seed_defensivos --all              # todas as empresas
python manage.py seed_defensivos --empresa-id 5      # empresa específica
python manage.py seed_defensivos --list              # listar os 88 defensivos
```
Novas empresas recebem os 88 defensivos automaticamente via signal, sem ação manual.

### Status final
Documentado como "100% implementado e pronto para produção" em 2025-02-04, junto com o sistema equivalente de seed de pragas (também 88 registros, mesmo padrão de signal + management command). Juntas, as duas rotinas de seed criam ~176 registros por empresa em menos de 2 segundos.

## B. Propostas de recomendação automática de defensivo por praga / receituário agronômico

Os dois documentos de análise (`ANALISE_RECEITUARIO_AGRONOMICO.md` e `ANALISE_RECOMENDACOES_DEFENSIVOS.md`) descrevem, **como proposta não fechada**, um fluxo em que o agrônomo identifica uma praga em um talhão, o sistema sugere defensivos recomendados (com dosagem, carência e efetividade pré-preenchidos), e opcionalmente gera um documento de "Receituário Agronômico" formal.

### Modelos propostos (nos documentos de análise)
- `RecomendacaoDefensivo` — relaciona `Praga` + `Produto`, com ordem de prioridade, efetividade (%), custo relativo, faixa de dosagem, carência mínima, intervalo de reaplicação.
- `Receituario` — documento com talhão, praga, recomendação escolhida, dados de aplicação (dosagem, volume de calda, condições climáticas), agrônomo responsável e status (Rascunho/Pendente/Aprovado/Rejeitado).
- Estimativas de esforço apresentadas variavam de ~3.5h (modal simples na tela de praga) a ~17h (solução completa com página dedicada, API REST e cálculo inteligente de dosagem).

### Situação real confirmada no código atual (verificado nesta consolidação, 2026-07-10)
- O modelo **`RecomendacaoDefensivo` existe e é referenciado em produção** — mas não em `produtos/models.py` como os documentos de análise propunham; ele é importado dinamicamente (`from produtos.models import RecomendacaoDefensivo`) dentro de `cadastros/forms.py` (~linha 3477) e `mip/forms.py` (~linha 157), como parte do módulo de Monitoramento Integrado de Pragas (MIP — ver cluster `docs/archive/mip/`, tratado por outra frente de trabalho). O uso está **envolto em `try/except` silencioso**, ou seja, o código tolera a ausência do modelo sem quebrar — sinal de que a integração pode ter sido implementada de forma incremental/parcial.
- **Não foi encontrada** uma classe `Receituario` em nenhum lugar do código-fonte atual (`grep` não retornou resultados). Ou seja, o conceito de "Receituário Agronômico" como documento formal, conforme desenhado em `ANALISE_RECEITUARIO_AGRONOMICO.md`, aparentemente **não foi implementado** como tal — o que existe hoje (monitoramento/NED em `mip/`) é uma evolução distinta do problema original.

### Aviso para quem consultar este histórico
Antes de assumir que qualquer parte da proposta em "B" está disponível no sistema atual, confirme diretamente em `produtos/models.py`, `mip/models.py` e `cadastros/models.py`, e consulte a documentação viva do módulo MIP (fora do escopo deste cluster de arquivamento).

## Quando foi feito
Documentos datados de **2025-02-04** (seed de defensivos) e sem data explícita nos dois arquivos de análise (mas do mesmo período, por conteúdo e referências cruzadas). Elaborados sobre uma versão anterior do projeto (referências a `c:\erp_agricola` como diretório de trabalho, hoje `f:\projetos\agrisdatav2`).
