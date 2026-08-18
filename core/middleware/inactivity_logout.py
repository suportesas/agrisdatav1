import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

# Prefixos que não devem contar como atividade nem disparar o logout
# (evita logout no meio de um upload/polling e evita interferir com login/estáticos)
_EXEMPT_PATH_PREFIXES = ('/static/', '/media/', '/login/', '/logout/')

# Não faz sentido usar como next a própria chamada do heartbeat.
_NON_REDIRECTABLE_PATHS = ('/session-heartbeat/',)


class InactivityLogoutMiddleware:
    """Desloga o usuário após settings.SESSION_INACTIVITY_TIMEOUT sem requisições.

    O front-end (static/js/session-heartbeat.js) envia uma requisição periódica
    enquanto detecta interação real do usuário (mouse/teclado/scroll/toque) com a
    aba visível, o que conta como requisição normal aqui e renova o prazo. Sem
    interação real (ou com a aba em segundo plano), o heartbeat para e o timeout
    passa a valer de verdade.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not request.path.startswith(_EXEMPT_PATH_PREFIXES):
            now = time.time()
            last_activity = request.session.get('last_activity')

            if last_activity is not None and (now - last_activity) > settings.SESSION_INACTIVITY_TIMEOUT:
                next_url = request.get_full_path()
                logout(request)
                messages.info(request, "Sua sessão expirou por inatividade. Faça login novamente.")
                login_url = reverse('login')
                if next_url and not next_url.startswith(_NON_REDIRECTABLE_PATHS):
                    login_url = '%s?%s' % (login_url, urlencode({'next': next_url}))
                return redirect(login_url)

            request.session['last_activity'] = now

        return self.get_response(request)
