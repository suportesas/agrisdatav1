from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from usuarios.models import Usuario
from empresas.models import Plano, Empresa
from frota.models import Vehicle
from rh.models import FuncaoFuncionario, Funcionario
from cadastros.models import Transportadora


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

    def test_vehicle_list_shows_transportadora_and_type_filters(self):
        """cadastros/templates/cadastros/vehicle/vehicle_list.html renderiza
        os veículos numa tabela (não cards) e os contadores por tipo como
        links .kpi-card com ?tipo=<TIPO>."""
        url = reverse('frota:vehicle_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Trans X', content)
        self.assertIn('Leve', content)
        self.assertIn('Pesado', content)
        self.assertIn('Médio', content)
        # cards de tipo devem ser links de filtro clicáveis
        self.assertIn('?tipo=LEVE', content)
        self.assertIn('?tipo=PESADO', content)
        self.assertIn('?tipo=MEDIO', content)

        # filtro por tipo de fato restringe a listagem
        resp_pesado = self.client.get(url + '?tipo=PESADO')
        content_pesado = resp_pesado.content.decode('utf-8')
        self.assertIn('Heavy', content_pesado)
        self.assertNotIn('Med', content_pesado)

    def test_pagination_shows_twenty_per_page(self):
        # frota/views_vehicle.py:vehicle_list pagina com Paginator(veiculos, 20)
        for i in range(20):
            Vehicle.objects.create(empresa=self.empresa, marca=f'M{i}', modelo=f'Mod{i}')
        # total = 3 (setUp) + 20 = 23 veículos -> 2 páginas (20 + 3)

        url = reverse('frota:vehicle_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        rows = content.count('<tr>') - 1  # subtrai a linha de cabeçalho da thead
        self.assertEqual(rows, 20)
        self.assertIn('page-item', content)

        resp2 = self.client.get(url + '?page=2')
        self.assertEqual(resp2.status_code, 200)
        content2 = resp2.content.decode('utf-8')
        rows2 = content2.count('<tr>') - 1
        self.assertEqual(rows2, 3)
