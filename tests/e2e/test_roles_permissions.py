import pytest
from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role

User = get_user_model()


@pytest.fixture
def e2e_roles_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Roles')
        user = User.objects.create_user(username='e2eadmin', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        # Create a role for testing
        role = Role.objects.create(empresa=empresa, name='E2E Role')

        client = Client()
        assert client.login(username='e2eadmin', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'role': role, 'sessionid': sessionid}


def test_permissions_flow_via_ui(page, live_server, e2e_roles_data, django_db_blocker):
    """Marca a primeira permissão disponível e salva, via
    /empresas/roles/<id>/permissions/ (empresas/templates/empresas/
    role_permissions_page.html, JS compartilhado em roles_js.html).

    Estrutura real: cada linha de #perms-tbody tem `data-module` (app_label)
    e um unico checkbox `.perm-cb[data-programa-id]` — nao ha um par
    add/remove por linha (isso e de uma UI antiga).
    """
    sessionid = e2e_roles_data['sessionid']
    role = e2e_roles_data['role']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{'name': 'sessionid', 'value': sessionid, 'domain': host, 'path': '/'}])

    page.goto(f"{live_server.url}/empresas/roles/{role.pk}/permissions/")
    page.wait_for_selector('#perms-tbody tr[data-module]', timeout=10000)

    checkbox = page.locator('#perms-tbody .perm-cb').first
    programa_id = checkbox.get_attribute('data-programa-id')
    assert not checkbox.is_checked()
    checkbox.check()

    assert page.locator('#btn-save-perms-bottom').is_enabled()
    page.click('#btn-save-perms-bottom')
    page.wait_for_selector('text=salva', timeout=5000)

    with django_db_blocker.unblock():
        role.refresh_from_db()
        assert role.programas.filter(pk=programa_id).exists()
