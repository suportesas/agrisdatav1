from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fazenda, Cultura, Safra


class SafraCrudTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.fazenda = Fazenda.objects.create(nome='F', empresa=self.empresa, area_total=1, cadastrado_por=self.user)
        self.cultura = Cultura.objects.create(nome='Milho', empresa=self.empresa)
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_create_safra(self):
        url = reverse('cadastros:safra_create')
        data = {
            'nome': 'Safra Teste',
            'fazenda': str(self.fazenda.pk),
            'cultura': str(self.cultura.pk),
            'ano': '2025',
            'periodo_inicio': '2025-01-01',
            'periodo_fim': '2025-12-31',
            'status': 'PLANEJADA'
        }
        resp = self.client.post(url, data)
        # redireciona para detail
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Safra.objects.filter(nome='Safra Teste').exists())

    def test_create_safra_with_cross_year_period_auto_name(self):
        url = reverse('cadastros:safra_create')
        data = {
            'fazenda': str(self.fazenda.pk),
            'cultura': str(self.cultura.pk),
            'periodo_inicio': '2025-10-01',
            'periodo_fim': '2026-03-01',
            'status': 'PLANEJADA'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        safra = Safra.objects.get()
        self.assertEqual(safra.ano, 2025)
        self.assertEqual(safra.nome, '202526')

    def test_update_safra(self):
        safra = Safra.objects.create(nome='Old', fazenda=self.fazenda, cultura=self.cultura)
        url = reverse('cadastros:safra_update', args=[safra.pk])
        data = {
            'nome': 'Atualizada',
            'fazenda': str(self.fazenda.pk),
            'cultura': str(self.cultura.pk),
            'ano': '2025',
            'status': 'PLANEJADA'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        safra.refresh_from_db()
        self.assertEqual(safra.nome, 'Atualizada')

    def test_delete_safra(self):
        safra = Safra.objects.create(nome='Del', fazenda=self.fazenda, cultura=self.cultura)
        url = reverse('cadastros:safra_delete', args=[safra.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Safra.objects.filter(pk=safra.pk).exists())
