"""Checagem de permissão para os atalhos de compras.

Admin da empresa (Usuario.is_admin_empresa()) já contorna o
RoleEnforcementMiddleware para o módulo /compras/ inteiro — ele consegue
criar Solicitação, Cotação e Pedido manualmente sem nenhuma permissão extra.
Os atalhos (Central de Alertas, Pedido Direto, Emergencial) são só um jeito
mais rápido de fazer a mesma coisa, então o admin tem acesso a eles por
padrão; a permissão Django é o mecanismo para DELEGAR o atalho a um
funcionário que não é admin.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def usuario_tem_atalho(user, codename):
    return user.is_superuser or user.is_admin_empresa() or user.has_perm(f'compras.{codename}')


def atalho_compras_required(codename):
    """Substitui @permission_required, liberando também para admin da empresa."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not usuario_tem_atalho(request.user, codename):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
