Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: correcao de exposicao de chaves Supabase no frontend e ativacao de RLS

Este é um registro histórico consolidado, mesclado a partir de 4 arquivos originais: `SECURITY_AUDIT_API_KEYS.md`, `SUMMARY_API_KEYS_FIX.md`, `MIGRATION_SECURE_API_KEYS.md` e `RLS_STATUS_FINAL.md` (preservados em `fontes/`). Os três primeiros documentam a mesma correção de segurança sob ângulos diferentes (auditoria técnica, resumo executivo, guia de migração); o quarto documenta um trabalho relacionado mas distinto — ativação de Row Level Security no Postgres/Supabase.

## Parte 1 — Correção de exposição de chaves Supabase no frontend

### Problema encontrado

`SECURITY_AUDIT_API_KEYS.md` e `SUMMARY_API_KEYS_FIX.md` documentam uma auditoria que encontrou `SUPABASE_URL` e `SUPABASE_ANON_KEY` sendo injetadas diretamente em templates HTML via context processor, e consumidas por JavaScript com variáveis globais — expondo as chaves a qualquer usuário que inspecionasse o HTML/console do navegador. Severidade classificada como **Alta**: o risco descrito era o de um atacante extrair as chaves e usar o SDK do Supabase diretamente, potencialmente contornando a lógica de aplicação (e RLS, se mal configurado).

Arquivos identificados como vulneráveis:
- `usuarios/context_processors.py` — injetava `supabase_url` e `supabase_anon_key` no contexto de templates.
- `usuarios/static/js/supabase-init.js` — consumia essas variáveis globais no frontend.
- `usuarios/supabase_auth/views.py` — repassava credenciais para templates.

### Solução implementada

Substituição do modelo "chaves injetadas no HTML" por um proxy de backend com 4 endpoints novos:

| Endpoint | Método | Proteção | Propósito |
|---|---|---|---|
| `/auth/api/auth-config/` | GET | público | Retorna `{oauth_enabled, oauth_providers, auth_mode}` — nunca chaves |
| `/auth/api/current-user/` | GET | `@login_required` | Dados do usuário logado |
| `/auth/api/validate-token/` | POST | — | Valida JWT do Supabase no backend |
| `/auth/api/callback-proxy/` | POST | — | Proxy do callback OAuth |

Arquivos criados: `usuarios/supabase_auth/api.py` (os 4 endpoints) e `usuarios/static/js/supabase-init-v2.js` (JS que só fala com esses endpoints, nunca guarda chaves em variáveis globais).

Arquivos modificados: `usuarios/context_processors.py` (parou de expor `supabase_url`/`supabase_anon_key`, passou a expor apenas `auth_mode`, `google_oauth_enabled` e as URLs dos endpoints seguros), `usuarios/supabase_auth/urls.py` (registrou as 4 rotas novas).

Login/registro por email-senha passaram a usar proxy de backend (`/auth/login/`, `/auth/register/`) em vez do SDK do Supabase diretamente no frontend; `SERVICE_ROLE_KEY` nunca sai do servidor. O Google OAuth continua usando `ANON_KEY` no frontend — isso é tratado como aceitável nas fontes ("pública por design"), carregada dinamicamente em vez de fixa no HTML.

`MIGRATION_SECURE_API_KEYS.md` é o guia operacional passo a passo para aplicar essa migração num ambiente (atualizar `base_auth.html`, trocar `supabase-init.js` por `supabase-init-v2.js`, testar com curl, checklist de deploy) — consultar o arquivo original em `fontes/` se for necessário reaplicar/verificar esses passos manualmente.

### Quando foi feito

**7 de abril de 2026**, conforme `SECURITY_AUDIT_API_KEYS.md` e `SUMMARY_API_KEYS_FIX.md`.

### Status final

Marcado como **corrigido e documentado**, "risco residual baixo após aplicar mudanças", com checklist de implementação todo marcado `[x]` exceto deploy/QA em staging e produção, que aparecem como `[ ]` pendentes nas próprias fontes (ou seja, a correção de código foi feita e validada localmente, mas o rollout para staging/produção não está confirmado nos documentos).

## Parte 2 — Ativação de RLS (Row Level Security) no Supabase

`RLS_STATUS_FINAL.md`, também datado de **7 de abril de 2026**, documenta um trabalho relacionado de segurança de dados, mas é uma frente separada: ativação de políticas RLS no Postgres/Supabase para reforçar isolamento multi-tenant no nível do banco (defesa em profundidade, complementando o isolamento por `empresa` já feito na camada Django).

- RLS ativado em **55 de 155 tabelas** (cobertura de 3.2% → 35.5%), com 38+ policies (antes 5).
- Estratégia principal: policy `isolar_tabela_por_empresa` usando `empresa_id = (auth.jwt() ->> 'empresa_id')::int OR auth.jwt() ->> 'tipo' = 'SUPERADMIN'`, aplicada às 55 tabelas com coluna `empresa_id` direta.
- Tabelas sem `empresa_id` direto (46 delas — ex.: `cadastros_armadorcontato`, `compras_itempedidocompra`, `produtos_produto`) dependem de isolamento em cascata via FK (RLS na tabela pai) mais validação de aplicação em Django — **não têm RLS próprio**.
- Tabelas de configuração global sem tenant (CFOP, NCM, Moeda, Cultura etc.) e tabelas internas do Django (`auth_*`) foram deliberadamente deixadas sem RLS.
- Performance: overhead estimado de policies em ~1-2% nas queries; índices em `empresa_id` recomendados.

### Status final (RLS)

"Concluído em 7 de Abril de 2026" — mas cobrindo apenas 35.5% das tabelas do banco. Não é "RLS completo": é uma primeira camada aplicada às tabelas mais sensíveis com `empresa_id` direto.

## Pendências / avisos ainda relevantes

Da correção de chaves de API (não confirmadas como concluídas nos documentos-fonte):
- Deploy em staging, QA testing e deploy em produção aparecem como itens `[ ]` não marcados.
- Rate limiting em `/auth/api/*`.
- Logging de autenticação (quem logou quando).
- Implementação de 2FA (two-factor authentication).
- IP whitelisting para operações admin.
- Migração das chaves para um secrets manager dedicado (Supabase Secrets / AWS / GCP) em vez de `.env`.
- Handling de expiração de token e testes de injeção SQL/CSRF.

Da ativação de RLS (explicitamente listadas como "próximos passos opcionais" em `RLS_STATUS_FINAL.md`, não implementadas):
- RLS direto nas 46 tabelas filhas sem `empresa_id` (hoje dependem só de FK + validação de aplicação — risco residual se algum código de app tiver bug de filtro).
- RLS por usuário (`usuario_id`) para tabelas que precisam de isolamento pessoal além de por empresa.
- Monitoramento/log de violações de RLS (tabela `rls_violation_logs` sugerida, não criada).

**Antes de assumir que o sistema está 100% protegido contra vazamento cross-tenant**, ter em mente que apenas ~35% das tabelas têm RLS no banco — o restante depende inteiramente da correção de filtros na camada Django (`empresa=request.user.empresa` em cada view), que é o padrão de todo o resto do projeto conforme `CLAUDE.md`.

Detalhes de comandos curl de verificação, exemplos completos de código antes/depois e a lista completa das 100 tabelas sem RLS (com justificativa individual) permanecem nos originais em `fontes/`.
