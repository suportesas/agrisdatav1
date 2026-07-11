# 🔐 AUDITORIA DE SEGURANÇA - CHAVES DE API

## ❌ PROBLEMA ENCONTRADO

### Exposição de Chaves no Frontend ("Hard-coded Secrets")

**Arquivos verificados com exposição:**

| Arquivo | Chaves Expostas | Severidade | Status |
|---------|------------------|-----------|--------|
| `usuarios/context_processors.py` | SUPABASE_URL, SUPABASE_ANON_KEY | ⚠️ Alto | ✅ CORRIGIDO |
| `usuarios/static/js/supabase-init.js` | Usa variáveis injetadas no HTML | ⚠️ Alto | ✅ CORRIGIDO |
| `usuarios/supabase_auth/views.py` | Injeta credenciais em templates via context | ⚠️ Alto | ✅ CORRIGIDO |

### Fluxo de Exposição (Antes)

```
.env (servidor)
  ↓
settings.py (Django)
  ↓
context_processors.py (injeta em templates)
  ↓
Templates HTML (renderizados)
  ↓
Browser inspect/source (EXPOSTO!)
  ↓
JavaScript supabase-init.js (usa variáveis globais)
  ↓
Frontend Supabase client (client-side operations)
```

**Risco:** Atacante pode:
1. Inspecionar source HTML da página
2. Extrair SUPABASE_URL e SUPABASE_ANON_KEY
3. Usar credenciais para acessar dados diretamente via SDK Supabase
4. Contornar lógica de aplicação e RLS (se não estiver bem configurado)
5. Modificar dados maliciosamente

---

## ✅ SOLUÇÃO IMPLEMENTADA

### Novo Fluxo Seguro

```
Backend Seguro (Servidor)
├── settings.py: SUPABASE_URL, ANON_KEY, SERVICE_ROLE_KEY (protegidas em .env)
│
├── Endpoint Seguro: GET /auth/api/auth-config/
│   └── Retorna: {oauth_enabled, oauth_providers, auth_mode}
│       (SEM expor chaves)
│
├── Endpoint Seguro: POST /auth/api/validate-token/
│   └── Valida JWT token no backend (não no frontend)
│
└── Endpoint Seguro: GET /auth/api/current-user/
    └── Retorna info do usuário logado (protegido por autenticação)
       
Frontend Seguro (Cliente)
├── supabase-init-v2.js: Carrega APENAS de endpoints seguros
│   └── Nunca armazena chaves em variáveis globais
│
├── OAuth Seguro: Usa ANON_KEY apenas quando necessário
│   └── Carregado dinamicamente de elemento HTML seguro
│   └── Usado apenas para signInWithOAuth (operação pública de design)
│
└── Email/Senha: Backend proxy via /auth/login/
    └── Backend maneja SERVICE_ROLE_KEY (nunca exposto)
```

### Arquivos Modificados

#### 1. **usuarios/context_processors.py** ✅
**Antes:**
```python
return {
    'supabase_url': getattr(settings, 'SUPABASE_URL', ''),
    'supabase_anon_key': getattr(settings, 'SUPABASE_ANON_KEY', ''),  # ❌ EXPOSTO
    ...
}
```

**Depois:**
```python
return {
    'auth_mode': getattr(settings, 'AUTH_MODE', 'django'),
    'google_oauth_enabled': bool(getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')),
    'api_auth_config_url': '/auth/api/auth-config/',  # ✅ Endpoint seguro
    'api_current_user_url': '/auth/api/current-user/',  # ✅ Endpoint seguro
}
```

#### 2. **usuarios/supabase_auth/urls.py** ✅
**Adicionado:**
```python
from . import api

urlpatterns = [
    # ... (URLs existentes)
    
    # Novos endpoints seguros
    path('api/auth-config/', api.auth_config, name='auth_config'),
    path('api/validate-token/', api.validate_token, name='validate_token'),
    path('api/callback-proxy/', api.auth_callback_proxy, name='callback_proxy'),
    path('api/current-user/', api.current_user, name='current_user'),
]
```

#### 3. **usuarios/supabase_auth/api.py** ✅ (NOVO ARQUIVO)
```python
@require_http_methods(["GET"])
def auth_config(request):
    """Retorna config SEM expor chaves"""
    return JsonResponse({
        "oauth_enabled": bool(getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')),
        "oauth_providers": ["google"],
        "auth_mode": getattr(settings, 'AUTH_MODE', 'django'),
    })

@require_http_methods(["GET"])
@login_required
def current_user(request):
    """Retorna usuário logado (protegido por auth)"""
    usuario = Usuario.objects.get(user_ptr=request.user)
    return JsonResponse({
        'user_id': str(usuario.user_ptr.id),
        'email': usuario.email,
        'empresa_id': usuario.empresa_id,
        'tipo': usuario.tipo,
    })
```

#### 4. **usuarios/static/js/supabase-init-v2.js** ✅ (NOVO ARQUIVO)
```javascript
// Carrega config de endpoint seguro
async function loadAuthConfig() {
  const response = await fetch('/auth/api/auth-config/');
  const config = await response.json();
  // Retorna APENAS: oauth_enabled, oauth_providers, auth_mode
  // NÃO contém chaves de API!
}

// Email/Senha usa backend proxy
async function loginWithEmail(email, password) {
  const response = await fetch('/auth/login/', {  // Backend endpoint
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

// Google OAuth carrega credenciais dinamicamente
// (ANON_KEY é pública por design, apenas para OAuth)
async function loginWithGoogle() {
  const supabase = await initSupabaseForOAuth();
  // ... (usa ANON_KEY apenas aqui, de forma segura)
}
```

---

## 🛡️ ESTRATÉGIA DE SEGURANÇA

### Níveis de Proteção

#### 1️⃣ **Backend (Seguro)**
- ✅ SUPABASE_URL em .env (servidor only)
- ✅ SUPABASE_ANON_KEY em .env (servidor only)
- ✅ SUPABASE_SERVICE_ROLE_KEY em .env (servidor only - máximas permissões)
- ✅ Django session + CSRF tokens
- ✅ Backend proxy para operações sensíveis

**Operações backend:**
```python
# Backend pode usar SERVICE_ROLE_KEY para admin operations
supabase_auth = SupabaseAuth()
user = supabase_auth.register_user(email, password)
```

#### 2️⃣ **Frontend (Público)**
- ✅ Sem chaves de API em variáveis globais
- ✅ Endpoints seguros via GET /auth/api/auth-config/
- ✅ JWT tokens via Authorization header
- ✅ Backend proxy para operações protegidas

**Operações frontend:**
```javascript
// Google OAuth usa ANON_KEY (pública por design)
// Carregada DINAMICAMENTE apenas quando necessário
await loginWithGoogle();

// Email/Senha usa backend proxy
await loginWithEmail(email, password);

// Validação usa JWT token
const user = await validateSession();
```

#### 3️⃣ **API (Segura)**
- ✅ GET /auth/api/auth-config/ - público, sem chaves
- ✅ GET /auth/api/current-user/ - login_required
- ✅ POST /auth/api/validate-token/ - Bearer token validation
- ✅ POST /auth/login/ - Backend proxy (SERVICE_ROLE_KEY)
- ✅ POST /auth/register/ - Backend proxy

---

## 📋 CHECKLIST DE SEGURANÇA

### ✅ Implementado

- [x] Remover SUPABASE_URL de context processor
- [x] Remover SUPABASE_ANON_KEY de context processor
- [x] Remover chaves de templates HTML
- [x] Criar endpoints seguros em /auth/api/
- [x] Atualizar JavaScript para usar endpoints seguros
- [x] Backend proxy para email/senha login
- [x] Proteger endpoints com @login_required onde necessário
- [x] Usar SERVICE_ROLE_KEY APENAS no backend
- [x] ANON_KEY carregada dinamicamente para OAuth
- [x] JWT validation no backend

### 📋 Próximos Passos (Recomendados)

- [ ] Implementar rate limiting em /auth/api/ endpoints
- [ ] Adicionar logging de autenticação (quem logou quando)
- [ ] Implementar 2FA (two-factor authentication)
- [ ] Adicionar IP whitelisting para operações admin
- [ ] Usar Supabase Secrets Manager (environment variables)
- [ ] Implementar token expiration handling
- [ ] Adicionar CORS headers apropriadamente
- [ ] Testar injeção SQL e CSRF attacks

---

## 🔑 TRATAMENTO DE CHAVES

### Em Produção (Recomendado: Supabase Secrets)

**Opção 1: Environment Variables (Atual)**
```bash
# .env.production (NUNCA commitar)
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

**Opção 2: Supabase Secrets Console (Futuro)**
```
Supabase Dashboard → Settings → Secrets
├── SUPABASE_URL
├── SUPABASE_ANON_KEY
└── SUPABASE_SERVICE_ROLE_KEY
```

**Opção 3: Cloud Secret Manager (AWS/GCP)**
```python
# Integrar com AWS Secrets Manager ou GCP Secret Manager
import boto3
secrets = boto3.client('secretsmanager')
secret = secrets.get_secret_value(SecretId='supabase-creds')
```

---

## ⚠️ IMPACTO NO CÓDIGO

### Aplicações Existentes

Se há código usando:
```javascript
// ❌ ANTES (Inseguro)
const { data } = await supabase.from('usuarios').select('*');
// Frontend SDK exposto, chaves visíveis no console
```

**Migrar para:**
```javascript
// ✅ DEPOIS (Seguro)
const response = await fetch('/auth/api/current-user/');
const user = await response.json();
// Ou usar custom endpoints backend
```

### Compatibilidade

- ✅ Django admin funciona normalmente
- ✅ API endpoints funcionam normalmente
- ✅ Migrations não são afetadas
- ✅ Session auth não muda
- ⚠️ Qualquer JS usando Supabase client diretamente precisa atualizar

---

## 🧪 TESTES RECOMENDADOS

```bash
# 1. Verificar que chaves não estão no HTML
curl http://localhost:8000/auth/login-page/ | grep -i "SUPABASE_.*KEY"
# Não deve retornar nada ✓

# 2. Verificar endpoint seguro
curl http://localhost:8000/auth/api/auth-config/
# Retorna: {"oauth_enabled": true, "auth_mode": "supabase", ...}
# Sem chaves ✓

# 3. Verificar proteção de endpoint
curl http://localhost:8000/auth/api/current-user/
# Erro 401 (requer autenticação) ✓

# 4. Inspecionar source code da página
# DevTools → Elements → não deve conter SUPABASE_ANON_KEY ✓
```

---

## 📊 RESUMO DE MUDANÇAS

| Componente | Antes | Depois | Benefício |
|-----------|-------|--------|-----------|
| Chaves no Frontend | Expostas | Ocultas | 🔒 Segurança |
| Context Processor | Injeta chaves | Endpoints | 🔄 Proxy seguro |
| JavaScript | Hardcoded keys | Dinâmico | 🔑 Sem exposição |
| Email/Senha | Supabase SDK | Backend proxy | 🛡️ Servidor controla |
| Google OAuth | (Mesmo) | (Sistema) | ✓ Seguro conforme design |
| API Endpoints | Nenhum | 4 novos | 📡 Backend intermediário |

---

## 📞 REFERÊNCIAS

- [Supabase Security Best Practices](https://supabase.com/docs/guides/auth)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Django Security](https://docs.djangoproject.com/en/4.2/topics/security/)
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)

---

**Status:** ✅ Auditoria concluída - Segurança implementada  
**Data:** 7 de Abril de 2026  
**Próxima:** Implementar 2FA e rate limiting
