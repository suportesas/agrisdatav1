from django.urls import reverse
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Safra, SafraPlan

class SafraPlanViewsTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        self.fazenda = self.empresa.fazendas.create(nome='F Teste', area_total=10)
        self.safra = Safra.objects.create(fazenda=self.fazenda, ano=2026)

    def test_get_create_plan(self):
        url = reverse('cadastros:safra_plan_create', args=[self.safra.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'cadastros/safra/safra_plan_form.html')

    def test_post_create_plan(self):
        url = reverse('cadastros:safra_plan_create', args=[self.safra.pk])
        data = {
            'planned_area': '120.0000',
            'planned_production': '50.00',
            'planned_plantio': '2026-04-01',
            'planned_colheita': '2026-09-01'
        }
        resp = self.client.post(url, data)
        # should redirect to detail
        self.assertEqual(resp.status_code, 302)
        self.safra.refresh_from_db()
        self.assertTrue(hasattr(self.safra, 'plano'))
        self.assertEqual(str(self.safra.plano.planned_production), '50.00')

    def test_update_plan(self):
        SafraPlan.objects.create(safra=self.safra, planned_production='10.00')
        url = reverse('cadastros:safra_plan_update', args=[self.safra.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = {
            'planned_area': '100.0000',
            'planned_production': '200.00',
            'planned_plantio': '2026-04-01',
            'planned_colheita': '2026-09-01'
        }
        resp2 = self.client.post(url, data)
        self.assertEqual(resp2.status_code, 302)
        self.safra.refresh_from_db()
        self.assertEqual(str(self.safra.plano.planned_production), '200.00')

    def test_ajax_create_plan(self):
        url = reverse('cadastros:safra_plan_create', args=[self.safra.pk])
        data = {
            'planned_area': '120.0000',
            'planned_production': '50.00',
            'planned_plantio': '2026-04-01',
            'planned_colheita': '2026-09-01'
        }
        resp = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        js = resp.json()
        self.assertTrue(js.get('success'))
        self.safra.refresh_from_db()
        self.assertTrue(hasattr(self.safra, 'plano'))

    def test_ajax_create_plan_invalid(self):
        url = reverse('cadastros:safra_plan_create', args=[self.safra.pk])
        data = {
            'planned_area': '',
            'planned_production': '',
        }
        resp = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        js = resp.json()
        self.assertFalse(js.get('success'))
        self.assertIn('html', js)

    def test_ajax_delete_plan(self):
        SafraPlan.objects.create(safra=self.safra, planned_production='10.00')
        url = reverse('cadastros:safra_plan_delete', args=[self.safra.pk])
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        js = resp.json()
        self.assertTrue(js.get('success'))
        self.safra.refresh_from_db()
        self.assertFalse(hasattr(self.safra, 'plano'))

    def test_ajax_update_plan(self):
        plan = SafraPlan.objects.create(safra=self.safra, planned_production='10.00')
        url = reverse('cadastros:safra_plan_update', args=[self.safra.pk])
        # GET via AJAX should return partial HTML
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        js = resp.json()
        self.assertTrue(js.get('success'))
        self.assertIn('planned_production', js.get('html'))
        # POST update via AJAX
        data = {'planned_area': '222.0000', 'planned_production': '777.00', 'planned_plantio': '2026-05-01', 'planned_colheita': '2026-10-01'}
        resp2 = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp2.status_code, 200)
        js2 = resp2.json()
        self.assertTrue(js2.get('success'))
        self.safra.refresh_from_db()
        self.assertEqual(str(self.safra.plano.planned_production), '777.00')
