"""
Context Processor para Supabase (Seguro)
Injeta apenas configurações publicamente seguras em templates
NÃO expõe chaves de API
"""

from django.conf import settings


def supabase_context(request):
    """
    Adiciona contexto Supabase a todos os templates.
    
    ⚠️  SEGURANÇA: Não injeta SUPABASE_URL nem SUPABASE_ANON_KEY.
    
    Frontend obtém configuração via:
    - GET /auth/api/auth-config/ (endpoint seguro)
    - JWT tokens no header Authorization
    - Backend proxy em /auth/api/
    
    Retorna:
    - auth_mode: Modo de autenticação ativo
    - google_oauth_enabled: Se Google OAuth está disponível
    """
    return {
        'auth_mode': getattr(settings, 'AUTH_MODE', 'django'),
        'google_oauth_enabled': bool(getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')),
        'api_auth_config_url': '/auth/api/auth-config/',
        'api_current_user_url': '/auth/api/current-user/',
    }
