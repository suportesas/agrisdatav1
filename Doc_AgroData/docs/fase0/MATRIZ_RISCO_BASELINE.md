# Matriz de Risco e Baseline - Fase 0

## Legenda

- Impacto: Alto, Medio, Baixo
- Probabilidade: Alta, Media, Baixa
- Prioridade: Critica, Alta, Media, Baixa

## Fluxos criticos (baseline)

| ID | Modulo | Fluxo | Impacto | Probabilidade | Prioridade | Dono | Evidencia de Baseline |
|---|---|---|---|---|---|---|---|
| F0-001 | Compras | Solicitacao -> Cotacao -> Pedido -> Recebimento | Alto | Media | Critica | Tech Lead | manage.py check OK; Feature flags: COMPRAS_XML_IMPORT implemented |
| F0-002 | Estoque | Entrada/Saida com lote | Alto | Media | Critica | Tech Lead | Modulo ativo; Validacoes de lote via models.py |
| F0-003 | Estoque | Entrada/Saida sem lote | Alto | Media | Critica | Tech Lead | Modulo ativo; Movimentacoes sem lote validadas |
| F0-004 | Financeiro | Conta a pagar -> parcelas -> pagamento | Alto | Media | Critica | Tech Lead | Modulo ativo; Feature flags: FINANCEIRO_RENEGOCIACAO desligada |
| F0-005 | RH | Férias, afastamento e rescisao CRUD | Medio | Media | Alta | Tech Lead | Modulo completo; CRUD validado em producao |
| F0-006 | Cadastros | Multi-tenant por empresa | Alto | Baixa | Alta | Tech Lead | Smoke test: test_safra_list_view_authenticated PASSED (11.503s); filtros por empresa funcionando |
| F0-007 | Acesso | Login, logout, permissao por perfil | Alto | Baixa | Alta | Tech Lead | Django auth integrado; Modulo cadastros.tests pass com filtro empresa |


## Acoes preventivas

1. Nenhuma feature nova pode alterar diretamente um fluxo da baseline sem teste de regressao equivalente.
2. Todo fluxo novo entra atras de feature flag desligada por padrao.
3. Toda release deve ter rollback validado antes da publicacao.
