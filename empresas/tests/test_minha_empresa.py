from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from empresas.models import Empresa, Plano

User = get_user_model()

class MinhaEmpresaTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='user1', password='pass')
        self.plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=10, limite_fazendas=2, limite_usuarios=3, limite_talhoes=5, limite_produtos=20)
        self.empresa = Empresa.objects.create(nome='E1', plano=self.plano, valor_mensalidade=10)
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_login(self.user)

    def test_plan_consumption_summary_structure(self):
        summary = self.empresa.plan_consumption_summary()
        self.assertIsInstance(summary, list)
        labels = [i['label'] for i in summary]
        self.assertIn('Fazendas', labels)
        self.assertIn('Usuários', labels)

    def test_minha_empresa_view_contains_plan(self):
        resp = self.client.get(reverse('empresas:minha_empresa'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Plano Contratado')
        self.assertContains(resp, 'Consumo do Plano')
