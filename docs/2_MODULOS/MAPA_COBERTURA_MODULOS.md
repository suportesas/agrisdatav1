Owner: Documentacao
Status: In Review
Last Updated: 2026-07-10
Scope: Cobertura funcional por modulo

## Objetivo
Controlar a cobertura de documentação de todos os 27 apps Django reais do projeto (lista extraída de `*/apps.py`).

## Matriz de cobertura
| Modulo | Documento | Status | Notas |
|---|---|---|---|
| compras | [MODULO_COMPRAS.md](MODULO_COMPRAS.md) | Approved | Verificado contra models/views/urls |
| estoque | [MODULO_ESTOQUE.md](MODULO_ESTOQUE.md) | In Review | Entidades/rotas mapeadas; estratégia de cálculo detalhada em `docs/4_TECNICO/ESTRATEGIA_ESTOQUE.md` |
| financeiro | [MODULO_FINANCEIRO.md](MODULO_FINANCEIRO.md) | Approved | Baseado em `financeiro/CLAUDE.md` (guia do app) |
| cadastros | [MODULO_CADASTROS.md](MODULO_CADASTROS.md) | Approved | Inclui NCM |
| produtos | [MODULO_PRODUTOS.md](MODULO_PRODUTOS.md) | Approved | Inclui hierarquia Categoria/Subcategoria |
| rh | [MODULO_RH.md](MODULO_RH.md) | In Review | Já reflete o app `rh` dedicado (pós-migração `0112_remove_rh_models`) |
| embalagem | [MODULO_EMBALAGEM.md](MODULO_EMBALAGEM.md) | In Review | Planejamento pré-implementação arquivado em `docs/archive/embalagem-planejamento-v1/` |
| drawback | [MODULO_DRAWBACK.md](MODULO_DRAWBACK.md) | Draft — a expandir | Criado nesta rodada; ver PRD em `docs/1_ARQUITETURA/prd_drawback.md` |
| estufas | [MODULO_ESTUFAS.md](MODULO_ESTUFAS.md) | Draft — a expandir | Criado nesta rodada |
| etiquetas_avulsas | [MODULO_ETIQUETAS_AVULSAS.md](MODULO_ETIQUETAS_AVULSAS.md) | Draft — a expandir | Criado nesta rodada |
| patrimonio | [MODULO_PATRIMONIO.md](MODULO_PATRIMONIO.md) | Draft — a expandir | Criado nesta rodada |
| portal | [MODULO_PORTAL.md](MODULO_PORTAL.md) | Draft — a expandir | Criado nesta rodada; app cobre só `/portal/cliente/`, ver tabela de outros portais no documento |
| usuarios | [MODULO_USUARIOS.md](MODULO_USUARIOS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| empresas | [MODULO_EMPRESAS.md](MODULO_EMPRESAS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| faturamento | [MODULO_FATURAMENTO.md](MODULO_FATURAMENTO.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| vendas | [MODULO_VENDAS.md](MODULO_VENDAS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| exportacao | [MODULO_EXPORTACAO.md](MODULO_EXPORTACAO.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| operacoes_campo | [MODULO_OPERACOES_CAMPO.md](MODULO_OPERACOES_CAMPO.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| mip | [MODULO_MIP.md](MODULO_MIP.md) | Draft — a expandir | Esqueleto auto-gerado; histórico de implementação em `docs/archive/mip/` (inclui TODO pendente não resolvido) |
| frota | [MODULO_FROTA.md](MODULO_FROTA.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| energia | [MODULO_ENERGIA.md](MODULO_ENERGIA.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| emprestimos | [MODULO_EMPRESTIMOS.md](MODULO_EMPRESTIMOS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| adiantamentos | [MODULO_ADIANTAMENTOS.md](MODULO_ADIANTAMENTOS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| bancario | [MODULO_BANCARIO.md](MODULO_BANCARIO.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| plano_contas | [MODULO_PLANO_CONTAS.md](MODULO_PLANO_CONTAS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| dashboard | [MODULO_DASHBOARD.md](MODULO_DASHBOARD.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |
| metricas | [MODULO_METRICAS.md](MODULO_METRICAS.md) | Draft — a expandir | Esqueleto auto-gerado, não revisado nesta rodada |

## Regra de "Approved"
Um módulo só pode ser marcado `Approved` quando:
1. O documento foi verificado contra `models.py`/`urls.py`/`views.py` reais do app (não é só esqueleto auto-gerado).
2. Fluxos principais e entidades-chave estão descritos com precisão.
3. Integrações com outros módulos estão referenciadas.

Módulos `Draft — a expandir` têm ao menos nome, prefixo de URL e entidades principais reais (não são mais tabelas 100% placeholder), mas ainda não tiveram fluxos/regras de negócio detalhados.
