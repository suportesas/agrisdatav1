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

    # Go to roles list and create a new role via UI
    page.goto(f"{live_server.url}/empresas/roles/")
    page.click('text=Nova Função')
    page.fill('input[name="name"]', 'E2E Role UI')
    page.fill('textarea[name="description"]', 'Criada via E2E')
    page.click('text=Salvar')

    # Wait for role to appear in list and click it
    page.wait_for_selector('text=E2E Role UI')
    page.click('text=E2E Role UI')

    # Wait for permissions section to render
    page.wait_for_selector('text=Permissões')

    # Toggle add checkbox for model 'empresa' (if present)
    try:
        row_selector = "tr[data-model='empresa']"
        page.wait_for_selector(row_selector, { 'timeout': 2000 })
        add_checkbox = page.locator(f"{row_selector} input[name='add']")
        add_checkbox.check()
    except Exception:
        # If the model 'empresa' isn't present (depends on available apps), pick first row
        first_add = page.locator('table tbody tr >> nth=0 input[name="add"]')
        first_add.check()

    # Save
    page.click("text=Salvar")

    # Confirm aria-live / toast message
    page.wait_for_selector('text=Permissões atualizadas')
    # Also confirm status region updated
    assert page.locator('div[role="status"][aria-live="polite"]').inner_text().strip() != ''

    # Verify via API: permissions endpoint should reflect the change
    resp = page.request.get(f"{live_server.url}/empresas/roles/{role.pk}/permissions/")
    data = resp.json()
    # Ensure at least one module has add true
    assert any(item['perms']['add'] for item in data['permissions'])

    # Test export: click 'Exportar' and wait for download
    with page.expect_download() as download_info:
        page.click('text=Exportar')
    download = download_info.value
    path = download.path()
    # Read downloaded file and assert JSON structure
    import json
    with open(path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    assert isinstance(payload, dict)
    # There should be keys representing models and boolean permission fields
    example_values = list(payload.values())[0]
    assert any(k in example_values for k in ['add','change','delete','view'])
    # Additionally ensure role's group in DB has the permission (sync check)
    page.wait_for_timeout(500)
    perm = Permission.objects.filter(codename__startswith='add_').first()
    if perm:
        assert perm in role.get_permissions()
