"""
Tag/filtro de template para checar acesso a Programas (telas) no sidebar,
usando a mesma lógica de resolução do middleware de enforcement
(ver empresas/acesso.py).
"""

from django import template

from empresas.acesso import usuario_tem_acesso

register = template.Library()


@register.filter
def tem_acesso(request, url_names):
    """Uso: {% if user.is_admin_empresa or request|tem_acesso:'app:url_name,app:outro_url_name' %}

    Retorna True se o usuário puder acessar QUALQUER um dos url_names
    (separados por vírgula) informados.
    """
    if request is None:
        return False
    nomes = [n.strip() for n in url_names.split(',') if n.strip()]
    if not nomes:
        return False
    return usuario_tem_acesso(request, *nomes)
