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

User = get_user_model()


@pytest.fixture
def e2e_cfop_import_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa CFOP')
        # tipo='ADMIN' -> is_admin_empresa() bypassa o ProgramaEnforcementMiddleware
        # (core/middleware/programa_enforcement.py) e o check manual de
        # usuario_tem_acesso() dentro de cadastros.views.cfop_import
        user = User.objects.create_user(username='e2eimport', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

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

    # Dry-run (default checkbox is checked). O form em cfop_import.html e um
    # POST tradicional (sem preventDefault) que recarrega a pagina inteira
    # renderizando o mesmo template com `result` populado — nao ha estado
    # "disabled" para checar de forma confiavel apos o clique, so o resultado
    # final pos-reload.
    page.set_input_files('input[name="arquivo"]', {'name': 'cfop_sample.csv', 'mimeType': 'text/csv', 'buffer': csv_bytes})
    page.click('button:has-text("Enviar")')

    # Wait for result block
    page.wait_for_selector('pre', timeout=5000)
    text = page.locator('pre').inner_text()
    assert 'dry_run=True' in text

    # A transient toast should also be shown and provide a details link
    page.wait_for_selector("div.alert", timeout=5000)
    page.wait_for_selector('a#toast-detail-link', timeout=5000)
    page.click('a#toast-detail-link')
    # After clicking, the <pre> of results should receive focus
    active_tag = page.evaluate("() => document.activeElement && document.activeElement.tagName")
    assert active_tag == 'PRE'

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
    assert 'Criado' in text2 or 'Importação concluída' in text2

    # Verify CFOP was persisted
    with django_db_blocker.unblock():
        assert CFOP.objects.filter(codigo='5102').exists()
