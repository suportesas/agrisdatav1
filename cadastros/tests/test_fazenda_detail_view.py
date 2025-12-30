from django.test import TestCase, Client
from empresas.models import Empresa
from cadastros.models import Fazenda


class FazendaDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(nome='TestCo2')
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda X', cnpj_cpf='11.111.111/0001-11', area_total=10)

    def test_fazenda_detail_page_loads(self):
        resp = self.client.get(f'/cadastros/fazendas/{self.fazenda.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Fazenda X', resp.content)
