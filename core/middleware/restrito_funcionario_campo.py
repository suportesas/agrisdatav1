from django.shortcuts import redirect
from django.contrib import messages


class RestrictFuncionarioCampoMiddleware:
    """
    Restringe usuários do grupo FUNC_CAMPO apenas ao portal do campo.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if 'FUNC_CAMPO' in request.user.get_grupos_nomes():
                if not (request.path.startswith('/portal/campo/') or request.path == '/logout/'):
                    messages.warning(request, 'Acesso restrito ao Portal do Campo.')
                    return redirect('portal_campo:home')
        return self.get_response(request)
