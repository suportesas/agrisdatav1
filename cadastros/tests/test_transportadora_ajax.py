from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
from cadastros.models import Transportadora

User = get_user_model()

class TransportadoraAjaxTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.t = Transportadora.objects.create(empresa=self.empresa, razao_social='T1', frete_padrao=100)

    def test_update_frete_ajax_success(self):
        url = reverse('cadastros:transportadora_update_frete', args=[self.t.pk])
        resp = self.client.post(url, {'frete': '150.50'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('sucesso'))
        self.t.refresh_from_db()
        self.assertEqual(str(self.t.frete_padrao), '150.50')

    def test_update_frete_ajax_invalid(self):
        url = reverse('cadastros:transportadora_update_frete', args=[self.t.pk])
        resp = self.client.post(url, {'frete': 'abc'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('erro', data)

    def test_update_frete_ajax_negative(self):
        url = reverse('cadastros:transportadora_update_frete', args=[self.t.pk])
        resp = self.client.post(url, {'frete': '-10'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn('erro', data)

    def test_update_frete_ajax_unauthorized(self):
        # different user (no empresa)
        other = User.objects.create_user(username='o', password='pass')
        self.client.logout()
        self.client.login(username='o', password='pass')
        url = reverse('cadastros:transportadora_update_frete', args=[self.t.pk])
        resp = self.client.post(url, {'frete': '200'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 404)  # should not find transportadora for this user's empresa
