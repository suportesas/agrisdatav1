"""
Middleware que verifica acesso por Programa (tela) — substitui
`core/middleware/role_enforcement.py` (que bloqueava por prefixo de módulo
inteiro, e cobria só 18 dos 27 apps).

Cada URL nomeada do sistema tem um `Programa` correspondente (ver
`empresas/programa_discovery.py`). O acesso é resolvido por
`Role.programas` (ver `empresas/models.py`), não mais por
`auth.Permission`/`user.has_perm()`.

Fail-closed: se a URL atual tem um Programa cadastrado e o usuário não tem
nenhuma Role que o conceda, bloqueia — inclusive se o Programa ainda não foi
sincronizado (não existe registro), também bloqueia (tela nova nasce
bloqueada até um admin liberar).

Bypass automático:
  - Paths públicos/self-gerenciados (login, admin, static, media, API,
    empresas, usuarios, dashboard, portais externos — mesma lista de
    referência usada em `empresas/programa_discovery.py` EXCLUDED_NAMESPACES,
    MANTENHA AS DUAS LISTAS SINCRONIZADAS)
  - Superuser
  - Admin da empresa (is_admin_empresa())

Configuração adicional: 'ROLE_ENFORCEMENT_ENABLED = False' no settings
desativa temporariamente (útil em desenvolvimento) — mesma flag usada pelo
middleware antigo.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings


# Prefixos que NUNCA são bloqueados por este middleware — telas controladas
# pelo próprio app (empresas/usuarios), portais externos com seu próprio
# middleware de acesso, ou infraestrutura pública/pré-autenticação.
# Mantenha sincronizado com EXCLUDED_NAMESPACES em empresas/programa_discovery.py.
PUBLIC_PREFIXES = (
    '/admin/',
    '/login', '/logout',
    '/static/', '/media/',
    '/api/', '/auth/',
    '/password_reset', '/reset/',
    '/cadastros/api/',
    '/__e2e_log__',
    '/empresas/',
    '/dashboard/', '/dashboard-executivo/',
    '/usuarios/',
    '/landing/', '/recursos', '/sobre/', '/planos/', '/faq/', '/contato/',
    '/portal/',
)


class ProgramaEnforcementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ROLE_ENFORCEMENT_ENABLED', True)

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if not self.enabled:
            return None

        path = request.path
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return None

        if not request.user.is_authenticated:
            return None

        if request.user.is_superuser:
            return None
        if hasattr(request.user, 'is_admin_empresa') and request.user.is_admin_empresa():
            return None

        resolver_match = request.resolver_match
        url_name = resolver_match.view_name if resolver_match else None
        if not url_name:
            return None

        from empresas.models import Programa

        programa = Programa.objects.filter(url_name=url_name, ativo=True).first()
        permitidos = self._programas_permitidos(request)

        if programa is not None and url_name in permitidos:
            return None

        # Bloqueado: ou o Programa não existe (URL não sincronizada — fail
        # closed), ou existe mas nenhuma Role do usuário o concede.
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
        )
        if is_ajax:
            return JsonResponse(
                {'error': 'Sem permissão para acessar esta tela.', 'programa': url_name},
                status=403
            )

        nome_tela = programa.nome if programa else 'esta tela'
        messages.error(
            request,
            f'⛔ Você não tem acesso à tela <strong>{nome_tela}</strong>. '
            'Solicite ao administrador que ajuste suas Funções em '
            '<a href="/empresas/roles/">Funções e Permissões</a>.'
        )
        return redirect('dashboard:index')

    @staticmethod
    def _programas_permitidos(request):
        """Set de url_names que o usuário pode acessar, calculado uma vez por request."""
        cache_attr = '_programas_permitidos_cache'
        cached = getattr(request, cache_attr, None)
        if cached is not None:
            return cached

        from empresas.models import Programa

        url_names = set(
            Programa.objects.filter(
                ativo=True, roles__usuarios=request.user
            ).values_list('url_name', flat=True)
        )
        setattr(request, cache_attr, url_names)
        return url_names
