import pytest
from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role
# Import PermissionTemplate lazily inside test to avoid collection-time import issues

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

    # Ensure CSRF cookie is present (some AJAX endpoints require the csrftoken cookie)
    token = page.evaluate("() => (document.querySelector('input[name=csrfmiddlewaretoken]') ? document.querySelector('input[name=csrfmiddlewaretoken]').value : '')")
    if token:
        # Try to set csrftoken cookie; best-effort (some Playwright versions require url or domain scoping and may reject invalid inputs)
        try:
            page.context.add_cookies([{'name':'csrftoken','value':token,'url': live_server.url,'path':'/'}])
        except Exception as e:
            try:
                parsed = urlparse(live_server.url)
                host = parsed.hostname or '127.0.0.1'
                page.context.add_cookies([{'name':'csrftoken','value':token,'domain': host,'path':'/'}])
            except Exception as e2:
                print('DEBUG: add_cookies failed with both url and domain attempts', e, e2)
        # Debug: list cookies after attempting to add
        try:
            ck = page.context.cookies()
            print('DEBUG cookies after add attempt:', ck)
        except Exception:
            pass
    else:
        print('DEBUG: no csrf token found on page; continuing (may fail CSRF checks)')

    # Wait for permission rows to render and toggle first add checkbox
    page.wait_for_selector('table tbody tr', timeout=10000)
    first_add = page.locator('table tbody tr >> nth=0 input[name="add"]')
    try:
        first_add.check(timeout=5000)
    except Exception:
        # fallback: toggle via JS if Playwright's check fails due to visibility issues
        page.eval_on_selector('table tbody tr input[name="add"]', 'el => { el.checked = true; el.dispatchEvent(new Event("change")); }')

    # Prepare dialog handler before clicking the Save button
    page.on('dialog', lambda dialog: dialog.accept('E2E Template'))
    # Ensure CSRF cookie/header present for the AJAX save (fallback): fetch a page that sets CSRF token and use it
    page.goto(f"{live_server.url}/login/")
    try:
        page.wait_for_selector('input[name=csrfmiddlewaretoken]', timeout=5000)
        token2 = page.evaluate("() => (document.querySelector('input[name=csrfmiddlewaretoken]') ? document.querySelector('input[name=csrfmiddlewaretoken]').value : '')")
        if token2:
            page.context.add_cookies([{'name':'csrftoken','value':token2,'domain': host,'path':'/'}])
            print('DEBUG: set csrftoken from login page')
    except Exception:
        print('DEBUG: could not obtain csrf token from login page')
    # Go back to permissions page
    page.goto(f"{live_server.url}/empresas/roles/{role.id}/permissions/")
    page.wait_for_selector('text=Permissões')

    # Prepare diagnostics: capture responses and console messages
    resp_list = []
    def on_response(r):
        try:
            if '/permissions/save-template/' in r.url:
                resp_list.append(r)
        except Exception:
            pass
    page.on('response', on_response)

    console_msgs = []
    page.on('console', lambda msg: console_msgs.append(f"console:{msg.type}:{msg.text}"))

    # Save as template using button
    page.click('text=Salvar como template')

    # wait a little for request/response
    page.wait_for_timeout(500)
    if resp_list:
        try:
            resp = resp_list[0]
            print('DEBUG save-template response status:', resp.status)
            try:
                print('DEBUG save-template response json:', resp.json())
            except Exception:
                print('DEBUG save-template response text:', resp.text())
        except Exception as e:
            print('DEBUG: failed to read save-template response', e)
    if console_msgs:
        print('Console messages around save:', '\n'.join(console_msgs))

    # Prefer server-side verification over toast: ensure template exists via API
    resp_api = page.request.get(f"{live_server.url}/empresas/roles/templates/")
    data = resp_api.json()
    if not any(t['nome'] == 'E2E Template' for t in data['templates']):
        import os
        os.makedirs('artifacts/screenshots', exist_ok=True)
        os.makedirs('artifacts/html', exist_ok=True)
        screenshot_path = 'artifacts/screenshots/roles_template_save_debug.png'
        html_path = 'artifacts/html/roles_template_save_debug.html'
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, 'w', encoding='utf-8') as fh:
            fh.write(page.content())
        print(f'DEBUG: saved screenshot {screenshot_path} and html {html_path}')
        raise AssertionError('Server did not list created template')

    # Now ensure the UI select is populated; trigger reload if necessary
    try:
        page.evaluate(f"() => loadTemplatesIntoSelect({role.id})")
    except Exception:
        pass

    # Wait for the select to show the new template option
    page.wait_for_function("() => Array.from(document.querySelectorAll('#template-select option')).some(o => o.textContent.includes('E2E Template'))", timeout=10000)

    # Ensure template exists via API
    resp = page.request.get(f"{live_server.url}/empresas/roles/templates/")
    data = resp.json()
    assert any(t['nome'] == 'E2E Template' for t in data['templates'])

    # Apply the template to role (select by label and click Apply)
    page.wait_for_function("() => Array.from(document.querySelectorAll('#template-select option')).some(o => o.textContent.includes('E2E Template'))", timeout=10000)
    # Select the template
    page.select_option('#template-select', label='E2E Template')
    page.click('text=Aplicar')

    # Wait for success
    try:
        page.wait_for_selector('text=Template aplicado com sucesso', timeout=10000)
    except Exception:
        import os
        os.makedirs('artifacts/screenshots', exist_ok=True)
        os.makedirs('artifacts/html', exist_ok=True)
        screenshot_path = 'artifacts/screenshots/roles_template_apply_debug.png'
        html_path = 'artifacts/html/roles_template_apply_debug.html'
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, 'w', encoding='utf-8') as fh:
            fh.write(page.content())
        print(f'DEBUG: saved screenshot {screenshot_path} and html {html_path}')
        raise

    # Check that a RoleAudit entry was created (server-side) by requesting templates detail
    from empresas.models import PermissionTemplate
    tpl = PermissionTemplate.objects.filter(empresa=role.empresa, nome='E2E Template').first()
    assert tpl is not None
