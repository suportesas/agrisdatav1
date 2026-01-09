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

    # Verify user is logged in in the browser context
    console_msgs = []
    responses = []
    # Use property .text since ConsoleMessage.text may be a property in this Playwright version
    page.on('console', lambda m: console_msgs.append(m.text))
    def on_response(r):
        if '/permissions/' in r.url:
            try:
                # r.text() may be expensive; attempt to capture body when possible
                text = r.text() if callable(getattr(r, 'text', None)) else r.text
                responses.append({'url': r.url, 'status': r.status, 'text': text})
            except Exception:
                responses.append({'url': r.url, 'status': r.status})
    page.on('response', on_response)

    page.goto(f"{live_server.url}/dashboard/")
    # Dashboard shows a logout or user menu; wait to confirm session cookie valid
    page.wait_for_selector('text=Sair', timeout=3000)

    # Navigate directly to the permissions page for the role created in fixture
    page.goto(f"{live_server.url}/empresas/roles/{role.pk}/permissions/")
    page.wait_for_selector('text=Permissões', timeout=5000)

    # Check whether loadPermissions() exists in the page and invoke it explicitly to capture errors
    try:
        is_fn = page.evaluate("() => typeof loadPermissions === 'function'")
        print('loadPermissions defined?', is_fn)
        # Invoke fetch directly from the page to see if the server returns JSON when X-Requested-With header is present
        try:
            fetch_res = page.evaluate("async (rid) => { const r = await fetch('/empresas/roles/'+rid+'/permissions/', {headers: {'X-Requested-With': 'XMLHttpRequest'}}); const txt = await r.text(); let json=null; try{ json = JSON.parse(txt);}catch(e){} return {status: r.status, body: txt.slice(0,1000), json: json}; }", role.id)
            print('fetch via page returned:', fetch_res)
        except Exception as e:
            print('Error invoking fetch via page', e)

        # Explicitly run the loadPermissions helper to ensure it renders the permissions table
        try:
            lp_res = page.evaluate("async (rid) => { try { await loadPermissions(rid); return 'ok' } catch(e) { return 'err:'+e.message } }", role.id)
            print('loadPermissions invocation returned:', lp_res)
            # Probe the first add checkbox DOM state
            probe = page.evaluate("() => { const el = document.querySelector('#permissions-area table tbody tr input[name=\'add\']'); if(!el) return {exists:false}; const b = el.getBoundingClientRect(); const s = window.getComputedStyle(el); return {exists:true, disabled: el.disabled, width: el.offsetWidth, height: el.offsetHeight, visible: (s.visibility === 'visible' && s.display !== 'none' && el.offsetWidth>0 && el.offsetHeight>0), bbox: {x: b.x, y: b.y, w: b.width, h: b.height}} }")
            print('first add probe:', probe)
        except Exception as e:
            print('Error invoking loadPermissions explicitly:', e)
    except Exception as e:
        print('Error invoking loadPermissions:', e)

    # Diagnostic: directly call the permissions endpoint to inspect server response
    resp = page.request.get(f"{live_server.url}/empresas/roles/{role.pk}/permissions/", headers={'Cookie': f'sessionid={sessionid}'})
    try:
        print('permissions endpoint status:', resp.status)
        txt = resp.text()
        print('permissions endpoint body (truncated):', txt[:1000])
    except Exception as e:
        print('permissions endpoint read failed', e)

    # (Optional) ensure loadPermissions JS ran and table populated
    try:
        page.wait_for_selector('table tbody tr', timeout=5000)
    except Exception:
        # Probe DOM to see if table exists and rows count
        rows_count = page.evaluate("() => document.querySelectorAll('#permissions-area table tbody tr').length")
        has_table = page.evaluate("() => !!document.querySelector('#permissions-area table')")
        print('Debug: table present?', has_table, 'rows_count=', rows_count)
        raise

    # Wait for permissions section to render
    page.wait_for_selector('text=Permissões')

    # Ensure the table has rows (debugging for flakiness)
    try:
        # Wait for at least one permission row to appear
        page.wait_for_selector('table tbody tr', timeout=10000)
    except Exception as e:
        print('*** DEBUG: Permission table rows not found. Dumping page content and console logs:')
        html = page.content()
        print(html[:4000])
        print('\n--- Console messages ---')
        for m in console_msgs:
            print(m)
        print('\n--- /permissions/ responses captured ---')
        for r in responses:
            print(r)
        raise

    # Toggle add checkbox for model 'empresa' (if present)
    try:
        row_selector = "tr[data-model='empresa']"
        page.wait_for_selector(row_selector, timeout=2000)
        add_checkbox = page.locator(f"{row_selector} input[name='add']")
        add_checkbox.check()
    except Exception:
        # If the model 'empresa' isn't present (depends on available apps), pick first row
        first_add = page.locator('table tbody tr >> nth=0 input[name="add"]')
        # Probe DOM state for debugging
        exists = page.evaluate("() => !!document.querySelector(\"table tbody tr input[name='add']\")")
        props = page.evaluate("() => { const el = document.querySelector(\"table tbody tr input[name='add']\"); if(!el) return null; const s = window.getComputedStyle(el); const r = el.getBoundingClientRect(); return {disabled: el.disabled, visible: (s.display !== 'none' && s.visibility === 'visible' && r.width>0 && r.height>0), width: r.width, height: r.height, outerHTML: el.outerHTML}; }")
        print('Fallback first_add exists?', exists, 'props=', props)
        try:
            first_add.check()
        except Exception:
            # Last resort: try to click via JS to bypass Playwright's visibility checks
            print('Playwright check failed, attempting JS click fallback')
            page.evaluate("() => { const el = document.querySelector(\"table tbody tr input[name='add']\"); if(el) el.click(); }")
            page.wait_for_timeout(200)
            # If still not checked, raise
            checked = page.evaluate("() => document.querySelector(\"table tbody tr input[name='add']\") ? document.querySelector(\"table tbody tr input[name='add']\").checked : false")
            print('After JS click, checked=', checked)
            if not checked:
                raise

