# Runbook de Rollback - Fase 0

Objetivo: recuperar estabilidade em ate 15 minutos apos incidente.

## Pre-condicoes

1. Build anterior disponivel.
2. Banco com backup recente.
3. Feature flags acessiveis por ambiente.

## Passo a passo

1. Identificar incidente e congelar deploy.
2. Desligar feature flag relacionada ao incidente.
3. Reexecutar smoke test dos fluxos criticos.
4. Se nao normalizar, reverter release para versao anterior.
5. Validar aplicacao apos rollback.
6. Comunicar status para time de negocio.

## Smoke test minimo apos rollback

- Login e dashboard
- Fluxo compras basico
- Movimento de estoque
- Conta a pagar listagem

## Checklist de encerramento

- [ ] Sistema estavel
- [ ] Sem erro critico em logs
- [ ] Times notificados
- [ ] Analise de causa raiz agendada
