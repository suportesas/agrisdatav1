try:
    import pytest
except Exception:
    import unittest
    raise unittest.SkipTest('pytest not available - skipping E2E Playwright tests')

from urllib.parse import urlparse
from django.test import Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from frota.models import Vehicle, VehiclePlate
from rh.models import Funcionario
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


@pytest.fixture
def e2e_plate_data(django_db_blocker):
    with django_db_blocker.unblock():
        empresa = Empresa.objects.create(nome='E2E Empresa Plate')
        user = User.objects.create_user(username='e2eplate', password='pass')
        user.empresa = empresa
        user.save()

        # create vehicle and plate
        v = Vehicle.objects.create(empresa=empresa, marca='TestMarca', modelo='TestModelo')
        VehiclePlate.objects.create(vehicle=v, placa='OLD-1111', vigencia_inicio=timezone.now().date(), atual=True)

        client = Client()
        assert client.login(username='e2eplate', password='pass')
        sessionid = client.cookies['sessionid'].value

    return {'empresa': empresa, 'user': user, 'vehicle': v, 'sessionid': sessionid}


def test_edit_and_delete_plate(page, live_server, e2e_plate_data):
    sessionid = e2e_plate_data['sessionid']
    vehicle = e2e_plate_data['vehicle']

    parsed = urlparse(live_server.url)
    host = parsed.hostname or '127.0.0.1'
    page.context.add_cookies([{
        'name': 'sessionid',
        'value': sessionid,
        'domain': host,
        'path': '/',
    }])

    # Go to vehicle detail
    page.goto(f"{live_server.url}/cadastros/veiculos/{vehicle.pk}/")

    # Click Edit on first plate (opens modal)
    page.wait_for_selector('button.btn-plate-edit')
    page.click('button.btn-plate-edit')

    # Change plate in modal
    page.wait_for_selector('#plateEditModal input#modal_placa', timeout=3000)
    page.fill('#modal_placa', 'NEW-2222')
    page.click('#plateEditModal button:has-text("Salvar")')

    # Wait for DOM update
    try:
        page.wait_for_selector('text=NEW-2222', timeout=20000)
        assert page.locator('text=NEW-2222').count() >= 1
    except Exception:
        import os
        os.makedirs('artifacts/screenshots', exist_ok=True)
        os.makedirs('artifacts/html', exist_ok=True)
        screenshot_path = 'artifacts/screenshots/plate_edit_debug.png'
        html_path = 'artifacts/html/plate_edit_debug.html'
        page.screenshot(path=screenshot_path, full_page=True)
        with open(html_path, 'w', encoding='utf-8') as fh:
            fh.write(page.content())
        print(f'DEBUG: saved screenshot {screenshot_path} and html {html_path}')
        raise

    # Now delete the plate (confirm page)
    page.click('a:has-text("Excluir")')
    page.wait_for_selector('button:has-text("Excluir")')
    page.click('button:has-text("Excluir")')

    # Confirm plate not present
    page.wait_for_timeout(500)
    assert page.locator('text=NEW-2222').count() == 0
