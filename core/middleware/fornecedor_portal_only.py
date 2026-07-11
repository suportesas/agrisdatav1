from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

FORNECEDOR_GROUP = 'FORNECEDOR'
FORNECEDOR_PORTAL_PREFIX = '/portal/fornecedor/'
EXEMPT_URLS = [
    '/admin/',
    '/logout',
    '/accounts/logout',
    '/static/',
    '/media/',
]

class FornecedorPortalOnlyMiddleware:
    """
    Restringe usuários do grupo FORNECEDOR a acessar apenas o portal do fornecedor.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path
        # Só aplica para usuários autenticados
        if user.is_authenticated:
            grupos = user.get_grupos_nomes()
            # Se for apenas FORNECEDOR
            if grupos == [FORNECEDOR_GROUP]:
                # Permite acesso ao portal do fornecedor e URLs isentas
                if not (path.startswith(FORNECEDOR_PORTAL_PREFIX) or any(path.startswith(e) for e in EXEMPT_URLS)):
                    return redirect(reverse('portal_fornecedor:dashboard'))
        return self.get_response(request)
