"""
Utilitários de controle de acesso baseado em Roles (Funções).

Uso em views:
    from core.role_permissions import perm_required

    @perm_required('compras.add_pedidocompra')
    def pedido_create(request):
        ...

    @perm_required('compras.delete_pedidocompra', raise_exception=True)
    def pedido_delete(request, pk):
        ...

Bypass automático para:
  - request.user.is_superuser
  - request.user.is_admin_empresa()
"""

import functools
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


def has_role_perm(user, codename: str) -> bool:
    """
    Verifica se o usuário tem a permissão via Roles/Groups.
    Superuser e admin_empresa sempre retornam True.

    codename pode ser 'app_label.action_model' ou apenas 'action_model'.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'is_admin_empresa') and user.is_admin_empresa():
        return True
    # Normaliza codename para formato 'app_label.codename'
    if '.' in codename:
        return user.has_perm(codename)
    # Sem app_label: verifica em todos os apps (less efficient, use sparingly)
    return any(p.codename == codename for p in user.get_all_permissions())


def perm_required(codename: str, redirect_url: str = 'dashboard:index', raise_exception: bool = False):
    """
    Decorator que protege uma view exigindo que o usuário tenha a permissão.

    Args:
        codename: Permissão no formato 'app_label.action_model' (ex: 'compras.view_pedidocompra')
        redirect_url: URL name para redirecionar em caso de acesso negado
        raise_exception: Se True, retorna 403 em vez de redirecionar (útil para AJAX)
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                return redirect(getattr(settings, 'LOGIN_URL', 'login'))

            if has_role_perm(request.user, codename):
                return view_func(request, *args, **kwargs)

            # Acesso negado
            is_ajax = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('Accept', '')
            )
            if raise_exception or is_ajax:
                return JsonResponse({'error': 'Permissão negada.', 'codename': codename}, status=403)

            messages.error(
                request,
                '⛔ Você não tem permissão para acessar esta área. '
                'Solicite ao administrador da empresa que ajuste suas Funções.'
            )
            return redirect(redirect_url)

        return wrapper
    return decorator


def any_perm_required(*codenames, redirect_url: str = 'dashboard:index'):
    """
    Decorator que exige que o usuário tenha QUALQUER UMA das permissões listadas.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if any(has_role_perm(request.user, c) for c in codenames):
                return view_func(request, *args, **kwargs)
            messages.error(request, '⛔ Você não tem permissão para acessar esta área.')
            return redirect(redirect_url)
        return wrapper
    return decorator
