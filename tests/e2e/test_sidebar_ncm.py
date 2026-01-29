try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa

User = get_user_model()


@pytest.fixture
def e2e_ncm_menu_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa NCM')
        user = User.objects.create_user(username='e2encm', password='pass')
        user.empresa = empresa
        user.save()

        client = Client()
        assert client.login(username='e2encm', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'sessionid': sessionid}


def test_sidebar_contains_ncm_link_and_navigates(page, live_server, e2e_ncm_menu_data):
    sessionid = e2e_ncm_menu_data['sessionid']
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    page.goto(f"{live_server.url}/")

    # Open Fiscal submenu
    page.wait_for_selector('text=Fiscal', timeout=5000)
    page.click('text=Fiscal')

    # Wait for NCMs link and click it
    page.wait_for_selector('a.submenu-link >> text=NCMs', timeout=3000)
    page.click('a.submenu-link >> text=NCMs')

    # Ensure we navigated to NCM list
    page.wait_for_url(f"{live_server.url}/cadastros/ncm/")
    assert page.locator('text=NCMs').count() >= 1
