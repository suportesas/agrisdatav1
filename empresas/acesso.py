"""
Resolução de quais Programas (telas) o usuário atual pode acessar.

Usado tanto pelo middleware de enforcement (`core/middleware/programa_enforcement.py`)
quanto pela tag de template do sidebar (`empresas/templatetags/permissoes_tags.py`),
para garantir que os dois lugares sempre concordem sobre o que é permitido —
o mesmo set de url_names é calculado uma única vez por request e cacheado.

## Endpoints AJAX internos (dropdowns em cascata, preview, autocomplete)

O projeto tem uma convenção de nomenclatura consistente pra esses helpers,
usada aqui pra evitar exigir permissão explícita de coisas que não são
"telas" de verdade:

- `<algo>_ajax` (sufixo): variante AJAX de uma ação que já existe sem esse
  sufixo (ex.: `cliente_contato_create` e `cliente_contato_create_ajax`).
  Tratada como um alias: se o usuário tem a ação "gêmea" concedida, a
  variante ajax também é liberada — evita duplicar checkbox pra mesma ação.
- `ajax_<algo>` (prefixo): helper isolado sem gêmeo (ex.: `ajax_areas_fazenda`,
  usado só pra popular um <select> dentro de outra tela já protegida). Não
  exige Programa concedido — a não ser que esteja em `AJAX_HELPERS_ESCRITA`
  (helpers que realmente gravam dado, identificados manualmente, e que
  continuam exigindo concessão normal).

## Herança Listagem → Detalhe/Excluir

`Detalhe` e `Excluir` não são geridos na tela de Funções e Permissões —
só a `Listagem` aparece lá (junto com Criar/Editar). Por padrão, quem tem
acesso à Listagem de uma tela também acessa o Detalhe e o Excluir dela
(`_herda_de_listagem`). Isso só vale enquanto NINGUÉM tiver recebido esse
Programa de Detalhe/Excluir explicitamente — a partir do momento em que um
admin configura isso pela tela do Programa (`empresas/views_programa.py`)
pra qualquer Função, o "passe livre" acaba pra todo mundo e vira concessão
normal (mesma regra do MadBuilder: "ao definir as ações, elas se tornam
obrigatórias").
"""

# Helpers no padrão `ajax_<algo>` que GRAVAM dado (ao contrário da maioria,
# que só lê/lista) — não entram no bypass automático, continuam exigindo
# concessão explícita como qualquer Programa comum.
AJAX_HELPERS_ESCRITA = {
    'embalagem:ajax_adicionar_pallet',
    'mip:ajax_adicionar_estagio',
    'mip:ajax_deletar_estagio',
}


def eh_ajax_helper_leitura(url_name):
    """True se for um helper AJAX isolado (padrão `ajax_<algo>`) e não estiver
    na lista de exceções que gravam dado."""
    if url_name in AJAX_HELPERS_ESCRITA:
        return False
    bare = url_name.rsplit(':', 1)[-1]
    return bare.startswith('ajax_') and not bare.endswith('_ajax')


def gemeo_de_ajax(url_name):
    """Se url_name for uma variante `<algo>_ajax`, retorna o url_name da ação
    'gêmea' sem o sufixo (ex.: 'cadastros:cliente_contato_create_ajax' ->
    'cadastros:cliente_contato_create'). Senão, retorna None."""
    namespace, _, bare = url_name.rpartition(':')
    if not bare.endswith('_ajax'):
        return None
    gemeo_bare = bare[:-len('_ajax')]
    return f'{namespace}:{gemeo_bare}' if namespace else gemeo_bare


def _herda_de_listagem(url_name, permitidos):
    """True se url_name for um Programa de Detalhe/Excluir cujo acesso ainda
    não foi configurado explicitamente pra nenhuma Função — nesse caso ele é
    liberado de graça pra quem tem a Listagem da mesma tela. Ver docstring
    do módulo ("Herança Listagem → Detalhe/Excluir")."""
    from .models import Programa

    programa = Programa.objects.filter(url_name=url_name, ativo=True).first()
    if not programa or programa.tipo_acao not in ('detalhe', 'excluir'):
        return False
    if programa.roles.exists():
        return False  # já configurado explicitamente por alguma Função — passe livre encerrado

    listagem = Programa.objects.filter(
        app_label=programa.app_label, grupo_tela=programa.grupo_tela,
        tipo_acao='listagem', ativo=True,
    ).first()
    return listagem is not None and listagem.url_name in permitidos


def usuario_tem_acesso(request, *url_names):
    """True se o usuário autenticado pode acessar QUALQUER uma das telas informadas."""
    user = request.user
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'is_admin_empresa') and user.is_admin_empresa():
        return True

    permitidos = programas_permitidos(request)
    for nome in url_names:
        if nome in permitidos:
            return True
        if eh_ajax_helper_leitura(nome):
            return True
        gemeo = gemeo_de_ajax(nome)
        if gemeo and gemeo in permitidos:
            return True
        if _herda_de_listagem(nome, permitidos):
            return True
    return False


def programa_required(*url_names, redirect_url='dashboard:index'):
    """Decorator de view que exige acesso a QUALQUER um dos Programas informados.

    Substitui decorators antigos baseados em `user.has_perm()`/Django Permission,
    que não são mais atualizados pela nova tela de Funções e Permissões
    (ver `Role.set_programas`).
    """
    import functools

    from django.conf import settings
    from django.contrib import messages
    from django.http import JsonResponse
    from django.shortcuts import redirect

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(getattr(settings, 'LOGIN_URL', 'login'))

            if usuario_tem_acesso(request, *url_names):
                return view_func(request, *args, **kwargs)

            is_ajax = (
                request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('Accept', '')
            )
            if is_ajax:
                return JsonResponse({'error': 'Permissão negada.'}, status=403)

            messages.error(request, '⛔ Você não tem permissão para acessar esta área.')
            return redirect(redirect_url)

        return wrapper
    return decorator


def programas_permitidos(request):
    """Set de url_names de Programa que o usuário do request pode acessar (cacheado por request)."""
    cache_attr = '_programas_permitidos_cache'
    cached = getattr(request, cache_attr, None)
    if cached is not None:
        return cached

    from .models import Programa

    url_names = set(
        Programa.objects.filter(
            ativo=True, roles__usuarios=request.user
        ).values_list('url_name', flat=True)
    )
    setattr(request, cache_attr, url_names)
    return url_names


def roles_visiveis_para_empresa(empresa):
    """Funções (Role) visíveis pra uma empresa: as próprias dela + Funções
    Globais que ela ainda não personalizou (ver Role.origem_global).

    Fonte única usada tanto pela tela de Funções e Permissões
    (`empresas/views.py::role_list`) quanto pelo campo `roles` do cadastro
    de usuário (`usuarios/forms.py`) — pra uma Função Global nunca aparecer
    numa tela e sumir na outra."""
    from .models import Role

    if not empresa:
        return Role.objects.none()

    roles_proprias = Role.objects.filter(empresa=empresa)
    ja_personalizadas = roles_proprias.filter(
        origem_global__isnull=False
    ).values_list('origem_global_id', flat=True)
    globais_disponiveis = Role.objects.filter(empresa__isnull=True).exclude(id__in=ja_personalizadas)
    return roles_proprias | globais_disponiveis
