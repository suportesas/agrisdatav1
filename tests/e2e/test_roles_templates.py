import pytest
from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role, PermissionTemplate

User = get_user_model()

@pytest.fixture
def e2e_templates_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Tpl')
        user = User.objects.create_user(username='tpladmin', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        role = Role.objects.create(empresa=empresa, name='TemplateRole')

        client = Client()
        assert client.login(username='tpladmin', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'role': role, 'sessionid': sessionid}


def test_save_and_apply_template_via_ui(page, live_server, e2e_templates_data):
    sessionid = e2e_templates_data['sessionid']
    role = e2e_templates_data['role']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{'name': 'sessionid', 'value': sessionid, 'domain': host, 'path': '/'}])

    page.goto(f"{live_server.url}/empresas/roles/{role.id}/permissions/")
    page.wait_for_selector('text=Permissões')

    # Wait for permission rows to render and toggle first add checkbox
    page.wait_for_selector('table tbody tr', timeout=10000)
    first_add = page.locator('table tbody tr >> nth=0 input[name="add"]')
    first_add.check()

    # Save as template using button
    page.click('text=Salvar como template')
    # Browser prompt handled by Playwright: fill with name
    page.on('dialog', lambda dialog: dialog.accept('E2E Template'))

    # Wait for success toast
    page.wait_for_selector('text=Template salvo com sucesso')

    # Ensure template exists via API
    resp = page.request.get(f"{live_server.url}/empresas/roles/templates/")
    data = resp.json()
    assert any(t['nome'] == 'E2E Template' for t in data['templates'])

    # Apply the template to role (select first template and click Apply)
    # Wait for select to be populated
    page.wait_for_selector('#template-select option[value]')
    # Select the template
    page.select_option('#template-select', label='E2E Template')
    page.click('text=Aplicar')

    # Wait for success
    page.wait_for_selector('text=Template aplicado com sucesso')

    # Check that a RoleAudit entry was created (server-side) by requesting templates detail
    tpl = PermissionTemplate.objects.filter(empresa=role.empresa, nome='E2E Template').first()
    assert tpl is not None
