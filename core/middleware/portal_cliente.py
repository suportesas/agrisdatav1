from django.shortcuts import redirect

PORTAL_CLIENTE_PREFIX = '/portal/cliente/'
EXEMPT_PATHS = ['/admin/', '/logout', '/static/', '/media/', '/portal/cliente/login/']


def _get_cliente_vinculado(user):
    """Retorna o Cliente vinculado ao usuário, ou None."""
    try:
        return user.cliente_vinculado.filter(acesso_portal=True).first()
    except Exception:
        return None


class PortalClienteMiddleware:
    """
    - Usuários com Cliente vinculado (acesso_portal=True) só podem acessar /portal/cliente/.
    - Acesso ao /portal/cliente/ requer usuário com Cliente vinculado.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path

        if not user.is_authenticated:
            return self.get_response(request)

        # Superusuários e staff não são restritos
        if user.is_superuser or user.is_staff:
            return self.get_response(request)

        cliente = _get_cliente_vinculado(user)

        if cliente:
            # Usuário de portal: só pode acessar o portal do cliente ou URLs isentas
            if not (path.startswith(PORTAL_CLIENTE_PREFIX) or any(path.startswith(e) for e in EXEMPT_PATHS)):
                return redirect(PORTAL_CLIENTE_PREFIX)

        return self.get_response(request)
