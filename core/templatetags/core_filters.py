import json as _json

from django import template
from django.template.defaultfilters import floatformat
from django.urls import NoReverseMatch, reverse

register = template.Library()


@register.inclusion_tag('partials/breadcrumb.html')
def breadcrumb(*items):
    """Renderiza um breadcrumb padronizado.

    Uso: {% breadcrumb "Dashboard:dashboard:index" "Estoque:estoque:dashboard" "Produtos" %}
    Cada item é "Label:nome_da_url" (vira link) ou só "Label" (item final/ativo, sem link).
    Nomes de URL namespaced ("app:view") funcionam normalmente — só o primeiro ':' separa o rótulo.

    Ícone opcional: prefixe o item com "classe-do-icone|" (ex. "bi-house-door|Dashboard:dashboard:index").
    Só o primeiro '|' separa o ícone do resto — o restante é parseado normalmente.
    """
    parsed = []
    for item in items:
        icon = None
        if '|' in item:
            icon, item = item.split('|', 1)
        if ':' in item:
            label, url_name = item.split(':', 1)
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                url = None
        else:
            label, url = item, None
        parsed.append({'label': label, 'url': url, 'icon': icon})
    return {'items': parsed}


@register.filter
def moeda(value):
    """Formata valor monetário brasileiro: R$ 1.234,56"""
    try:
        formatted = floatformat(value, '2g')
        return f'R$ {formatted}' if formatted not in ('', None) else 'R$ 0,00'
    except (ValueError, TypeError):
        return 'R$ 0,00'


@register.filter
def num_br(value, decimals=2):
    """Formata número com separadores brasileiros: 1.234,567"""
    try:
        return floatformat(value, f'{int(decimals)}g')
    except (ValueError, TypeError):
        return ''


@register.filter
def cce_resumo(value):
    """Formata JSON de correções CC-e em texto legível.

    Entrada: '[{"grupo_corrigido":"compl","campo_corrigido":"xObs","valor_corrigido":"Texto"}]'
    Saída:   'compl.xObs = "Texto"'
    """
    try:
        correcoes = _json.loads(value or '[]')
        if not isinstance(correcoes, list):
            return value
        partes = []
        for c in correcoes:
            grupo = c.get('grupo_corrigido', '')
            campo = c.get('campo_corrigido', '')
            valor = c.get('valor_corrigido', '')
            item  = c.get('numero_item_grupo_corrigido', '')
            chave = f'{grupo}.{campo}' if grupo else campo
            if item:
                chave = f'{chave}[{item}]'
            partes.append(f'{chave} = "{valor}"')
        return ' | '.join(partes) if partes else value
    except Exception:
        return value
