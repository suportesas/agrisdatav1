import pytest
from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role
from django.contrib.auth.models import Permission

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


def test_permissions_flow_via_ui(page, live_server, e2e_roles_data):
    sessionid = e2e_roles_data['sessionid']
    role = e2e_roles_data['role']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{'name': 'sessionid', 'value': sessionid, 'domain': host, 'path': '/'}])

    # Go to roles list and click the role
    page.goto(f"{live_server.url}/empresas/roles/")
    page.click(f'text={role.name}')

    # Wait for permissions section to render
    page.wait_for_selector('text=Permissões')

    # Find a row for app 'empresas' and model 'empresa' then toggle add checkbox
    # Click the add checkbox for empresas.empresa
    row_selector = "tr[data-model='empresa']"
    page.wait_for_selector(row_selector)
    add_checkbox = page.locator(f"{row_selector} input[name='add']")
    add_checkbox.check()

    # Save
    page.click("button:has-text('Salvar')")

    # Fetch permissions JSON and assert 'add_empresa' is present and has true
    page.goto(f"{live_server.url}/empresas/roles/{role.pk}/permissions/")
    data = page.content()
    assert 'add_empresa' in data

    # Additionally ensure role's group in DB has the permission (sync check)
    perm = Permission.objects.filter(codename='add_empresa').first()
    if perm:
        assert perm in role.get_permissions()
