# Estrategia de Testes

Owner: Engenharia e QA
Status: Draft
Last Updated: 2026-07-01
Scope: Cobertura e qualidade

## Objetivo
Garantir confiabilidade das regras de negocio e evitar regressao.

## Piramide de testes
- Unitario: models, services, validacoes e calculos
- Integracao: fluxo entre apps (compras -> financeiro, estoque -> faturamento)
- E2E: jornada de usuario critica

## Prioridades de cobertura
1. Calculos fiscais e financeiros
2. Condicionais de status e aprovacao
3. Controle de saldo e bloqueios de estoque
4. Isolamento multiempresa

## Criterio minimo por regra critica
- 1 teste feliz
- 1 teste de borda
- 1 teste de regressao

## Meta inicial
- Cobertura funcional critica com rastreabilidade doc -> teste

## Referencias
- Testes E2E (Playwright): `e2e/README.md` — comandos: `pytest tests/e2e/`
- Testes unitarios (Django): `python manage.py test <app>`
- Casos especificos de estoque: `docs/5_DESENVOLVIMENTO/TESTES_ESTOQUE.md`, `docs/5_DESENVOLVIMENTO/TESTES_E2E_ESTOQUE.md`
