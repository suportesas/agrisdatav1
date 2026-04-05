// Supabase JavaScript SDK Initialization
// This file initializes the Supabase client and handles OAuth flows

// Configuration - these should match your Django settings
const SUPABASE_CONFIG = {
  url: '{{ supabase_url }}',
  anonKey: '{{ supabase_anon_key }}',
  redirectUrl: window.location.origin + '/auth/callback/google/'
};

// Initialize Supabase Client
let supabase = null;

async function initSupabase() {
  if (typeof window.supabase === 'undefined') {
    console.error('Supabase library not loaded. Make sure to include the Supabase JS SDK in your HTML.');
    return null;
  }
  
  supabase = window.supabase.createClient(
    SUPABASE_CONFIG.url,
    SUPABASE_CONFIG.anonKey
  );
  
  return supabase;
}

// Google OAuth Login
async function loginWithGoogle() {
  try {
    if (!supabase) {
      await initSupabase();
    }
    
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: SUPABASE_CONFIG.redirectUrl,
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
