from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Vehicle, FuncaoFuncionario, Funcionario


class VehicleApiFilterTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='T', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        f_role = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')
        self.driver = Funcionario.objects.create(empresa=self.empresa, nome_completo='D1', cpf='0002', funcao=f_role, salario=0, cnh='X', cnh_validade=timezone.now().date() + timedelta(days=10))

        self.v1 = Vehicle.objects.create(empresa=self.empresa, marca='A', modelo='One', tipo_combustivel='DIESEL', consumo_medio=5)
        self.v2 = Vehicle.objects.create(empresa=self.empresa, marca='B', modelo='Two', tipo_combustivel='GASOLINA', consumo_medio=10)



    def test_filter_by_tipo_combustivel(self):
        url = reverse('cadastros:api_vehicles') + '?tipo_combustivel=GASOLINA'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [i['id'] for i in data['items']]
        self.assertIn(self.v2.pk, ids)
        self.assertNotIn(self.v1.pk, ids)



    def test_ordering_consumo(self):
        url = reverse('cadastros:api_vehicles') + '?sort=-consumo_medio'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data['items']
        self.assertGreater(float(items[0]['consumo_medio']), float(items[1]['consumo_medio']))
