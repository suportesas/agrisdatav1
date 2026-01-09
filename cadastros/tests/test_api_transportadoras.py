from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
from cadastros.models import Transportadora, Viagem
from datetime import date

User = get_user_model()

class ApiTransportadorasTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.t1 = Transportadora.objects.create(empresa=self.empresa, razao_social='T1', cidade='C1', uf='SP', frete_padrao=10)
        self.t2 = Transportadora.objects.create(empresa=self.empresa, razao_social='T2', cidade='C2', uf='PR', frete_padrao=20)
        Viagem.objects.create(transportadora=self.t1, origem='A', destino='B', data=date(2025,1,1), valor_frete=100)

    def test_list_json(self):
        url = reverse('cadastros:api_transportadoras')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('items', data)
        self.assertGreaterEqual(data['count'], 2)

    def test_viagens_json(self):
        url = reverse('cadastros:api_transportadora_viagens', args=[self.t1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['items'][0]['origem'], 'A')