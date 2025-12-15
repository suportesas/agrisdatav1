from django.urls import reverse
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano


class SafraViewsTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_safra_list_view_authenticated(self):
        resp = self.client.get(reverse('cadastros:safra_list'))
        self.assertEqual(resp.status_code, 200)
