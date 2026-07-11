# Runbook de Troubleshooting Supabase

Owner: Operacoes
Status: Draft
Last Updated: 2026-07-01
Scope: Banco/conexao

## Sinais de incidente
- Erro InvalidCursorName
- Erro intermitente de conexao em rotas de edicao
- Timeouts em operacoes com varias queries

## Diagnostico inicial
1. Confirmar se ambiente usa PG_* ativo no .env.
2. Verificar parametros de conexao no settings.
3. Testar conexao simples via shell.
4. Verificar se problema desaparece apos restart do servidor local.

## Acoes de mitigacao
1. Aplicar configuracoes de pool e timeout no banco.
2. Reiniciar servidor de desenvolvimento.
3. Fechar e reabrir conexao no shell quando necessario.
4. Em caso de bloqueio local, usar SQLite temporariamente para continuidade.

## Acoes definitivas
- Revisar consultas com risco de N+1
- Aplicar select_related/prefetch_related
- Ajustar logging de queries para diagnostico
- Monitorar estabilidade apos ajuste

## Checklist de retorno a normalidade
- Rota afetada responde sem erro
- Conexao valida em shell
- Fluxo de negocio alvo executa de ponta a ponta
- Sem novos erros relacionados em log

## Referencia legada
- TROUBLESHOOTING_SUPABASE.md
