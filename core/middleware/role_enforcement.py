"""
Middleware que verifica permissões de módulo baseadas em Roles.

Para cada URL prefix protegido, exige que o usuário tenha a permissão 'view_*'
do modelo principal daquele módulo. Isso bloqueia o acesso ao módulo inteiro
para usuários sem a Role adequada.

Bypass automático:
  - Paths públicos (login, admin, static, media, API)
  - Superuser
  - Admin da empresa (is_admin_empresa())
  - Usuário com a permissão Django correspondente

Configuração adicional: adicione 'ROLE_ENFORCEMENT_ENABLED = False' no settings
para desativar temporariamente (útil em desenvolvimento).
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings


# Mapeamento de prefixo de URL → permissão Django necessária para ACESSAR o módulo.
# A permissão 'view_X' garante que o usuário pode ao menos LISTAR/VER o módulo.
# Ações mais específicas (add/change/delete) são verificadas individualmente nas views
# ou pelo decorator @perm_required.
MODULE_PERMISSIONS = {
    '/compras/':       'compras.view_pedidocompra',
    '/financeiro/':    'financeiro.view_contapagar',
    '/plano-contas/':  'plano_contas.view_contacontabil',
    '/bancario/':      'bancario.view_contabancaria',
    '/adiantamentos/': 'adiantamentos.view_adiantamentointernacional',
    '/faturamento/':   'faturamento.view_notafiscal',
    '/vendas/':        'vendas.view_pedidovenda',
    '/exportacao/':    'exportacao.view_booking',
    '/embalagem/':     'embalagem.view_ordemembalagem',
    '/estoque/':       'estoque.view_movimentacaoestoque',
    '/patrimonio/':    'patrimonio.view_patrimonio',
    '/frota/':         'frota.view_vehicle',
    '/mip/':           'mip.view_monitoramentomip',
    '/emprestimos/':   'emprestimos.view_emprestimoprodutor',
    '/estufas/':       'estufas.view_estufa',
    '/rh/':            'rh.view_funcionario',
    '/campo/':         'operacoes_campo.view_ordemservico',
    '/energia/':       'energia.view_usinafotovoltaica',
}

# Prefixos que NUNCA são bloqueados (independente de permissões)
PUBLIC_PREFIXES = (
    '/admin/',
    '/login',
    '/logout',
    '/static/',
    '/media/',
    '/api/',
    '/auth/',
    '/password_reset',
    '/reset/',
    '/cadastros/api/',      # endpoints AJAX internos
    '/__e2e_log__',
    '/empresas/',           # gerenciamento de empresa/roles — controlado pelo próprio app
    '/dashboard/',
    '/dashboard-executivo/',
    '/usuarios/',           # cadastro de usuários — controlado pelo próprio app
    '/landing/',
    '/recursos',
    '/sobre/',
    '/planos/',
    '/faq/',
    '/contato/',
    '/portal/',
)


class RoleEnforcementMiddleware:
    """
    Verifica permissões de módulo baseadas em Roles antes de processar a view.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'ROLE_ENFORCEMENT_ENABLED', True)

    def __call__(self, request):
        if self.enabled:
            response = self._check_permission(request)
            if response is not None:
                return response
        return self.get_response(request)

    def _check_permission(self, request):
        path = request.path

        # Ignora paths públicos
        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return None

        # Ignora usuários não autenticados (deixa para @login_required tratar)
        if not request.user.is_authenticated:
            return None

        # Superuser e admin empresa passam direto
        if request.user.is_superuser:
            return None
        if hasattr(request.user, 'is_admin_empresa') and request.user.is_admin_empresa():
            return None

        # Verifica se o path cai em algum módulo protegido
        required_perm = None
        for prefix, perm in MODULE_PERMISSIONS.items():
            if path.startswith(prefix):
                required_perm = perm
                break

        if required_perm is None:
            return None  # Módulo não mapeado — sem restrição

        if request.user.has_perm(required_perm):
            return None  # Permissão concedida

        # Acesso negado
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
        )
        if is_ajax:
            return JsonResponse(
                {'error': 'Sem permissão para acessar este módulo.', 'perm': required_perm},
                status=403
            )

        # Descobre o nome do módulo para a mensagem
        module_name = self._get_module_name(path)
        messages.error(
            request,
            f'⛔ Você não tem acesso ao módulo <strong>{module_name}</strong>. '
            'Solicite ao administrador que ajuste suas Funções em '
            '<a href="/empresas/roles/">Funções e Permissões</a>.'
        )
        return redirect('dashboard:index')

    @staticmethod
    def _get_module_name(path: str) -> str:
        names = {
            '/compras/': 'Compras', '/financeiro/': 'Financeiro',
            '/plano-contas/': 'Plano de Contas', '/bancario/': 'Bancário',
            '/adiantamentos/': 'Adiantamentos', '/faturamento/': 'Faturamento',
            '/vendas/': 'Vendas', '/exportacao/': 'Exportação',
            '/embalagem/': 'Embalagem', '/estoque/': 'Estoque',
            '/patrimonio/': 'Patrimônio', '/frota/': 'Frota',
            '/mip/': 'MIP', '/emprestimos/': 'Empréstimos',
            '/estufas/': 'Estufas', '/rh/': 'RH',
            '/campo/': 'Operações de Campo', '/energia/': 'Energia',
        }
        for prefix, name in names.items():
            if path.startswith(prefix):
                return name
        return 'este módulo'
