Owner: Documentacao (Legado)
Status: Deprecated
Last Updated: 2026-07-10
Scope: Integração de frontend com Supabase Auth (login/registro/OAuth) e Supabase Storage para upload de imagens (módulo Safra)

# Supabase: autenticação de frontend e storage de imagens de Safra

Registro histórico consolidado, mesclado a partir de 5 arquivos originais:
- `CHANGELOG_SUPABASE_FRONTEND.md`
- `SUPABASE_FRONTEND_CHECKLIST.md`
- `SUPABASE_IMPLEMENTATION_SUMMARY.md`
- `DOCUMENTACAO_SUPABASE_STORAGE_SAFRA.md`
- `IMPLEMENTACAO_SAFRA_SUPABASE_STORAGE.md`

Os 3 primeiros arquivos documentam a mesma entrega (frontend de autenticação Supabase), escrita em momentos diferentes da mesma sessão. Os 2 últimos documentam uma entrega posterior e não relacionada (upload de imagens de Safra para o Supabase Storage). Ambos os temas compartilham apenas a dependência do Supabase como serviço, por isso foram agrupados neste único cluster de arquivamento.

## A. Frontend de autenticação Supabase (5 de abril de 2025)

### O que foi implementado
Páginas de login/registro com Supabase Auth (email+senha e Google OAuth), substituindo/complementando o fluxo de autenticação Django padrão, com sincronização de usuários entre Supabase e o model `Usuario` do Django.

**Arquivos criados:**
- `usuarios/templates/usuarios/supabase_login.html` (405 linhas) e `supabase_register.html` (418 linhas) — layout split, campos de email/senha (+ nome/sobrenome no registro), medidor de força de senha em tempo real, botão de OAuth Google, paleta de cores "Nexsafra", responsivo.
- `usuarios/templates/usuarios/base_auth.html` — template base que carrega o Supabase JS SDK (CDN) e `supabase-init.js`.
- `usuarios/static/js/supabase-init.js` (189 linhas) — client singleton e funções `loginWithGoogle()`, `registerWithEmail()`, `loginWithEmail()`, `getCurrentSession()`, `getCurrentUser()`, `logoutUser()`, `requestPasswordReset()`, `onAuthStateChange()`, exportadas em `window.SupabaseAuth`.
- `usuarios/context_processors.py` — injeta `supabase_url`, `supabase_anon_key`, `auth_mode`, `google_oauth_enabled` em todos os templates.
- `usuarios/models_supabase.py` — `SupabaseUsuarioSync` (ponte Django↔Supabase) e `LoginSupabase` (log de auditoria).
- `core/supabase_config.py` — `SupabaseClient`/`SupabaseAuth` (cliente singleton).
- `core/supabase_rls.sql` — políticas de Row Level Security para isolamento multi-tenant (usuários só veem a própria empresa via `auth.uid()` / `empresa_id` nos JWT claims), aplicadas em `usuarios_usuario`, `cadastros_fazenda`, `estoque_armazem`, `compras_solicitacaocompra`, `financeiro_contapagar` (lista da época — não necessariamente exaustiva hoje).

**Arquivos modificados:**
- `core/settings.py` — registrado `usuarios.context_processors.supabase_context` em `TEMPLATES`.
- `usuarios/supabase_auth/views.py` — views GET `login_page()` e `register_page()` adicionadas (227 linhas totais).
- `usuarios/supabase_auth/urls.py` — rotas `/auth/login-page/`, `/auth/register-page/` (além das já existentes `/auth/login/`, `/auth/register/`, `/auth/logout/`, `/auth/callback/google/`).

### Fluxos (login, registro, Google OAuth)
- **Registro**: usuário preenche formulário → `registerWithEmail()` (JS) → `POST /auth/register/` → cria usuário no Supabase Auth + `Usuario` Django + `SupabaseUsuarioSync` → redireciona para login.
- **Login**: `loginWithEmail()` (JS) → `POST /auth/login/` → autentica no Supabase, localiza/cria `SupabaseUsuarioSync`, cria sessão Django, grava `LoginSupabase` (auditoria) → redireciona para `/dashboard/`.
- **Google OAuth**: `loginWithGoogle()` → redirect Google → `GET /auth/callback/google/` → processa token, sincroniza usuário, cria sessão Django → redireciona para `/dashboard/`.

### Segurança e configuração
CSRF em todos os forms; `ANON_KEY` é segura para o frontend (protegida por RLS); `SERVICE_ROLE_KEY` nunca deve ir ao frontend; RLS habilitado nas tabelas multi-tenant. Variáveis `.env` necessárias: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `AUTH_MODE`, opcionalmente `GOOGLE_OAUTH_CLIENT_ID`/`SECRET`.

### Status final
Documentado como "100% completo e pronto para produção" em 5 de abril de 2025, sobre Django 4.2.29 / Python 3.14.3 (versões da época — o projeto está hoje em Django 6.0.6, ver `README.md` raiz). Pendências explicitamente deixadas para o usuário: colar `.env`, rodar migrations, colar SQL de RLS no dashboard do Supabase, configurar Google OAuth (opcional) e testar localmente antes do deploy.

## B. Supabase Storage para imagens de Safra (8 de abril de 2026)

### O que foi implementado
Upload automático de imagens do cadastro de `Safra` (`cadastros` app) para o Supabase Storage, com fallback implícito para `MEDIA_ROOT` local quando o Supabase não está configurado (padrão já descrito em `CLAUDE.md` para uploads do projeto).

**Arquivos criados:**
- `core/supabase_storage.py` (108 linhas) — backend de storage customizado (`SupabaseStorage`) compatível com a API de storage do Django, parametrizável por `bucket_name`.
- `cadastros/management/commands/init_supabase_buckets.py` e `setup_supabase_buckets.py` — inicializam os buckets configurados em `SUPABASE_STORAGE_BUCKETS` (à época: `empresas-logos`, `documentos`, `produtos-imagens`, `funcionarios-fotos`, `compras-xml`, `safra-imagens`, `uploads-gerais`).

**Arquivos modificados:**
- `cadastros/models.py` — campo `imagem` (ImageField, opcional) adicionado ao model `Safra`.
- `cadastros/forms.py` — campo de upload em `SafraForm` (widget `FileInput`, `accept="image/*"`).
- `cadastros/signals.py` — `safra_post_save_upload_imagem()` faz o upload para o Supabase Storage após salvar a `Safra`, seguindo a estrutura de diretórios `safra-imagens/{fazenda_id}/{safra_id}/...`; há também tratamento de `safra_post_delete` para remover a imagem do storage ao excluir a safra.
- `cadastros/templates/cadastros/safra/safra_form.html` e `safra_detail.html` — campo de upload e exibição da imagem.
- `core/settings.py` — bucket `safra-imagens` adicionado a `SUPABASE_STORAGE_BUCKETS`.
- Migration `cadastros/migrations/0076_safra_imagem.py` — aplicada.

### Segurança
Bucket público para leitura; upload restrito a usuários autenticados (via Django); validação de MIME type (`image/*`); upsert automático não sobrescreve sem confirmação.

### Status final
Documentado como "completo e testado", migração aplicada, formulário/templates funcionando e comando de validação de buckets funcionando sem erros de log à época.

## Gotchas / avisos ainda relevantes (ambos os temas)
- Confirmar no código atual (`core/supabase_config.py`, `usuarios/supabase_auth/`, `core/supabase_storage.py`) se esses componentes ainda existem com os mesmos nomes — os documentos originais são de abril/2025 e abril/2026 e o projeto pode ter evoluído (ex.: versão do Django mudou de 4.2.29 para 6.0.6 entre os dois sub-registros).
- Erros comuns documentados à época: `ModuleNotFoundError: No module named 'supabase'` (rodar `pip install supabase`), `Bucket does not exist` (rodar `init_supabase_buckets`), SDK do Supabase não carregado no frontend (checar ordem de scripts: SDK antes de `supabase-init.js`), OAuth redirecionando incorretamente (checar Redirect URL no Google Cloud Console vs Supabase), RLS bloqueando queries com 403 (checar JWT claims/policies).
- Os documentos fazem referência cruzada a `SUPABASE_AUTH_SETUP.md`, `SUPABASE_JS_INTEGRATION.md`, `TROUBLESHOOTING_SUPABASE_STORAGE.md`, `SUMMARY_API_KEYS_FIX.md` e `SECURITY_AUDIT_API_KEYS.md` — arquivos que podem estar em outros clusters de arquivamento (ex.: `api-keys-seguranca`, tratado em outra frente de trabalho) ou ainda na raiz do repositório; não foram incluídos neste cluster por não constarem na lista de arquivos-fonte definida para esta consolidação.
