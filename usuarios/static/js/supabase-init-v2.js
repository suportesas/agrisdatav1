// ============================================================
// SUPABASE AUTH - VERSÃO SEGURA (SEM EXPOSIÇÃO DE CHAVES)
// ============================================================
// 🔐 IMPORTANTE: Chaves de API NÃO são expostas no frontend
// Todas as operações sensíveis usam backend proxy
// OAuth usa Supabase ANON_KEY carregada dinamicamente

// ============================================================
// 1. ENDPOINTS SEGUROS DO BACKEND
// ============================================================

const API = {
  authConfig: '/auth/api/auth-config/',
  currentUser: '/auth/api/current-user/',
  validateToken: '/auth/api/validate-token/',
  callbackProxy: '/auth/api/callback-proxy/',
  
  // Endpoints existentes (backend)
  login: '/auth/login/',
  register: '/auth/register/',
  logout: '/auth/logout/',
};

// ============================================================
// 2. ESTADO GLOBAL
// ============================================================

let supabaseClient = null;
let authConfig = null;

// ============================================================
// 3. CARREGAR CONFIGURAÇÃO SEGURA
// ============================================================

async function loadAuthConfig() {
  try {
    if (authConfig) return authConfig;
    
    const response = await fetch(API.authConfig);
    authConfig = await response.json();
    
    console.log('✓ Auth config loaded');
    console.log('  OAuth enabled:', authConfig.oauth_enabled);
    
    return authConfig;
  } catch (error) {
    console.error('Erro ao carregar config:', error);
    return null;
  }
}

// ============================================================
// 4. INICIALIZAR SUPABASE (APENAS PARA OAUTH)
// ============================================================
// ⚠️ ANON_KEY é pública por design - usada apenas para OAuth

async function initSupabaseForOAuth() {
  try {
    if (supabaseClient) return supabaseClient;
    
    // Carregar config do backend
    const config = await loadAuthConfig();
    if (!config) {
      console.warn('⚠️  Não foi possível carregar config de OAuth');
      return null;
    }
    
    if (!config.oauth_enabled) {
      console.log('ℹ️  OAuth não habilitado');
      return null;
    }
    
    // Verificar se SDK está carregado
    if (typeof window.supabase === 'undefined') {
      console.error('❌ Supabase SDK não carregado');
      console.log('   Include: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js"></script>');
      return null;
    }
    
    // Tentar obter chaves de elemento seguro no DOM
    // Alternativa: usar localStorage temporário após resposta segura do backend
    const configEl = document.getElementById('supabase-config-oauth');
    if (!configEl) {
      console.warn('⚠️  Elemento de config OAuth não encontrado');
      return null;
    }
    
    const url = configEl.getAttribute('data-url');
    const anonKey = configEl.getAttribute('data-key');
    
    if (!url || !anonKey) {
      console.warn('⚠️  Chaves OAuth incompletas');
      return null;
    }
    
    supabaseClient = window.supabase.createClient(url, anonKey);
    console.log('✓ Supabase OAuth inicializado');
    
    return supabaseClient;
  } catch (error) {
    console.error('Erro ao inicializar Supabase:', error);
    return null;
  }
}

// ============================================================
// 5. GOOGLE OAUTH LOGIN
// ============================================================

async function loginWithGoogle() {
  try {
    const supabase = await initSupabaseForOAuth();
    
    if (!supabase) {
      showAlert('OAuth não configurado. Use email/senha ou contate suporte.', 'warning');
      return false;
    }
    
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin + '/auth/callback/google/',
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });
    
    if (error) {
      console.error('OAuth error:', error);
      showAlert('Erro ao conectar com Google: ' + error.message, 'danger');
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('LoginWithGoogle error:', error);
    showAlert('Erro ao fazer login com Google', 'danger');
    return false;
  }
}

// ============================================================
// 6. EMAIL/SENHA LOGIN (BACKEND PROXY)
// ============================================================
// ⚠️ NUNCA use Supabase SDK direto para isso
// Backend maneja SERVICE_ROLE_KEY de forma segura

async function loginWithEmail(email, password) {
  try {
    const response = await fetch(API.login, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ email, password }),
      credentials: 'include',
    });
    
    const data = await response.json();
    
    if (!data.success) {
      showAlert(data.message || 'Erro ao fazer login', 'danger');
      return false;
    }
    
    console.log('✓ Login bem-sucedido');
    window.location.href = data.redirect || '/dashboard/';
    return true;
  } catch (error) {
    console.error('LoginWithEmail error:', error);
    showAlert('Erro ao fazer login', 'danger');
    return false;
  }
}

// ============================================================
// 7. EMAIL/SENHA REGISTRO (BACKEND PROXY)
// ============================================================

async function registerWithEmail(email, password, firstName, lastName) {
  try {
    const response = await fetch(API.register, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      }),
    });
    
    const data = await response.json();
    
    if (!data.success) {
      showAlert(data.message || 'Erro ao registrar', 'danger');
      return false;
    }
    
    showAlert('Conta criada com sucesso! Faça login.', 'success');
    window.location.href = data.redirect || '/auth/login-page/';
    return true;
  } catch (error) {
    console.error('RegisterWithEmail error:', error);
    showAlert('Erro ao registrar', 'danger');
    return false;
  }
}

// ============================================================
// 8. VALIDAR SESSÃO / OBTER USUÁRIO ATUAL
// ============================================================

async function validateSession() {
  try {
    const response = await fetch(API.currentUser);
    
    if (!response.ok) {
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Validate session error:', error);
    return null;
  }
}

async function getCurrentUser() {
  return validateSession();
}

// ============================================================
// 9. LOGOUT
// ============================================================

async function logoutUser() {
  try {
    const response = await fetch(API.logout);
    console.log('✓ Logout realizado');
    window.location.href = '/auth/login-page/';
    return true;
  } catch (error) {
    console.error('LogoutUser error:', error);
    return false;
  }
}

// ============================================================
// UTILITÁRIOS
// ============================================================

function getCsrfToken() {
  const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  if (token) return token;
  
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

function showAlert(message, type = 'info') {
  console.log(`[${type.toUpperCase()}] ${message}`);
  
  const alertHtml = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
  `;
  
  const alertContainer = document.getElementById('alerts-container') || 
                        document.querySelector('.container');
  
  if (alertContainer) {
    const div = document.createElement('div');
    div.innerHTML = alertHtml;
    alertContainer.insertBefore(div.firstElementChild, alertContainer.firstChild);
  }
}

// ============================================================
// INICIALIZAÇÃO
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  console.log('🔐 Supabase Auth (Secure Mode) - iniciado');
  
  // Carregar configuração
  const config = await loadAuthConfig();
  
  if (config) {
    console.log('✓ Config carregada');
    console.log('  OAuth:', config.oauth_enabled ? 'habilitado' : 'desabilitado');
    console.log('  Auth mode:', config.auth_mode);
  }
  
  // Validar sessão existente
  const user = await validateSession();
  if (user) {
    console.log('✓ Usuário logado:', user.email);
  }
});

// ============================================================
// EXPORTAR GLOBALMENTE
// ============================================================

window.SupabaseAuth = {
  // Public functions
  loadAuthConfig,
  loginWithGoogle,
  loginWithEmail,
  registerWithEmail,
  validateSession,
  getCurrentUser,
  logoutUser,
  
  // Utilities
  getCsrfToken,
  showAlert,
  
  // Debug
  _debug: {
    initSupabaseForOAuth,
    API,
  }
};

console.log('✓ SupabaseAuth available as window.SupabaseAuth');
