try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import EmpresaNCM, NCM

User = get_user_model()


@pytest.fixture
def e2e_ncm_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa NCM')
        user = User.objects.create_user(username='e2encm', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        # create two company-scoped NCMs
        EmpresaNCM.objects.create(empresa=empresa, codigo='01022110', nome='Prenhes', descricao='Prenhes ou com cria', ativo=True)
        EmpresaNCM.objects.create(empresa=empresa, codigo='01022190', nome='Outros', descricao='', ativo=True)

        client = Client()
        assert client.login(username='e2encm', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'sessionid': sessionid}


def test_live_search_filters(page, live_server, e2e_ncm_data):
    sessionid = e2e_ncm_data['sessionid']
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    page.goto(f"{live_server.url}/cadastros/ncm/")

    # Type into search box and submit (press Enter) to perform full-page search (like porto_list)
    page.fill('input[name="q"]', '01022110')
    page.press('input[name="q"]', 'Enter')

    # Wait for navigation to include the query param
    page.wait_for_function("() => location.search.includes('q=01022110')", timeout=5000)

    # Only the matching row should be visible
    rows = page.locator('table tbody tr')
    assert rows.count() == 1
    text = page.locator('table tbody tr td').nth(0).inner_text()
    assert '01022110' in text


def test_non_superuser_edit_template_shows_message(page, live_server, django_db_blocker):
    with django_db_blocker.unblock():
        # create a global template NCM
        n = NCM.objects.create(codigo='01012100', nome='Trigo', ativo=True)
        user = User.objects.create_user(username='e2enonsuper', password='pass')

        client = Client()
        assert client.login(username='e2enonsuper', password='pass')
        sessionid = client.cookies['sessionid'].value

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Directly navigate to the edit page for a template (should redirect to list with message)
    page.goto(f"{live_server.url}/cadastros/ncm/{n.pk}/editar/")

    # Should end up on list page
    page.wait_for_url(f"{live_server.url}/cadastros/ncm/")

    # Flash message should be visible
    page.wait_for_selector('text=Você não tem permissão', timeout=3000)
    assert page.locator('text=Você não tem permissão').count() >= 1
