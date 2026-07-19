from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model

User = get_user_model()

class SidebarTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        # tipo padrao 'FUNC' nao tem acesso a nenhum Programa sem Role
        # explicito — o link so aparece no sidebar via
        # `user.is_admin_empresa or request|tem_acesso:'...'`, entao o
        # usuario de teste precisa ser ADMIN para o link ser renderizado.
        self.user = User.objects.create_user(username='u', password='pass', tipo='ADMIN')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_sidebar_contains_transportadoras_link(self):
        url = reverse('dashboard:index')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse('cadastros:transportadora_list'))
        self.assertContains(resp, 'Transportadoras')
