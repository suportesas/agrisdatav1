import os

os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

try:
    import pytest
except Exception:
    # When running Django's `manage.py test` without pytest installed, skip this module
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')
from datetime import date
from urllib.parse import urlparse
from django.test import Client
from cadastros.models import Fazenda, Area, Talhao, Cultura
from empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def e2e_safra_data(django_db_blocker):
    with django_db_blocker.unblock():
        import empresas.models as empresas_models
        if not hasattr(empresas_models, 'CATEGORIAS_AGRICOLAS'):
            empresas_models.CATEGORIAS_AGRICOLAS = []

        empresa = Empresa.objects.create(nome='E2E Empresa 2')
        user = User.objects.create_user(username='e2euser2', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        fazenda = Fazenda.objects.create(empresa=empresa, nome='Fazenda E2E 2', area_total=100)
        area = Area.objects.create(fazenda=fazenda, empresa=empresa, nome='Area E2E 2', area_total=10, area_plantavel=8)
        talhao = Talhao.objects.create(area=area, fazenda=fazenda, nome='T-e2e-2', codigo='E2E2', area_hac=1, empresa=empresa)
        cultura = Cultura.objects.create(empresa=empresa, nome='E2E Cultura 2')

        client = Client()
        assert client.login(username='e2euser2', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {
        'empresa': empresa,
        'user': user,
        'fazenda': fazenda,
        'area': area,
        'talhao': talhao,
        'cultura': cultura,
        'sessionid': sessionid,
    }


def test_safra_create_talhoes_choices(page, live_server, e2e_safra_data):
    fazenda = e2e_safra_data['fazenda']
    cultura = e2e_safra_data['cultura']
    sessionid = e2e_safra_data['sessionid']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Acessa formulario de criação de safra
    page.goto(f"{live_server.url}/cadastros/safras/nova/")

    # Seleciona fazenda e aguarda carregamento dos talhões via AJAX
    page.select_option('#id_fazenda', str(fazenda.pk))
    page.wait_for_selector('#loading-talhoes', state='hidden')

    # Verifica que o select foi populado
    options_count = page.locator('#id_talhoes option').count()
    assert options_count >= 1


def test_talhao_in_use_hidden_in_dropdown(page, live_server, e2e_safra_data, django_db_blocker):
    # Cria safra que usa o talhao e verifica que ele não aparece no dropdown
    with django_db_blocker.unblock():
        from cadastros.models import Safra, Talhao
        fazenda = e2e_safra_data['fazenda']
        area = e2e_safra_data['area']
        talhao = e2e_safra_data['talhao']
        cultura = e2e_safra_data['cultura']
        # Create an additional available talhão so the form has at least one option to select
        Talhao.objects.create(area=area, fazenda=fazenda, nome='T-e2e-available', codigo='E2E-AV', area_hac=2, empresa=fazenda.empresa)
        safra = Safra.objects.create(fazenda=fazenda, cultura=cultura, ano=2025)
        safra.talhoes.add(talhao)

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': e2e_safra_data['sessionid'],
        'domain': host,
        'path': '/',
    }])

    page.goto(f"{live_server.url}/cadastros/safras/nova/")
    page.select_option('#id_fazenda', str(fazenda.pk))
    page.wait_for_selector('#loading-talhoes', state='hidden')

    # Aguarda cards de talhões renderizarem
    page.wait_for_function("() => document.querySelectorAll('.talhao-card').length > 0", timeout=5000)

    # Talhão em uso deve aparecer bloqueado
    assert page.locator('.talhao-card.disabled', has_text='E2E2').count() == 1

    # Seleciona cultura e talhão disponível (card)
    page.select_option('#id_cultura', str(cultura.pk))
    page.locator('.talhao-card', has_text='E2E-AV').first.click()
    page.wait_for_function("() => (document.getElementById('talhoes-input')?.value || '').length > 0", timeout=5000)

    # Preenche datas mínimas
    today = date.today().isoformat()
    page.fill('#id_nome', 'Safra E2E UI')
    page.fill('#id_ano', str(date.today().year))
    page.fill('#id_periodo_inicio', today)
    page.fill('#id_periodo_fim', today)

    # Submete o formulário
    page.click("button:has-text('Salvar Safra')")

    # Aguarda estabilização da navegação e valida redirecionamento para rota de safra
    page.wait_for_timeout(800)
    assert '/cadastros/safras/' in page.url
    assert '/cadastros/safras/nova/' not in page.url
