"""
Descoberta automática de Programas (telas) via introspecção das URLs do Django.

Percorre `django.urls.get_resolver()` e cria/atualiza um `Programa` para cada
URL nomeada do sistema, inferindo app, tipo de ação (abrir/criar/editar/
excluir) e um nome amigável a partir do padrão de nomenclatura usado no
projeto (`<entidade>_list`, `<entidade>_create`, etc.).

Uso: `sincronizar_programas()`, chamado pelo comando de management
`sync_programas` e automaticamente após todo `migrate` (ver `empresas/apps.py`).
"""

from django.apps import apps as django_apps
from django.urls import URLPattern, URLResolver, get_resolver

from .acesso import eh_ajax_helper_leitura
from .models import Programa

# Namespaces inteiros que ficam fora do controle de acesso por Programa —
# mesma lista de referência de `core/middleware/role_enforcement.py`
# (PUBLIC_PREFIXES): telas controladas pelo próprio app, ou portais externos
# que já têm seu próprio middleware de acesso.
EXCLUDED_NAMESPACES = {
    'admin', 'supabase_auth', 'rest_framework',
    'empresas', 'usuarios', 'dashboard', 'metricas',
    'portal_fornecedor', 'portal_produtor', 'portal_motorista', 'portal_cliente',
}

# URLs sem namespace (declaradas direto em core/urls.py) que são sempre
# públicas/pré-autenticação ou utilitárias — nunca viram Programa.
EXCLUDED_URL_NAMES = {
    'login', 'logout', 'root_redirect', 'page_not_found',
    'password_reset', 'password_reset_done',
    'password_reset_confirm', 'password_reset_complete',
    'landing_page', 'recursos_page', 'sobre_page', 'planos_page',
    'faq_page', 'contato_page', 'recursos_avancados_page',
    'session_heartbeat',
}

# Sufixos de nome de URL → tipo de ação. Ordem importa (mais específico primeiro).
_SUFIXOS_TIPO_ACAO = [
    ('_list', 'listagem'), ('_dashboard', 'listagem'),
    ('_detail', 'detalhe'), ('_view', 'detalhe'),
    ('_create', 'criar'), ('_novo', 'criar'), ('_nova', 'criar'), ('_add', 'criar'),
    ('_update', 'editar'), ('_edit', 'editar'), ('_editar', 'editar'),
    ('_delete', 'excluir'), ('_excluir', 'excluir'), ('_remove', 'excluir'),
]


def _walk(patterns, namespace_prefix, path_prefix, out):
    for entry in patterns:
        if isinstance(entry, URLPattern):
            if not entry.name:
                continue
            full_name = f"{namespace_prefix}{entry.name}" if namespace_prefix else entry.name
            full_path = f"{path_prefix}{entry.pattern}"
            out.append((full_name, full_path, entry.callback))
        elif isinstance(entry, URLResolver):
            ns = entry.namespace
            novo_prefixo_ns = f"{namespace_prefix}{ns}:" if ns else namespace_prefix
            novo_prefixo_path = f"{path_prefix}{entry.pattern}"
            _walk(entry.url_patterns, novo_prefixo_ns, novo_prefixo_path, out)


def _deve_ignorar(full_name, full_path):
    if not full_name:
        return True
    namespace = full_name.split(':')[0] if ':' in full_name else ''
    bare_name = full_name.rsplit(':', 1)[-1]

    if namespace in EXCLUDED_NAMESPACES:
        return True
    if not namespace and bare_name in EXCLUDED_URL_NAMES:
        return True
    if '/api/' in full_path or full_path.startswith('api/'):
        return True
    if eh_ajax_helper_leitura(full_name):
        return True
    return False


def _derive_tipo_acao(bare_name):
    # Telas de dashboard nomeadas apenas "dashboard" ou "dashboard_<algo>"
    # (ex.: financeiro:dashboard, estufas:dashboard_estufas) não têm o sufixo
    # "_dashboard" e cairiam em 'outro' — tratadas como 'listagem' para que
    # apareçam como candidatas a Página inicial (ver usuarios/forms.py,
    # empresas/forms.py) igual às demais telas de listagem/visão geral.
    if bare_name == 'dashboard' or bare_name.startswith('dashboard_'):
        return 'listagem', bare_name
    for sufixo, tipo in _SUFIXOS_TIPO_ACAO:
        if bare_name.endswith(sufixo):
            resto = bare_name[:-len(sufixo)]
            return tipo, resto or bare_name
    return 'outro', bare_name


def _infer_app_label(namespace, callback):
    if namespace:
        return namespace.split(':')[0]
    module = getattr(callback, '__module__', '') or ''
    top = module.split('.')[0]
    if top and django_apps.is_installed(top):
        return top
    return 'root'


def _nome_amigavel(app_label, grupo_tela):
    try:
        app_config = django_apps.get_app_config(app_label)
    except LookupError:
        app_config = None

    if app_config:
        alvo = grupo_tela.replace('_', '')
        for model in app_config.get_models():
            if model._meta.model_name == alvo:
                return str(model._meta.verbose_name_plural).capitalize()

    return grupo_tela.replace('_', ' ').strip().capitalize() or grupo_tela


def sincronizar_programas():
    """Varre todas as URLs nomeadas do sistema e sincroniza a tabela Programa.

    Retorna um dict com contagem de {'criados', 'atualizados', 'desativados'}.
    """
    resolver = get_resolver()
    coletados = []
    _walk(resolver.url_patterns, '', '', coletados)

    vistos = set()
    stats = {'criados': 0, 'atualizados': 0, 'desativados': 0}

    for full_name, full_path, callback in coletados:
        if _deve_ignorar(full_name, full_path):
            continue

        namespace = full_name.rsplit(':', 1)[0] if ':' in full_name else ''
        bare_name = full_name.rsplit(':', 1)[-1]
        app_label = _infer_app_label(namespace, callback)
        tipo_acao, grupo_tela = _derive_tipo_acao(bare_name)

        vistos.add(full_name)

        programa = Programa.objects.filter(url_name=full_name).first()
        if programa:
            programa.app_label = app_label
            programa.grupo_tela = grupo_tela
            programa.tipo_acao = tipo_acao
            programa.ativo = True
            if not programa.nome_customizado:
                programa.nome = _nome_amigavel(app_label, grupo_tela)
            programa.save()
            stats['atualizados'] += 1
        else:
            Programa.objects.create(
                url_name=full_name,
                app_label=app_label,
                grupo_tela=grupo_tela,
                tipo_acao=tipo_acao,
                nome=_nome_amigavel(app_label, grupo_tela),
                ativo=True,
            )
            stats['criados'] += 1

    # Nunca desativa Programas cadastrados manualmente (descoberta_automatica=False) —
    # eles não têm URL própria para a varredura encontrar (ver Programa.descoberta_automatica).
    desativados_qs = Programa.objects.filter(ativo=True, descoberta_automatica=True).exclude(url_name__in=vistos)
    stats['desativados'] = desativados_qs.count()
    desativados_qs.update(ativo=False)

    return stats
