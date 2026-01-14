import pytest
from urllib.parse import urlparse
from empresas.models import Role, Empresa


def test_role_selection_highlight_and_hide(page, live_server, e2e_roles_data, django_db_blocker):
    # Setup: create a second role so we have at least two
    with django_db_blocker.unblock():
        empresa = e2e_roles_data['empresa']
        Role.objects.create(empresa=empresa, name='E2E Role 2')

    sessionid = e2e_roles_data['sessionid']
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{'name': 'sessionid', 'value': sessionid, 'domain': host, 'path': '/'}])

    page.goto(f"{live_server.url}/empresas/roles/")
    page.wait_for_selector('.role-card', timeout=5000)

    # Click first card
    page.click('.role-card >> nth=0')
    # Ensure it has selected class
    selected_count = page.evaluate("() => document.querySelectorAll('.role-card.selected').length")
    assert selected_count == 1

    # Click second card to change selection (do this while both are visible)
    page.click('.role-card >> nth=1')
    selected_count2 = page.evaluate("() => document.querySelectorAll('.role-card.selected').length")
    assert selected_count2 == 1

    # Toggle hide others (now that a card is selected, hidden cards should be collapsed)
    page.click('#toggle-hide')
    # Ensure only one role is visible
    visible_count = page.evaluate("() => Array.from(document.querySelectorAll('.role-card')).filter(c=>c.offsetParent!==null).length")
    assert visible_count == 1, 'Expected only the selected role to be visible when hide toggle is active'

    # Turn off hide and ensure both visible (poll a few times for animation/dom updates)
    page.click('#toggle-hide')
    visible_count2 = 0
    # Give more time for animations / DOM updates
    for _ in range(40):
        visible_count2 = page.evaluate("() => Array.from(document.querySelectorAll('.role-card')).filter(c=>c.offsetParent!==null).length")
        if visible_count2 >= 2:
            break
        page.wait_for_timeout(500)
    try:
        assert visible_count2 >= 2, f'Expected at least 2 visible roles, got {visible_count2}'
    except AssertionError:
        import os
        os.makedirs('artifacts/screenshots', exist_ok=True)
        os.makedirs('artifacts/html', exist_ok=True)
        screenshot_path = 'artifacts/screenshots/roles_ui_debug.png'
        html_path = 'artifacts/html/roles_ui_debug.html'
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, 'w', encoding='utf-8') as fh:
            fh.write(page.content())
        print(f'DEBUG: saved screenshot {screenshot_path} and html {html_path}')
        raise