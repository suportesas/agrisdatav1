from django.shortcuts import redirect
from django.contrib import messages


class RestrictMotoristaMiddleware:
    """
    Restringe usuários do grupo MOTORISTA apenas ao portal do motorista.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if 'MOTORISTA' in request.user.get_grupos_nomes():
                if not (request.path.startswith('/portal/motorista/') or request.path == '/logout/'):
                    messages.warning(request, 'Acesso restrito ao Portal do Motorista.')
                    return redirect('portal_motorista:home')
        return self.get_response(request)
