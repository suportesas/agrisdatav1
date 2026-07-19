from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from frota.models import Vehicle


class VehicleApiTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='T', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        # create vehicles
        self.v1 = Vehicle.objects.create(empresa=self.empresa, marca='A', modelo='One', renavam='R1', chassis='C1', numero_motor='M1', tipo_combustivel='DIESEL', codigo_patrimonio='P1', consumo_medio=7.5)
        self.v2 = Vehicle.objects.create(empresa=self.empresa, marca='B', modelo='Two')
        # create transportadora info
        from rh.models import Funcionario, FuncaoFuncionario
        f_role = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')
        self.driver = Funcionario.objects.create(empresa=self.empresa, nome_completo='CurDriver', cpf='0001', funcao=f_role, salario=0, cnh='X', cnh_validade=timezone.now().date() + timedelta(days=10))

    def test_api_vehicles_includes_optional_fields(self):
        url = reverse('frota:api_vehicles')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('items', data)
        items = {i['id']: i for i in data['items']}
        self.assertIn(self.v1.pk, items)
        i = items[self.v1.pk]
        self.assertEqual(i['renavam'], 'R1')
        self.assertEqual(i['chassis'], 'C1')
        self.assertEqual(i['numero_motor'], 'M1')
        self.assertEqual(i['tipo_combustivel'], 'DIESEL')
        self.assertEqual(i['codigo_patrimonio'], 'P1')
        self.assertEqual(i['consumo_medio'], '7.50')
        # no current_driver field after assignment backend removal
        self.assertNotIn('current_driver', i)

    def test_placa_atual_fallback_behavior(self):
        # v1 has no plates initially; check None
        url = reverse('frota:api_vehicles')
        resp = self.client.get(url)
        data = resp.json()
        items = {i['id']: i for i in data['items']}
        i1 = items[self.v1.pk]
        self.assertIsNone(i1['placa_atual'])

        # add a plate not marked as 'atual' -> should be returned as fallback
        from frota.models import VehiclePlate
        VehiclePlate.objects.create(vehicle=self.v1, placa='FALL-111', vigencia_inicio=timezone.now().date(), atual=False)
        resp = self.client.get(url)
        data = resp.json()
        items = {i['id']: i for i in data['items']}
        i1 = items[self.v1.pk]
        self.assertEqual(i1['placa_atual'], 'FALL-111')

        # add an 'atual' plate and ensure it takes precedence
        VehiclePlate.objects.create(vehicle=self.v1, placa='ATU-999', vigencia_inicio=timezone.now().date(), atual=True)
        resp = self.client.get(url)
        data = resp.json()
        items = {i['id']: i for i in data['items']}
        i1 = items[self.v1.pk]
        self.assertEqual(i1['placa_atual'], 'ATU-999')

