import time

from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

INACTIVITY_TIMEOUT_SECONDS = 300  # 5 minutos

# Prefixos que não devem contar como atividade nem disparar o logout
# (evita logout no meio de um upload/polling e evita interferir com login/estáticos)
_EXEMPT_PATH_PREFIXES = ('/static/', '/media/', '/login/', '/logout/')


class InactivityLogoutMiddleware:
    """Desloga o usuário após INACTIVITY_TIMEOUT_SECONDS sem requisições."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not request.path.startswith(_EXEMPT_PATH_PREFIXES):
            now = time.time()
            last_activity = request.session.get('last_activity')

            if last_activity is not None and (now - last_activity) > INACTIVITY_TIMEOUT_SECONDS:
                logout(request)
                messages.info(request, "Sua sessão expirou por inatividade. Faça login novamente.")
                return redirect('login')

            request.session['last_activity'] = now

        return self.get_response(request)
