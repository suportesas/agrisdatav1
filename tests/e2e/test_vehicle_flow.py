try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def e2e_vehicle_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Veiculos')
        user = User.objects.create_user(username='e2eveiculo', password='pass', tipo='ADMIN')
        user.empresa = empresa
        user.save()

        client = Client()
        assert client.login(username='e2eveiculo', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'sessionid': sessionid}


def test_vehicle_create_plate_assign(page, live_server, e2e_vehicle_data):
    """Cria um veículo em /frota/veiculos/novo/ e adiciona uma placa no
    detalhe. frota/forms.py:VehicleForm usa Meta.exclude (não fields), então
    os widgets 'tipo'/'marca'/'modelo'/'cor' vêm direto do model Vehicle.
    """
    sessionid = e2e_vehicle_data['sessionid']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Go to vehicle list and open the create form
    page.goto(f"{live_server.url}/frota/veiculos/")
    page.click('#addVehicleBtn')
    page.wait_for_selector('form', timeout=5000)

    # Fill vehicle form
    page.select_option('select[name="tipo"]', 'LEVE')
    page.fill('input[name="marca"]', 'TestMarca')
    page.fill('input[name="modelo"]', 'TestModelo')
    page.fill('input[name="cor"]', 'Branco')
    page.click('#vehicleSaveBtn')

    # vehicle_create redireciona para o detalhe do veículo recém-criado
    page.wait_for_url(f"{live_server.url}/frota/veiculos/*", timeout=10000)
    assert page.locator('text=TestMarca').count() >= 1
    assert page.locator('text=TestModelo').count() >= 1

    # Add a plate via the plain "Adicionar Placa" form on the detail page
    # (frota:vehicle_plate_create — POST tradicional com reload, nao modal)
    today = timezone.now().date().isoformat()
    page.fill('input[name="placa"]', 'E2E-1234')
    page.fill('input[name="vigencia_inicio"]', today)
    page.click('#plateSaveBtn')

    page.wait_for_selector('text=E2E-1234', timeout=5000)

    # Assignment UI was removed; ensure the motorista select is not present
    assert page.locator('select[name="motorista"]').count() == 0
