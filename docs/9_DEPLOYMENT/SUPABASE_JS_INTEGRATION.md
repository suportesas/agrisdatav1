# Supabase JavaScript Integration

## Instalação do SDK

Para usar autenticação Supabase no frontend, adicione o SDK aos seus templates:

### 1. **Importar a libra Supabase (no HEAD ou antes de usar)**

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@v2"></script>
```

### 2. **Importar o script de inicialização**

```html
<script src="{% static 'js/supabase-init.js' %}"></script>
```

## Páginas de Autenticação

### Login Page
- **URL**: `/auth/login-page/`
- **Template**: `usuarios/supabase_login.html`
- **Recursos**:
  - Split layout (branding + form)
  - Email/Password login
  - Google OAuth button
  - "Esqueceu senha?" link
  - "Criar conta" link

### Register Page
- **URL**: `/auth/register-page/`
- **Template**: `usuarios/supabase_register.html`
- **Recursos**:
  - Split layout (branding + form)
  - Email/Password registration
  - Password strength meter (JavaScript)
  - Google OAuth button
  - Form validation

## Funções Disponíveis

Todas as funções são acessíveis via `window.SupabaseAuth`:

### Email/Password Authentication

```javascript
// Registrar novo usuário
const result = await SupabaseAuth.registerWithEmail(
  email = 'user@example.com',
  password = 'senha123',
  firstName = 'João',
  lastName = 'Silva'
);

if (result.success) {
  console.log('Usuário criado:', result.user);
} else {
  console.error('Erro:', result.message);
}
```

```javascript
// Login com email/senha
const result = await SupabaseAuth.loginWithEmail(
  email = 'user@example.com',
  password = 'senha123'
);

if (result.success) {
  console.log('Login bem-sucedido:', result.user);
  // Redirecionar para dashboard
  window.location.href = '/dashboard/';
} else {
  console.error('Email ou senha inválidos');
}
```

### Google OAuth

```javascript
// Iniciar login com Google
const success = await SupabaseAuth.loginWithGoogle();

if (success) {
  console.log('Redirecionando para Google...');
  // O usuário será redirecionado para Google e depois para /auth/callback/google/
}
```

### Session Management

```javascript
// Obter sessão atual
const session = await SupabaseAuth.getCurrentSession();

if (session) {
  console.log('Sessão ativa:', session.user.email);
}
```

```javascript
// Obter usuário atual
const user = await SupabaseAuth.getCurrentUser();

if (user) {
  console.log('Usuário:', user.email);
}
```

```javascript
// Logout
const success = await SupabaseAuth.logoutUser();

if (success) {
  window.location.href = '/auth/login-page/';
}
```

### Password Recovery

```javascript
// Solicitar reset de senha
const result = await SupabaseAuth.requestPasswordReset(
  email = 'user@example.com'
);

if (result.success) {
  console.log('Email enviado com sucesso');
}
```

### Auth State Listener

```javascript
// Escutar mudanças de estado de autenticação
SupabaseAuth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN') {
    console.log('Usuário fez login:', session.user.email);
  } else if (event === 'SIGNED_OUT') {
    console.log('Usuário fez logout');
  }
});
```

## Exemplos de Implementação

### Exemplo 1: Validar Formulário de Login

```html
<form id="loginForm">
  <input type="email" id="email" required>
  <input type="password" id="password" required>
  <button type="submit">Entrar</button>
</form>

<script>
document.getElementById('loginForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  
  const result = await SupabaseAuth.loginWithEmail(email, password);
  
  if (result.success) {
    window.location.href = '/dashboard/';
  } else {
    alert('Erro: ' + result.message);
  }
});
</script>
```

### Exemplo 2: Password Strength Meter

```javascript
function updatePasswordMeter() {
  const password = document.getElementById('password').value;
  const meter = document.getElementById('passwordMeter');
  
  let strength = 0;
  if (password.length >= 6) strength++;
  if (!/[a-z]/.test(password)) strength++;
  if (!/[A-Z]/.test(password)) strength++;
  if (!/[0-9]/.test(password)) strength++;
  if (!/[^a-zA-Z0-9]/.test(password)) strength++;
  
  const colors = ['#ff6b6b', '#ffa94d', '#74c0fc', '#51cf66', '#37b24d'];
  meter.style.width = (strength * 20) + '%';
  meter.style.background = colors[strength - 1] || '#ddd';
}

document.getElementById('password').addEventListener('input', updatePasswordMeter);
```

### Exemplo 3: Integrar Google OAuth em Button Customizado

```html
<button type="button" id="googleBtn">
  <i class="bi bi-google"></i> Entrar com Google
</button>

<script>
document.getElementById('googleBtn').addEventListener('click', async () => {
  const success = await SupabaseAuth.loginWithGoogle();
  if (!success) {
    alert('Erro ao conectar com Google');
  }
});
</script>
```

## Configuração no settings.py

As seguintes variáveis de ambiente são necessárias:

```python
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
AUTH_MODE = os.getenv('AUTH_MODE', 'django')  # 'django', 'dual', ou 'supabase'
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
```

## Endpoints API

### Register (POST)
```
POST /auth/register/
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=senha123&first_name=João&last_name=Silva
```

**Response:**
```json
{
  "success": true,
  "message": "Registrado com sucesso. Faça login para continuar.",
  "redirect": "/login/"
}
```

### Login (POST)
```
POST /auth/login/
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=senha123
```

**Response:**
```json
{
  "success": true,
  "redirect": "/dashboard/",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "João Silva"
  }
}
```

### Logout (GET)
```
GET /auth/logout/
```

### Google OAuth Callback (GET)
```
GET /auth/callback/google/?code=...&state=...
```

## Troubleshooting

### "Supabase library not loaded"
- Certifique-se de que o script do Supabase JS está importado ANTES de supabase-init.js
- Ordem correta:
  1. `<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@v2"></script>`
  2. `<script src="{% static 'js/supabase-init.js' %}"></script>`

### OAuth não funciona
- Verifique se `GOOGLE_OAUTH_CLIENT_ID` está configurado em settings.py
- Configure o callback URL em Google Cloud Console
- Teste em localhost:8000 vs 127.0.0.1:8000 (podem ser diferentes)

### Usuário não sincroniza com Django
- Verifique logs: `LoginSupabase.objects.all().order_by('-data_hora')`
- Verifique `SupabaseUsuarioSync`: `SupabaseUsuarioSync.objects.all()`
- Execute migrations: `python manage.py migrate usuarios`

## Performance

O Supabase SDK é ~300KB minificado. Para otimizar:

1. **Usar CDN com cache**: Já está usando jsdelivr.net
2. **Lazy load**: Carregar apenas em páginas de auth
3. **Minification**: Supabase JS já vem minificado

## Segurança

- ✅ ANON_KEY é segura (permissões limitadas por RLS)
- ✅ Não exponha SERVICE_ROLE_KEY no frontend
- ✅ Todas requests são via HTTPS
- ✅ RLS policies isolam dados por tenant
- ✅ CSRF protection via `{% csrf_token %}`

## Próximos Passos

1. [ ] Adicionar suporte 2FA (two-factor authentication)
2. [ ] Implementar social login (GitHub, Microsoft)
3. [ ] Email verification obrigatória
4. [ ] Session timeout automático
5. [ ] Remember me (persistent login)
