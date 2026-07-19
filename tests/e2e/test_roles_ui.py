import pytest
from urllib.parse import urlparse
from empresas.models import Role, Empresa


def test_role_selection_highlight_and_hide(page, live_server, e2e_roles_data, django_db_blocker):
    """Clicar numa função na lista deve destaca-la (.active) e carregar o
    painel de permissões correspondente.

    O comportamento de "esconder as demais" (#toggle-hide / .role-card) que
    esse teste cobria não existe em empresas/templates/empresas/roles_list.html
    — a lista atual usa .role-item/.active e não tem esse botão. Reescrito
    para cobrir o que a tela realmente faz.
    """
    with django_db_blocker.unblock():
        empresa = e2e_roles_data['empresa']
        Role.objects.create(empresa=empresa, name='E2E Role 2')

    sessionid = e2e_roles_data['sessionid']
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{'name': 'sessionid', 'value': sessionid, 'domain': host, 'path': '/'}])

    page.goto(f"{live_server.url}/empresas/roles/")
    page.wait_for_selector('.role-item', timeout=5000)

    items = page.locator('.role-item')
    assert items.count() >= 2

    # Clica no primeiro item
    items.nth(0).click()
    assert page.evaluate("() => document.querySelectorAll('.role-item.active').length") == 1
    page.wait_for_selector('#perms-content:not(.d-none)', timeout=5000)

    # Clica no segundo item: seleção deve mover, não acumular
    items.nth(1).click()
    assert page.evaluate("() => document.querySelectorAll('.role-item.active').length") == 1
    active_id = page.evaluate("() => document.querySelector('.role-item.active').dataset.roleId")
    second_id = page.evaluate("() => document.querySelectorAll('.role-item')[1].dataset.roleId")
    assert active_id == second_id
