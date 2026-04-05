"""
Context Processor para Supabase
Injeta configurações Supabase em todos os templates
"""

from django.conf import settings


def supabase_context(request):
    """
    Adiciona contexto Supabase a todos os templates
    """
    return {
        'supabase_url': getattr(settings, 'SUPABASE_URL', ''),
        'supabase_anon_key': getattr(settings, 'SUPABASE_ANON_KEY', ''),
        'auth_mode': getattr(settings, 'AUTH_MODE', 'django'),
        'google_oauth_enabled': bool(getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')),
    }
