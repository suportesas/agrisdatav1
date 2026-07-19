from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import Fazenda

User = get_user_model()


class FazendaDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.empresa = Empresa.objects.create(nome='TestCo2')
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda X', cnpj_cpf='11.111.111/0001-11', area_total=10)
        # fazenda_detail e @login_required e filtra por empresa=request.user.empresa
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_login(self.user)

    def test_fazenda_detail_page_loads(self):
        resp = self.client.get(f'/cadastros/fazendas/{self.fazenda.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Fazenda X', resp.content)
