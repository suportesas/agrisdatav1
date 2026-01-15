try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import CFOP
from django.contrib.auth.models import Group, Permission

User = get_user_model()


@pytest.fixture
def e2e_cfop_import_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa CFOP')
        user = User.objects.create_user(username='e2eimport', password='pass')
        user.empresa = empresa
        user.save()

        # Grant group permission to import CFOPs
        g, _ = Group.objects.get_or_create(name='E2E Import Test')
        perm = Permission.objects.get(codename='add_cfop', content_type__app_label='cadastros')
        g.permissions.add(perm)
        user.groups.add(g)

        client = Client()
        assert client.login(username='e2eimport', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'sessionid': sessionid}


def test_cfop_import_dry_run_and_persist(page, live_server, e2e_cfop_import_data, django_db_blocker):
    sessionid = e2e_cfop_import_data['sessionid']
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    page.goto(f"{live_server.url}/cadastros/cfop/importar/")

    # Prepare CSV with one valid and one invalid row
    csv_bytes = b"codigo,nome,descricao\n5102,Venda Interna,Teste\nabcd,Invalido,Top\n"

    # Dry-run (default checkbox is checked)
    page.set_input_files('input[name="arquivo"]', {'name': 'cfop_sample.csv', 'mimeType': 'text/csv', 'buffer': csv_bytes})
    page.click('button:has-text("Enviar")')

    # Button should be disabled immediately to prevent duplicate submits
    page.wait_for_function("() => document.querySelector('button#cfopImportBtn').disabled === true", timeout=2000)

    # Wait for result block
    page.wait_for_selector('pre', timeout=5000)
    text = page.locator('pre').inner_text()
    assert 'dry_run=True' in text or 'Import concluído' in text

    # Ensure that in dry-run no CFOP was created
    with django_db_blocker.unblock():
        assert not CFOP.objects.filter(codigo='5102').exists()

    # Now perform actual import: uncheck dry_run and submit
    page.uncheck('input[name="dry_run"]')
    # attach same file again
    page.set_input_files('input[name="arquivo"]', {'name': 'cfop_sample.csv', 'mimeType': 'text/csv', 'buffer': csv_bytes})
    page.click('button:has-text("Enviar")')

    page.wait_for_selector('pre', timeout=5000)
    text2 = page.locator('pre').inner_text()
    assert 'Criado' in text2 or 'Import concluído' in text2

    # Verify CFOP was persisted
    with django_db_blocker.unblock():
        assert CFOP.objects.filter(codigo='5102').exists()
