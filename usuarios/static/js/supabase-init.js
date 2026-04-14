// Supabase JavaScript SDK - VERSÃO SEGURA
// ⚠️ NÃO expõe chaves de API sensíveis no frontend
// Usa backend proxy para operações de dados

// CONFIGURAÇÃO SEGURA - Apenas endpoints publicamente seguros
const API_CONFIG = {
  authConfigUrl: '/auth/api/auth-config/',
  currentUserUrl: '/auth/api/current-user/',
  validateTokenUrl: '/auth/api/validate-token/',
  callbackProxyUrl: '/auth/api/callback-proxy/',
};

// SUPABASE CLIENT - Carregado dinamicamente apenas se necessário
let supabaseClient = null;
let supabaseConfig = null;

// ===================================================================
// 1. CARREGAR CONFIGURAÇÃO SEGURA DO BACKEND
// ===================================================================

async function loadAuthConfig() {
  try {
    const response = await fetch(API_CONFIG.authConfigUrl);
    const config = await response.json();
    
    console.log('✓ Auth config loaded (sem chaves de API)');
    return config;
  } catch (error) {
    console.error('Erro ao carregar configuração:', error);
    return null;
  }
}

// ===================================================================
// 2. INICIALIZAR SUPABASE (APENAS PARA OAUTH)
// ===================================================================
// ⚠️ NOTA: ANON_KEY é tecnicamente pública por design do Supabase
// Usado APENAS para Google OAuth (autenticação)
// Para operações de dados, use o backend proxy em /auth/api/

async function initSupabaseForOAuth() {
  try {
    if (supabaseClient) return supabaseClient;
    
    // Se variáveis estão no DOM (para compatibilidade), usar
    // Caso contrário, NUNCA exponha chaves aqui
    const configElement = document.getElementById('supabase-config');
    
    if (!configElement) {
      console.warn('⚠️  Supabase config element not found. OAuth may not work.');
      console.log('   → Use: <script id="supabase-config" data-url="..." data-key="..."></script>');
      return null;
    }
    
    const url = configElement.getAttribute('data-url');
    const anonKey = configElement.getAttribute('data-key');
    
    if (!url || !anonKey) {
      console.warn('⚠️  Supabase credentials missing from config element');
      return null;
    }
    
    if (typeof window.supabase === 'undefined') {
      console.error('❌ Supabase library not loaded. Include: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js"></script>');
      return null;
    }

    supabaseClient = window.supabase.createClient(url, anonKey, {
      auth: {
        storage: window.sessionStorage,
        persistSession: true,
        autoRefreshToken: true,
      },
    });
    supabaseConfig = { url, anonKey };
    
    console.log('✓ Supabase client initialized for OAuth');
    return supabaseClient;
  } catch (error) {
    console.error('Erro ao inicializar Supabase:', error);
    return null;
  }
}

// ===================================================================
// 3. GOOGLE OAUTH LOGIN (Frontend)
// ===================================================================

async function loginWithGoogle() {
  try {
    const supabase = await initSupabaseForOAuth();
    
    if (!supabase) {
      showAlert('❌ Autenticação não configurada. Contate suporte.', 'danger');
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
      console.error('Google OAuth error:', error);
      showAlert('❌ Erro ao conectar com Google: ' + error.message, 'danger');
      return false;
    }
    
    console.log('✓ Google OAuth iniciado');
    return true;
  } catch (error) {
    console.error('Google login error:', error);
    showAlert('❌ Erro ao fazer login com Google', 'danger');
    return false;
  }
}

// ===================================================================
// 4. EMAIL/SENHA LOGIN (Backend Proxy)
// ===================================================================
// ⚠️ IMPORTANTE: Não use Supabase client para isso
// Use o endpoint /auth/login/ do Django backend

async function loginWithEmail(email, password) {
  try {
    const response = await fetch('/auth/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ email, password }),
      credentials: 'include', // Incluir cookies de sessão
    });
    
    const data = await response.json();
    
    if (!data.success) {
      showAlert('❌ ' + (data.message || 'Erro ao fazer login'), 'danger');
      return false;
    }
    
    console.log('✓ Login bem-sucedido');
    window.location.href = data.redirect || '/dashboard/';
    return true;
  } catch (error) {
    console.error('Email login error:', error);
    showAlert('❌ Erro ao fazer login', 'danger');
    return false;
  }
}

// ===================================================================
// 5. EMAIL/SENHA REGISTRO (Backend Proxy)
// ===================================================================

async function registerWithEmail(email, password, firstName, lastName) {
  try {
    const response = await fetch('/auth/register/', {
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
      showAlert('❌ ' + (data.message || 'Erro ao registrar'), 'danger');
      return false;
    }
    
    console.log('✓ Registro bem-sucedido. Faça login...');
    window.location.href = data.redirect || '/auth/login-page/';
    return true;
  } catch (error) {
    console.error('Register error:', error);
    showAlert('❌ Erro ao registrar', 'danger');
    return false;
  }
}

// ===================================================================
// 6. VALIDAR SESSÃO (Frontend)
// ===================================================================

async function validateSession() {
  try {
    const response = await fetch(API_CONFIG.currentUserUrl);
    
    if (!response.ok) {
      console.warn('⚠️  Sessão expirada');
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error('Session validation error:', error);
    return null;
  }
}

// ===================================================================
// 7. OBTER USUÁRIO ATUAL
// ===================================================================

async function getCurrentUser() {
  return await validateSession();
}

// ===================================================================
// 8. FAZER LOGOUT
// ===================================================================

async function logoutUser() {
  try {
    const response = await fetch('/auth/logout/');
    console.log('✓ Logout realizado');
    window.location.href = '/auth/login-page/';
    return true;
  } catch (error) {
    console.error('Logout error:', error);
    return false;
  }
}

// ===================================================================
// UTILITÁRIOS
// ===================================================================

function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
         document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1] || '';
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
    alertContainer.insertAdjacentHTML('afterbegin', alertHtml);
  }
}

// ===================================================================
// INICIAÇÃO AUTOMÁTICA
// ===================================================================

// Carregar configuração ao iniciar página
document.addEventListener('DOMContentLoaded', async () => {
  console.log('🔐 Supabase Auth (Secure Mode) initialized');
  const config = await loadAuthConfig();
  
  if (config) {
    console.log('✓ Auth config loaded');
    console.log('✓ Google OAuth:', config.oauth_enabled ? 'enabled' : 'disabled');
  }
});

// Exportar funções globalmente
window.SupabaseAuth = {
  initSupabaseForOAuth,
  loginWithGoogle,
  loginWithEmail,
  registerWithEmail,
  validateSession,
  getCurrentUser,
  logoutUser,
  loadAuthConfig,
};
    }
    
    return true;
  } catch (error) {
    console.error('OAuth login error:', error);
    showAlert('Erro inesperado ao conectar com Google', 'danger');
    return false;
  }
}

// Email/Password Registration
async function registerWithEmail(email, password, firstName, lastName) {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data, error } = await supabase.auth.signUp({
      email: email,
      password: password,
      options: {
        data: {
          first_name: firstName,
          last_name: lastName,
        },
      },
    });
    
    if (error) {
      console.error('Registration error:', error);
      return { success: false, message: error.message };
    }
    
    return { 
      success: true, 
      message: 'Conta criada com sucesso! Verifique seu email.',
      user: data.user 
    };
  } catch (error) {
    console.error('Registration error:', error);
    return { success: false, message: 'Erro inesperado ao criar conta' };
  }
}

// Email/Password Login
async function loginWithEmail(email, password) {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email,
      password: password,
    });
    
    if (error) {
      console.error('Login error:', error);
      return { success: false, message: error.message };
    }
    
    return { 
      success: true, 
      message: 'Login realizado com sucesso!',
      user: data.user,
      session: data.session
    };
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, message: 'Erro inesperado ao fazer login' };
  }
}

// Get Current Session
async function getCurrentSession() {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data: { session }, error } = await supabase.auth.getSession();
    
    if (error) {
      console.error('Session error:', error);
      return null;
    }
    
    return session;
  } catch (error) {
    console.error('Session error:', error);
    return null;
  }
}

// Get Current User
async function getCurrentUser() {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data: { user }, error } = await supabase.auth.getUser();
    
    if (error) {
      console.error('User error:', error);
      return null;
    }
    
    return user;
  } catch (error) {
    console.error('User error:', error);
    return null;
  }
}

// Logout
async function logoutUser() {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { error } = await supabase.auth.signOut();
    
    if (error) {
      console.error('Logout error:', error);
      return false;
    }
    
    return true;
  } catch (error) {
    console.error('Logout error:', error);
    return false;
  }
}

// Password Reset Request
async function requestPasswordReset(email) {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/auth/reset-password-confirm/',
    });
    
    if (error) {
      console.error('Password reset error:', error);
      return { success: false, message: error.message };
    }
    
    return { 
      success: true, 
      message: 'Email de recuperação enviado com sucesso' 
    };
  } catch (error) {
    console.error('Password reset error:', error);
    return { success: false, message: 'Erro inesperado ao solicitar recuperação' };
  }
}

// Helper: Show Alert Message
function showAlert(message, type = 'danger') {
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.innerHTML = `
    <i class="bi bi-${type === 'danger' ? 'exclamation-triangle' : 'check-circle'}"></i>
    ${message}
  `;
  
  const formWrapper = document.querySelector('.form-wrapper');
  if (formWrapper) {
    formWrapper.insertBefore(alert, formWrapper.firstChild);
    setTimeout(() => alert.remove(), 5000);
  }
}

// Listen for Auth State Changes
function onAuthStateChange(callback) {
  if (!supabase) {
    console.error('Supabase not initialized');
    return null;
  }
  
  return supabase.auth.onAuthStateChange(callback);
}

// Initialize Supabase on page load
document.addEventListener('DOMContentLoaded', async () => {
  await initSupabase();
  
  // Check if user is already logged in
  const user = await getCurrentUser();
  if (user) {
    console.log('User already logged in:', user.email);
  }
});

// Export functions for use in standalone environment
if (typeof window !== 'undefined') {
  window.SupabaseAuth = {
    initSupabase,
    loginWithGoogle,
    registerWithEmail,
    loginWithEmail,
    getCurrentSession,
    getCurrentUser,
    logoutUser,
    requestPasswordReset,
    showAlert,
    onAuthStateChange,
  };
}
