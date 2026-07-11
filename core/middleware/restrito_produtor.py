from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.contrib import messages

class RestrictProdutorMiddleware:
    """
    Restringe usuários do grupo PRODUTOR apenas ao portal do produtor.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Só processa se o usuário estiver autenticado
        if request.user.is_authenticated:
            # Se for do grupo PRODUTOR
            if 'PRODUTOR' in request.user.get_grupos_nomes():
                # Permitir URLs do portal do produtor e /logout/
                if not (request.path.startswith('/portal/produtor/') or request.path == '/logout/'):
                    messages.warning(request, 'Acesso restrito ao Portal do Produtor.')
                    return redirect('portal_produtor:dashboard')
        return self.get_response(request)
