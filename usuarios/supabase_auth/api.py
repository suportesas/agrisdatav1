"""
API Proxy Seguro para Supabase
Endpoints que não expõem chaves de API
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from core.supabase_config import supabase_auth, supabase_client
import json
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def auth_config(request):
    """
    Retorna configuração de autenticação SEM expor chaves de API.
    Endpoint público - retorna apenas URL de redirecionamento segura.
    
    Resposta:
    {
      "oauth_enabled": true,
      "oauth_providers": ["google"],
      "auth_mode": "supabase"
    }
    """
    return JsonResponse({
        "oauth_enabled": bool(getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')),
        "oauth_providers": ["google"] if getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '') else [],
        "auth_mode": getattr(settings, 'AUTH_MODE', 'django'),
    })


@require_http_methods(["POST"])
@csrf_exempt  # Protegido por verificação de token JWT
def validate_token(request):
    """
    Valida um token JWT do Supabase.
    Endpoint protegido - apenas para tokens válidos.
    
    Requer header: Authorization: Bearer <token>
    
    Resposta:
    {
      "valid": true,
      "user_id": "uuid",
      "email": "user@example.com",
      "empresa_id": 1
    }
    """
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        if not token:
            return JsonResponse({'valid': False, 'error': 'Token ausente'}, status=401)
        
        # Validar token via Supabase (usando chave privada no backend)
        # Este é um exemplo - Supabase SDK não tem método built-in para isso
        # Alternativa: decodificar JWT e validar signature localmente
        
        from jwt import decode, DoesNotExist
        
        try:
            payload = decode(
                token,
                settings.SUPABASE_ANON_KEY,  # Usar ANON_KEY para verificar assinatura
                algorithms=['HS256'],
                options={"verify_exp": True}
            )
            
            return JsonResponse({
                'valid': True,
                'user_id': payload.get('sub'),
                'email': payload.get('email'),
                'empresa_id': payload.get('user_metadata', {}).get('empresa_id'),
            })
        except Exception as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return JsonResponse({'valid': False, 'error': 'Token inválido'}, status=401)
    
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return JsonResponse({'error': 'Erro ao validar token'}, status=500)


@require_http_methods(["POST"])
@csrf_exempt  # CSRF não se aplica a APIs sem session
def auth_callback_proxy(request):
    """
    Proxy para callback de autenticação.
    Recebe o código de autorização e troca por sessão no backend.
    
    POST: {
      "code": "auth_code_from_oauth",
      "provider": "google"
    }
    
    Resposta:
    {
      "success": true,
      "user": {...},
      "session_token": "..."
    }
    """
    try:
        body = json.loads(request.body)
        code = body.get('code')
        provider = body.get('provider', 'google')
        
        if not code:
            return JsonResponse({'success': False, 'error': 'Code ausente'}, status=400)
        
        # Trocar código por sessão usando SERVICE_ROLE_KEY no backend
        # (JavaScript não terá acesso à SERVICE_ROLE_KEY)
        
        # TODO: Implementar exchange com SERVICE_ROLE_KEY
        # Este é um ponto de flexibilidade para migração futura
        
        return JsonResponse({
            'success': False,
            'error': 'Endpoint em desenvolvimento',
            'message': 'Use /auth/callback/google/ direto por enquanto'
        }, status=501)
    
    except Exception as e:
        logger.error(f"Auth callback error: {str(e)}")
        return JsonResponse({'error': 'Erro no callback'}, status=500)


@require_http_methods(["GET"])
@login_required
def current_user(request):
    """
    Retorna informações do usuário logado.
    Endpoint protegido - requer autenticação Django.
    
    Resposta:
    {
      "user_id": "uuid",
      "email": "...",
      "first_name": "...",
      "empresa_id": 1,
      "tipo": "GERENTE"
    }
    """
    from usuarios.models import Usuario
    
    try:
        usuario = Usuario.objects.get(user_ptr=request.user)
        
        return JsonResponse({
            'user_id': str(usuario.user_ptr.id),
            'email': usuario.email,
            'first_name': usuario.first_name,
            'last_name': usuario.last_name,
            'empresa_id': usuario.empresa_id,
            'tipo': usuario.tipo,
        })
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Current user error: {str(e)}")
        return JsonResponse({'error': 'Erro ao buscar usuário'}, status=500)
