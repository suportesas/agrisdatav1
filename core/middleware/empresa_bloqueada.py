from django.shortcuts import redirect
from django.contrib import messages
from core.settings import LOGOUT_REDIRECT_URL


class EmpresaBloqueadaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificação para usuários Django normais (inclui motoristas, que agora são Usuario)
        user = request.user
        if user.is_authenticated and hasattr(user, 'empresa') and user.empresa and hasattr(user.empresa, 'is_blocked') and user.empresa.is_blocked():
            LOGOUT_REDIRECT_URL(request)
            messages.error(request, f"A empresa {user.empresa.nome} está bloqueada. Entre em contato com o suporte.")
            return redirect('login')

        return self.get_response(request)
