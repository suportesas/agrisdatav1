# 🔐 Configuração de Autenticação Supabase

Autenticação com **Email/Senha** e **Google OAuth** usando **Supabase + RLS**.

---

## 📋 Status da Implementação

✅ **Arquivos Criados:**
- `core/supabase_config.py` — Cliente Supabase
- `usuarios/models_supabase.py` — Modelos (SupabaseUsuarioSync, LoginSupabase)
- `usuarios/supabase_auth/views.py` — Views de registro/login
- `usuarios/supabase_auth/urls.py` — Rotas de autenticação
- `core/supabase_rls.sql` — RLS Policies (multi-tenancy)
- `usuarios/management/commands/make_supabase_migrations.py` — Auto-migrate

✅ **Dependências Instaladas:**
```bash
pip install supabase
```

✅ **Settings.py Atualizado** com variáveis:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `AUTH_MODE`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

---

## 🚀 Próximas Etapas

### PASSO 1: Copie as Variáveis para `.env`

Abra seu `.env` e adicione (ou atualize):

```env
# ==============================================================================
# SUPABASE CONFIGURATION
# ==============================================================================
SUPABASE_URL=https://aycjmeeteinbjvqnrycj.supabase.co
SUPABASE_ANON_KEY=SUA_CHAVE_ANONIMA_AQUI
SUPABASE_SERVICE_ROLE_KEY=SUA_SERVICE_ROLE_KEY_AQUI
AUTH_MODE=django
GOOGLE_OAUTH_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=seu-client-secret
```

### PASSO 2: Obtenha as Chaves Supabase

1. Acesse: https://supabase.com/dashboard
2. Clique no projeto `aycjmeeteinbjvqnrycj`
3. Vá para **Settings** (engrenagem) → **API**
4. **Copie:**
   - `Project URL` → Coloque em `SUPABASE_URL`
   - `anon public` → Coloque em `SUPABASE_ANON_KEY`
   - `service_role secret` (clique em "Show") → Coloque em `SUPABASE_SERVICE_ROLE_KEY`

### PASSO 3: Configure Google OAuth (Opcional, mas Recomendado)

1. Acesse: https://console.cloud.google.com/
2. Crie um novo projeto
3. Habilite: **Google+ API**
4. Vá para: **Credenciais** → **Criar Credencial** → **OAuth 2.0 Client ID**
5. Escolha: **Desktop Application**
6. Copie: **Client ID** e **Client Secret**
7. Paste no seu `.env`

Depois, configure no Supabase:
- Dashboard → **Authentication** → **Providers** → **Google**
- Cole as credenciais e salve

### PASSO 4: Execute as Migrações

```bash
python manage.py makemigrations usuarios
python manage.py migrate usuarios
```

Ou use o command automático:

```bash
python manage.py make_supabase_migrations
```

### PASSO 5: Ative RLS Policies

1. No Supabase dashboard, vá para **SQL Editor**
2. Abra o arquivo `core/supabase_rls.sql`
3. Copie TODO o conteúdo
4. Cole no SQL Editor do Supabase
5. Clique em **Run**

Esta etapa é **CRÍTICA** para isolamento por empresa (multi-tenancy)!

---

## 🧪 Testando

### Teste 1: Registrar novo usuário

```bash
curl -X POST http://localhost:8000/auth/register/ \
  -d "email=teste@example.com&password=senha123&first_name=João&last_name=Silva"
```

Esperado: `{"success": true, "redirect": "/login/"}`

### Teste 2: Login

```bash
curl -X POST http://localhost:8000/auth/login/ \
  -d "email=teste@example.com&password=senha123"
```

Esperado: `{"success": true, "redirect": "/dashboard/"}`

### Teste 3: Via Browser

- Registrar: http://localhost:8000/auth/register/
- Login: http://localhost:8000/auth/login/

---

## 📊 Arquitetura

```
┌─────────────────────────────────┐
│   Usuário (Frontend)            │
└──────────────┬──────────────────┘
               │
        ┌──────▼────────┐
        │  Django Login │
        │     Form      │
        └──────┬────────┘
               │
        ┌──────▼──────────────────────┐
        │ usuarios/supabase_auth/     │
        │ views.py                    │
        │ - register()                │
        │ - login()                   │
        │ - logout_view()             │
        └──────┬──────────────────────┘
               │
        ┌──────▼──────────────────────────┐
        │ core/supabase_config.py         │
        │ SupabaseAuth                    │
        │ - login_with_email()            │
        │ - register_with_email()         │
        │ - get_google_oauth_url()        │
        └──────┬──────────────────────────┘
               │
        ┌──────▼──────────────────────┐
        │  Supabase Auth Service      │
        │  - Email/Senha              │
        │  - Google OAuth             │
        │  - JWT Tokens               │
        └──────┬──────────────────────┘
               │
        ┌──────▼──────────────────────┐
        │  Supabase PostgreSQL        │
        │  + Row Level Security (RLS) │
        │  + Multi-tenancy            │
        └─────────────────────────────┘
```

---

## 🔒 Segurança (RLS Policies)

Cada usuário só vê dados da sua empresa:

```sql
-- Usuário só vê sua empresa
SELECT * FROM usuarios_usuario WHERE empresa_id = auth.jwt() ->> 'empresa_id'

-- Admin pode gerenciar usuários da empresa
UPDATE usuarios_usuario WHERE empresa_id = auth.jwt() ->> 'empresa_id'

-- Superadmin vê tudo
WHERE auth.jwt() ->> 'tipo' = 'SUPERADMIN'
```

---

## 🔄 Fluxo de Autenticação

### Login com Email/Senha:

```
1. Usuário submete email + senha
2. Supabase valida credenciais
3. Se OK → retorna JWT token + user ID
4. Procura SupabaseUsuarioSync no Django
5. Se não encontrar → cria usuário automaticamente
6. Django login (session)
7. Registra LoginSupabase (auditoria)
8. Redireciona para /dashboard/
```

### Login com Google (Frontend):

```
1. Usuário clica "Login com Google"
2. Redirecionado para Google OAuth consent
3. Google valida e retorna code
4. Frontend troca code por sessão (Supabase JS SDK)
5. Backend sincroniza com Django
6. Redireciona para /dashboard/
```

---

## 📚 Endpoints Disponíveis

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/auth/register/` | POST | Registrar novo usuário |
| `/auth/login/` | POST | Fazer login |
| `/auth/logout/` | GET | Fazer logout |
| `/auth/callback/google/` | GET | Callback Google OAuth |

---

## 🛠️ Modelos Django

### SupabaseUsuarioSync

Rastreia sincronização entre Django e Supabase:

```python
usuario = Usuario.objects.get(email='user@example.com')
sync = usuario.supabase_sync
print(f"UID Supabase: {sync.supabase_uid}")
print(f"Sincronizado: {sync.sincronizado}")
print(f"Última atualização: {sync.ultima_sincronizacao}")
```

### LoginSupabase

Auditoria de todos os logins:

```python
from usuarios.models_supabase import LoginSupabase

# Todos os logins bem-sucedidos
logins = LoginSupabase.objects.filter(sucesso=True)

# Logins com Google
google_logins = LoginSupabase.objects.filter(origem='google')

# Últimos 10 logins do usuário
usuario_logins = LoginSupabase.objects.filter(usuario=user).order_by('-timestamp')[:10]
```

---

## ⚙️ Variáveis de Ambiente

```env
# Obrigatório em produção
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=xxxx
SUPABASE_SERVICE_ROLE_KEY=xxxx (manter secreto!)

# Modo de autenticação
AUTH_MODE=django|dual|supabase

# Google OAuth (opcional)
GOOGLE_OAUTH_CLIENT_ID=xxxx
GOOGLE_OAUTH_CLIENT_SECRET=xxxx
```

---

## 🐛 Troubleshooting

**Erro: "SUPABASE_URL e SUPABASE_ANON_KEY não configurados"**

Solução: Copie as variáveis para `.env` (veja PASSO 2 acima)

**Erro: "Email já registrado"**

Solução: Supabase rejeita emails duplicados. Limpe o BD Supabase ou use outro email.

**RLS bloqueando queries**

Solução: Execute o SQL em `core/supabase_rls.sql` no Supabase SQL Editor

**Google OAuth não funciona**

Solução: Verifique se Client ID/Secret estão corretos e se o Supabase foi configurado

---

## 📞 Suporte

- **Docs Supabase:** https://supabase.com/docs
- **Supabase CLI:** https://supabase.com/docs/guides/cli
- **RLS:** https://supabase.com/docs/guides/auth/row-level-security

---

## ✅ Checklist Final

- [ ] Copiei `.env` com chaves Supabase
- [ ] Executei migrações (`makemigrations` + `migrate`)
- [ ] Executing RLS SQL no Supabase dashboard
- [ ] Configurei Google OAuth no Supabase (opcional)
- [ ] Testei registrar novo usuário
- [ ] Testei fazer login
- [ ] Verifiquei que dados estão isolados por empresa
- [ ] Consultei LoginSupabase para auditoria

---

**Status:** ✅ Pronto Para Produção (após testes)

**Criado em:** 2026-04-05  
**Versão:** 1.0 - Email/Senha + Google + RLS
