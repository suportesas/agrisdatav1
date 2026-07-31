"""
Helper de paginacao configuravel pelo usuario.

Centraliza a leitura/validacao do parametro "per_page" da querystring,
reproduzindo o padrao original de produtos.views.produto_list.
"""

from django.core.paginator import Paginator

PER_PAGE_OPTIONS = (10, 25, 50, 100)
PER_PAGE_DEFAULT = 25


def resolve_per_page(request, options=PER_PAGE_OPTIONS, default=PER_PAGE_DEFAULT):
    """Le e valida 'per_page' da querystring contra a whitelist (com fallback).

    Util quando a view nao pode usar paginate() diretamente (ex: paginacao
    manual/agrupada), mas ainda quer respeitar a escolha do usuario.
    """
    try:
        per_page = int(request.GET.get('per_page', default))
    except (TypeError, ValueError):
        per_page = default
    if per_page not in options:
        per_page = default
    return per_page


def paginate(request, queryset, options=PER_PAGE_OPTIONS, default=PER_PAGE_DEFAULT, page_param='page'):
    """Pagina queryset lendo 'per_page' da querystring (whitelist + fallback).

    Retorna (page_obj, per_page, per_page_options) — os dois ultimos vao
    direto no contexto do template junto com o partial per_page_select.html.
    """
    per_page = resolve_per_page(request, options, default)
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(request.GET.get(page_param))
    return page_obj, per_page, list(options)
