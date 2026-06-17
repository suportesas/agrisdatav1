from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


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
