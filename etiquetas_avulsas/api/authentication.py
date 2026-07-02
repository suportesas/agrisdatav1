import hashlib

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from empresas.models import APIKey


class AnonymousAPIUser:
    """Usuário leve para chamadas autenticadas por API Key (sem Usuario Django).
    Expõe `.empresa` e `is_authenticated=True` para reaproveitar o acessor
    `request.user.empresa` usado no resto do sistema."""

    is_authenticated = True

    def __init__(self, empresa):
        self.empresa = empresa


class APIKeyAuthentication(BaseAuthentication):
    """Autentica chamadas externas via header `X-API-Key`."""

    def authenticate_header(self, request):
        # Necessário para o DRF responder 401 (e não 403) quando a chave falta/é inválida.
        return 'API-Key'

    def authenticate(self, request):
        raw_key = request.META.get('HTTP_X_API_KEY')
        if not raw_key:
            return None

        chave_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        try:
            api_key = APIKey.objects.select_related('empresa').get(chave_hash=chave_hash, ativo=True)
        except APIKey.DoesNotExist:
            raise AuthenticationFailed('API Key inválida ou inativa.')

        api_key.registrar_uso()
        return (AnonymousAPIUser(api_key.empresa), api_key)
