from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from usuarios.models import Usuario
from empresas.models import Plano, Empresa
from cadastros.models import Vehicle, VehiclePlate, FuncaoFuncionario, Funcionario, Transportadora


class VehicleListViewTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='T', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        self.transportadora = Transportadora.objects.create(empresa=self.empresa, razao_social='Trans X')
        self.v = Vehicle.objects.create(empresa=self.empresa, marca='M', modelo='Mod', transportadora=self.transportadora)
        self.frole = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')
        self.driver = Funcionario.objects.create(empresa=self.empresa, nome_completo='Driver L', cpf='111', funcao=self.frole, salario=0, cnh='X', cnh_validade=timezone.now().date()+timedelta(days=365))
        # add other type vehicles to verify counts
        Vehicle.objects.create(empresa=self.empresa, marca='Heavy', modelo='H', tipo='PESADO')
        Vehicle.objects.create(empresa=self.empresa, marca='Med', modelo='M', tipo='MEDIO')

    def test_vehicle_list_shows_transportadora_and_driver(self):
        url = reverse('cadastros:vehicle_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Trans X', content)
        # Verify type count cards appear
        self.assertIn('Leve', content)
        self.assertIn('Pesado', content)
        self.assertIn('Médio', content)
        # counts should show numbers (at least 1 for each created type)
        self.assertRegex(content, r'Leve[\s\S]*?\d+')
        self.assertRegex(content, r'Pesado[\s\S]*?\d+')
        self.assertRegex(content, r'Médio[\s\S]*?\d+')
        # cards should be clickable filter links
        self.assertIn('?tipo=LEVE', content)

    def test_pagination_shows_ten_per_page(self):
        # Create enough vehicles to require pagination
        for i in range(12):
            Vehicle.objects.create(empresa=self.empresa, marca=f'M{i}', modelo=f'Mod{i}')
        url = reverse('cadastros:vehicle_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # There should be at most 10 vehicle cards on the first page
        cards = content.count('fornecedor-card')
        self.assertTrue(cards <= 10)
        # And pagination controls should be present
        self.assertIn('page-item', content)
        # Request the second page and assert remaining items show
        resp2 = self.client.get(url + '?page=2')
        self.assertEqual(resp2.status_code, 200)
        content2 = resp2.content.decode('utf-8')
        self.assertTrue('fornecedor-card' in content2)
