"""
Views de autenticação com Supabase
Email/Senha e Google OAuth
"""

from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login as django_login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.supabase_config import supabase_auth
from usuarios.models import Usuario
from usuarios.models_supabase import SupabaseUsuarioSync, LoginSupabase
import logging
import json

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extrai IP do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@require_http_methods(["POST"])
def supabase_register(request):
    """
    Registra novo usuário via email/senha
    POST: {email, password, first_name, last_name}
    """
    try:
        email = request.POST.get('email') or json.loads(request.body).get('email')
        password = request.POST.get('password') or json.loads(request.body).get('password')
        first_name = request.POST.get('first_name', '') or json.loads(request.body).get('first_name', '')
        last_name = request.POST.get('last_name', '') or json.loads(request.body).get('last_name', '')
    except:
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
    
    # Validações
    if not email or not password:
        return JsonResponse({'error': 'Email e senha são obrigatórios'}, status=400)
    
    if len(password) < 6:
        return JsonResponse({'error': 'Senha deve ter mínimo 6 caracteres'}, status=400)
    
    try:
        # Registra no Supabase Auth
        response = supabase_auth.register_with_email(
            email=email,
            password=password,
            user_metadata={
                'first_name': first_name,
                'last_name': last_name
            }
        )
        
        if 'error' in response:
            logger.error(f"✗ Erro ao registrar no Supabase: {response['error']}")
            return JsonResponse({'error': response['error']}, status=400)
        
        # Verifica se usuário já existe
        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # Cria usuário local
            usuario = Usuario.objects.create(
                username=email,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
        
        # Sincroniza com Supabase
        SupabaseUsuarioSync.objects.update_or_create(
            usuario=usuario,
            defaults={
                'supabase_uid': response['user'].id,
                'sincronizado': True
            }
        )
        
        logger.info(f"✓ Usuário registrado e sincronizado: {email}")
        return JsonResponse({
            'success': True,
            'message': 'Registrado com sucesso. Faça login para continuar.',
            'redirect': '/login/'
        })
    
    except Exception as e:
        logger.error(f"✗ Erro ao registrar: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def supabase_login(request):
    """
    Login com email/senha
    POST: {email, password}
    """
    try:
        email = request.POST.get('email') or json.loads(request.body).get('email')
        password = request.POST.get('password') or json.loads(request.body).get('password')
    except:
        email = request.POST.get('email')
        password = request.POST.get('password')
    
    ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    if not email or not password:
        return JsonResponse({'error': 'Email e senha são obrigatórios'}, status=400)
    
    # Tenta login no Supabase
    response = supabase_auth.login_with_email(email, password)
    
    if 'error' in response:
        # Registra falha
        LoginSupabase.objects.create(
            email=email,
            origem='email',
            sucesso=False,
            motivo_falha='invalid_credentials',
            ip_address=ip,
            user_agent=user_agent
        )
        logger.warning(f"✗ Falha de login: {email}")
        return JsonResponse({'error': 'Email ou senha inválidos'}, status=401)
    
    try:
        # Busca usuário sincronizado
        sync = SupabaseUsuarioSync.objects.get(
            supabase_uid=response['user'].id
        )
        usuario = sync.usuario
        
    except SupabaseUsuarioSync.DoesNotExist:
        # Tenta encontrar por email
        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # Cria novo usuário
            usuario = Usuario.objects.create(
                username=email,
                email=email,
                first_name=response['user'].user_metadata.get('first_name', '') if response['user'].user_metadata else '',
                last_name=response['user'].user_metadata.get('last_name', '') if response['user'].user_metadata else '',
                is_active=True
            )
        
        # Sincroniza
        SupabaseUsuarioSync.objects.create(
            usuario=usuario,
            supabase_uid=response['user'].id
        )
    
    # Django login
    django_login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
    request.session.set_expiry(0)
    
    # Registra sucesso
    LoginSupabase.objects.create(
        usuario=usuario,
        email=email,
        origem='email',
        sucesso=True,
        ip_address=ip,
        user_agent=user_agent
    )
    
    logger.info(f"✓ Login bem-sucedido: {email}")
    
    return JsonResponse({
        'success': True,
        'redirect': '/dashboard/',
        'user': {
            'id': usuario.id,
            'email': usuario.email,
            'name': usuario.get_full_name()
        }
    })


@require_http_methods(["GET"])
def login_page(request):
    """
    Renderiza página de login com contexto Supabase
    GET: /auth/login-page/
    """
    from django.conf import settings
    
    context = {
        'supabase_url': getattr(settings, 'SUPABASE_URL', ''),
        'supabase_anon_key': getattr(settings, 'SUPABASE_ANON_KEY', ''),
    }
    
    return render(request, 'usuarios/supabase_login.html', context)


@require_http_methods(["GET"])
def register_page(request):
    """
    Renderiza página de registro com contexto Supabase
    GET: /auth/register-page/
    """
    from django.conf import settings
    
    context = {
        'supabase_url': getattr(settings, 'SUPABASE_URL', ''),
        'supabase_anon_key': getattr(settings, 'SUPABASE_ANON_KEY', ''),
    }
    
    return render(request, 'usuarios/supabase_register.html', context)


@csrf_exempt
def google_oauth_callback(request):
    """
    Callback após autenticação Google
    O frontend usa Supabase JS SDK para handle do OAuth
    Este é apenas um redirect de confirmação
    """
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error:
        logger.error(f"✗ Erro Google OAuth: {error}")
        return redirect('/login/?error=google_auth_failed')
    
    if not code:
        return redirect('/login/?error=missing_code')
    
    logger.info("✓ Google OAuth callback recebido")
    return redirect('/dashboard/')


def logout_view(request):
    """
    Faz logout do usuário
    Remove sessão Django e redireciona para login
    """
    from django.contrib.auth import logout
    logout(request)
    supabase_auth.logout()
    return redirect('/login/')
