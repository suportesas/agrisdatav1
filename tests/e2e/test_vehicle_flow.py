try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import Vehicle, Funcionario
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


@pytest.fixture
def e2e_vehicle_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Veiculos')
        user = User.objects.create_user(username='e2eveiculo', password='pass')
        user.empresa = empresa
        user.save()

        # create a driver with CNH
        from cadastros.models import FuncaoFuncionario
        funcao = FuncaoFuncionario.objects.create(nome='Motorista E2E')
        driver = Funcionario.objects.create(
            empresa=empresa, nome_completo='Motorista E2E', cpf='00000000353', funcao=funcao, salario=0, cnh='ABC123', cnh_validade=timezone.now().date() + timedelta(days=365)
        )

        client = Client()
        assert client.login(username='e2eveiculo', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'driver': driver, 'sessionid': sessionid}


def test_vehicle_create_plate_assign(page, live_server, e2e_vehicle_data):
    sessionid = e2e_vehicle_data['sessionid']
    driver = e2e_vehicle_data['driver']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Go to vehicle list
    page.goto(f"{live_server.url}/cadastros/veiculos/")

    # Click add
    page.wait_for_selector('#addVehicleBtn', state='attached')
    try:
        page.click('#addVehicleBtn', timeout=5000)
    except Exception:
        page.click('#addVehicleBtn', force=True)

    page.wait_for_selector('form', timeout=5000)

    # Fill vehicle form
    page.select_option('select[name="tipo"]', 'LEVE')
    page.fill('input[name="marca"]', 'TestMarca')
    page.fill('input[name="modelo"]', 'TestModelo')
    page.fill('input[name="cor"]', 'Branco')

    # Submit
    try:
        page.click('#vehicleSaveBtn')
    except Exception:
        page.click('#vehicleSaveBtn', force=True)

    # Wait for redirect to detail page
    page.wait_for_url(f"{live_server.url}/cadastros/veiculos/*")

    # Check brand/model present
    assert page.locator('text=TestMarca').count() >= 1
    assert page.locator('text=TestModelo').count() >= 1

    # Add a plate
    today = timezone.now().date().isoformat()
    page.fill('input[name="placa"]', 'E2E-1234')
    page.fill('input[name="vigencia_inicio"]', today)
    try:
        page.click('#plateSaveBtn')
    except Exception:
        page.click('#plateSaveBtn', force=True)

    page.wait_for_timeout(500)
    # Ensure plate appears in list
    assert page.locator('text=E2E-1234').count() >= 1

    # Assign driver
    # Select by value (driver.pk)
    page.select_option('select[name="motorista"]', str(driver.pk))
    # Fill start datetime (use now)
    now = datetime.now().strftime('%Y-%m-%dT%H:%M')
    page.fill('input[name="data_inicio"]', now)
    try:
        page.click('#assignmentSaveBtn')
    except Exception:
        page.click('#assignmentSaveBtn', force=True)

    page.wait_for_timeout(500)

    # Check driver appears in assignments
    assert page.locator(f'text={driver.nome_completo}').count() >= 1
