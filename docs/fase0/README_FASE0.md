# Fase 0 - Preparacao e Seguranca

Objetivo da fase: criar uma trilha de desenvolvimento segura para evoluir modulos sem danificar fluxos estaveis.

## Escopo

1. Congelar baseline funcional.
2. Definir regressao bloqueante por modulo critico.
3. Padronizar uso de feature flags.
4. Definir gate de qualidade para liberar fase seguinte.
5. Definir runbook de rollback com tempo alvo de 15 minutos.

## Status

- [x] Infraestrutura de feature flags em settings.
- [x] Helper central para consulta de flags.
- [x] Modelos de matriz de risco, regressao, gate e rollback.
- [x] Baseline minima executada e evidenciada.
- [ ] Gate assinado para inicio da Fase 1.

## Artefatos desta fase

- `docs/fase0/MATRIZ_RISCO_BASELINE.md`
- `docs/fase0/CHECKLIST_REGRESSAO_BLOQUEANTE.md`
- `docs/fase0/GATE_QUALIDADE_FASE.md`
- `docs/fase0/ROLLBACK_RUNBOOK.md`
- `docs/fase0/PLANO_HOMOLOGACAO_FASE0.md`

## Regra de passagem para Fase 1

A Fase 1 so inicia quando todos os itens bloqueantes do gate estiverem aprovados.
