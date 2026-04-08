# 🔄 GUIA DE MIGRAÇÃO - API KEYS SEGURAS

## ⏱️ Tempo Estimado: 30 minutos

## 1️⃣ ATUALIZAR TEMPLATES

### Remover injeção insegura de chaves

**Arquivo: `usuarios/templates/usuarios/base_auth.html`**

❌ **Antes:**
```html
<head>
    <!-- ❌ INSEGURO: Expõe chaves no HTML -->
    <script type="text/javascript">
        window.supabaseUrl = '{{ supabase_url }}';
        window.supabaseAnonKey = '{{ supabase_anon_key }}';
    </script>
</head>
```

✅ **Depois:**
```html
<head>
    <!-- ✅ SEGURO: Sem exposição de chaves -->
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js"></script>
    <script src="{% static 'js/supabase-init-v2.js' %}"></script>
    
    <!-- Para OAuth: elemento seguro que será preenchido dinamicamente -->
    <script id="supabase-config-oauth" 
            data-url="" 
            data-key=""></script>
</head>
```

---

## 2️⃣ ATUALIZAR JAVASCRIPT

### Usar nova versão segura

**Antes: Incluir `supabase-init.js` (antigo - com chaves expostas)**

```html
<!-- ❌ Versão antigo -->
<script src="{% static 'js/supabase-init.js' %}"></script>
```

**Depois: Incluir `supabase-init-v2.js` (novo - seguro)**

```html
<!-- ✅ Versão nova e segura -->
<script src="{% static 'js/supabase-init-v2.js' %}"></script>
```

### Exemplo de uso em formulários

```html
<!-- Login Form -->
<form id="login-form">
    <input type="email" id="email" required>
    <input type="password" id="password" required>
    
    <!-- ✅ Usar nova function segura -->
    <button onclick="SupabaseAuth.loginWithEmail(
        document.getElementById('email').value,
        document.getElementById('password').value
    )">Login</button>
    
    <!-- Google OAuth -->
    <button onclick="SupabaseAuth.loginWithGoogle()">
        Entrar com Google
    </button>
</form>
```

---

## 3️⃣ ROTAS - JÁ IMPLEMENTADAS ✅

Não é necessário mudar nada! As rotas já estão configuradas:

```
GET  /auth/api/auth-config/         → Configuração segura
GET  /auth/api/current-user/        → Usuário logado (requer auth)
POST /auth/api/validate-token/      → Validar JWT
POST /auth/api/callback-proxy/      → OAuth callback proxy
```

---

## 4️⃣ VERIFICAR EXPOSIÇÃO DE CHAVES

### Script de Auditoria (Segurança)

```bash
# 1. Verificar que chaves NÃO estão no HTML
python manage.py runserver
curl http://localhost:8000/auth/login-page/ | grep -E "SUPABASE_(ANON|SERVICE)_KEY"
# ✅ Não deve retornar nada

# 2. Verificar estrutura correta
curl http://localhost:8000/auth/api/auth-config/
# ✅ Deve retornar: {"oauth_enabled": true, "auth_mode": "supabase"}

# 3. Verificar proteção de dados do usuário
curl http://localhost:8000/auth/api/current-user/
# ✅ Deve retornar 401 (não autenticado) ou usuário (autenticado)
```

---

## 5️⃣ TESTAR AUTENTICAÇÃO

### Email/Senha (Backend Proxy)

```bash
# Registrar
curl -X POST http://localhost:8000/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@example.com",
    "password": "senha123",
    "first_name": "João",
    "last_name": "Silva"
  }'

# Login
curl -X POST http://localhost:8000/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@example.com", "password": "senha123"}'
```

### Google OAuth (Frontend)

```javascript
// No browser console
SupabaseAuth.loginWithGoogle()
// Deve redirecionar para Google OAuth
```

---

## 6️⃣ VERIFICAR COMPATIBILIDADE

### ✅ Deve funcionar

- [x] Django admin login (`/admin/`)
- [x] Session authentication
- [x] CSRF protection
- [x] API endpoints
- [x] Migrations
- [x] Database queries

### ⚠️ Pode precisar ajuste

Se há código JavaScript customizado usando Supabase SDK diretamente:

```javascript
// ❌ Não funciona mais se chaves não estão disponíveis
const { data } = await supabase.from('usuarios').select('*');

// ✅ Solução: usar endpoint backend
const response = await fetch('/seu-endpoint-aqui/');
const data = await response.json();
```

---

## 🔧 TROUBLESHOOTING

### Problem: "Supabase SDK not loaded"

```javascript
// ✓ Solução: Garantir que SDK está carregado
// Em base_auth.html:
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js"></script>
<script src="{% static 'js/supabase-init-v2.js' %}"></script>
```

### Problem: "OAuth not configured"

```javascript
// ✓ Solução: Verificar que Google OAuth está habilitado
SupabaseAuth.loadAuthConfig().then(config => {
    console.log('OAuth enabled:', config.oauth_enabled);
});
```

### Problem: "401 Unauthorized on /auth/api/current-user/"

```javascript
// ✓ Solução: Fazer login primeiro ou usar endpoint público
// /auth/api/auth-config/ é público (não requer auth)
SupabaseAuth.loadAuthConfig();
```

---

## 📋 CHECKLIST DE MIGRAÇÃO

- [ ] Atualizar `base_auth.html` (remover injeção de chaves)
- [ ] Atualizar imports JavaScript (usar `supabase-init-v2.js`)
- [ ] Testar login com email/senha
- [ ] Testar Google OAuth
- [ ] Testar logout
- [ ] Rodar curl tests (auditoria)
- [ ] Verificar console do browser (nenhuma chave visível)
- [ ] Fazer commit das mudanças
- [ ] Deploy em staging
- [ ] QA testing
- [ ] Deploy em produção

---

## 🎯 OBJETIVOS ALCANÇADOS

✅ **Antes:**
- Chaves expostas no HTML
- Frontend acessa Supabase diretamente com ANON_KEY
- Risco de vazamento de credenciais

✅ **Depois:**
- Chaves protegidas no servidor (.env)
- Frontend usa endpoints seguro do backend
- Backend controla SERVICE_ROLE_KEY
- Sem exposição de credentials

---

## 📊 RESUMO TÉCNICO

| Operação | Antes | Depois |
|----------|-------|--------|
| Login | Supabase SDK | Backend proxy /auth/login/ |
| Registro | Supabase SDK | Backend proxy /auth/register/ |
| Google OAuth | Direct SDK | initSupabaseForOAuth() |
| Validação | JWT no frontend | /auth/api/validate-token/ |
| Usuário | Frontend SDK | /auth/api/current-user/ |
| Config | Context injection | /auth/api/auth-config/ |

---

## 🚀 PRÓXIMOS PASSOS

1. **Aplicar mudanças** (este guia)
2. **Testar localmente**
3. **Deploy em staging**
4. **QA testing**
5. **Deploy em produção**
6. **Monitorar logs**
7. **Implementar 2FA** (opcional, futuro)
8. **Implementar rate limiting** (opcional, futuro)

---

**Status:** Pronto para migração  
**Tempo:** ~30 minutos de implementação + testes  
**Risco:** Baixo (mudanças na camada de apresentação)
