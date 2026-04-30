from django.shortcuts import redirect
from django.contrib import messages
from core.settings import LOGOUT_REDIRECT_URL

PORTAL_MOTORISTA_PREFIX = '/portal/motorista/'
PORTAL_MOTORISTA_LOGIN  = '/portal/motorista/login/'
PORTAL_MOTORISTA_LOGOUT = '/portal/motorista/logout/'

class EmpresaBloqueadaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificação para usuários Django normais
        user = request.user
        if user.is_authenticated and hasattr(user, 'empresa') and user.empresa and hasattr(user.empresa, 'is_blocked') and user.empresa.is_blocked():
            LOGOUT_REDIRECT_URL(request)
            messages.error(request, f"A empresa {user.empresa.nome} está bloqueada. Entre em contato com o suporte.")
            return redirect('login')

        # Verificação para motoristas autenticados via session (portal independente)
        motorista_id = request.session.get('motorista_id')
        if motorista_id and request.path.startswith(PORTAL_MOTORISTA_PREFIX):
            # Permite logout mesmo com empresa bloqueada
            if request.path == PORTAL_MOTORISTA_LOGOUT:
                return self.get_response(request)
            try:
                from cadastros.models import Motorista
                motorista = Motorista.objects.select_related('empresa').get(pk=motorista_id, ativo=True)
                empresa = motorista.empresa
                if empresa and hasattr(empresa, 'is_blocked') and empresa.is_blocked():
                    request.session.flush()
                    messages.error(request, f"O acesso ao portal está temporariamente suspenso. Entre em contato com o suporte.")
                    return redirect(PORTAL_MOTORISTA_LOGIN)
            except Exception:
                # Se não conseguir verificar, encerra a session por segurança
                request.session.flush()
                return redirect(PORTAL_MOTORISTA_LOGIN)

        return self.get_response(request)
