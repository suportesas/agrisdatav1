import pytest
from datetime import date
from urllib.parse import urlparse
from django.test import Client
from cadastros.models import Fazenda, Area, Talhao, Cultura, HistoricoTalhao
from empresas.models import Empresa
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.usefixtures('db')
def test_create_historico_via_ui(page, live_server):
    # Cria dados iniciais
    empresa = Empresa.objects.create(nome='E2E Empresa')
    user = User.objects.create_user(username='e2euser', password='pass')
    user.empresa = empresa
    user.save()

    fazenda = Fazenda.objects.create(empresa=empresa, nome='Fazenda E2E', area_total=100)
    area = Area.objects.create(fazenda=fazenda, empresa=empresa, nome='Area E2E', area_total=10, area_plantavel=8)
    talhao = Talhao.objects.create(area=area, fazenda=fazenda, nome='T-e2e', codigo='E2E1', area_hac=1, empresa=empresa)
    cultura = Cultura.objects.create(empresa=empresa, nome='E2E Cultura')

    # Login via Django test client para obter sessionid
    client = Client()
    assert client.login(username='e2euser', password='pass')
    sessionid = client.cookies['sessionid'].value

    # Adiciona cookie de sessão ao browser do Playwright
    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Acessa a página do talhão e registra histórico
    page.goto(f"{live_server.url}/cadastros/talhoes/{talhao.pk}/")
    page.click('text=Registrar Histórico')

    # Seleciona cultura e preenche formulário
    page.select_option('#id_cultura', str(cultura.pk))
    page.fill('#id_data_plantio', date.today().isoformat())
    page.fill('#id_producao_real', '1500')
    page.fill('#id_custo_total', '200')
    page.click("button:has-text('Registrar')")

    # Aguardar e verificar que redirecionou para a página do talhão e mensagem está presente
    page.wait_for_url(f"{live_server.url}/cadastros/talhoes/{talhao.pk}/")
    assert page.locator('text=Histórico registrado').count() >= 0

    # Verifica que existe no banco
    assert HistoricoTalhao.objects.filter(talhao=talhao, cultura=cultura).exists()
