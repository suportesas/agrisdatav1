from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
from cadastros.models import Transportadora, Viagem
from datetime import date

User = get_user_model()

class TransportadoraViewsTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        self.t1 = Transportadora.objects.create(empresa=self.empresa, razao_social='T1', cidade='CidadeA', uf='SP')
        self.t2 = Transportadora.objects.create(empresa=self.empresa, razao_social='T2', cidade='CidadeB', uf='PR', frete_padrao=150)

        Viagem.objects.create(transportadora=self.t1, origem='A', destino='B', data=date(2025,1,1), valor_frete=100)
        Viagem.objects.create(transportadora=self.t1, origem='C', destino='D', data=date(2025,2,1), valor_frete=200)

    def test_transportadora_list_shows_cards(self):
        url = reverse('cadastros:transportadora_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'T1')
        self.assertContains(resp, 'CidadeA')
        self.assertContains(resp, 'Viagens')

    def test_transportadora_detail_shows_viagens(self):
        url = reverse('cadastros:transportadora_detail', args=[self.t1.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A')
        self.assertContains(resp, 'C')
        self.assertContains(resp, 'R$ 200')

    def test_filters_work(self):
        url = reverse('cadastros:transportadora_list') + '?uf=PR'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'T2')
        self.assertNotContains(resp, 'T1')

    def test_create_page_has_autofill_js(self):
        url = reverse('cadastros:transportadora_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'CADASTROS_BUSCAR_CNPJ_URL')
        self.assertContains(resp, 'cadastros_transportadora.js')

    def test_pagination_preserves_filters(self):
        # create more than one page (default page size 20)
        for i in range(25):
            Transportadora.objects.create(empresa=self.empresa, razao_social=f'T{i}', cidade='C{i}', uf='SP', tipo='TER')

        url = reverse('cadastros:transportadora_list') + '?q=T&tipo=TER'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # pagination links should include our filters
        self.assertIn('page=2', content)
        self.assertIn('q=T', content)
        self.assertIn('tipo=TER', content)
