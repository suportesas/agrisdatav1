from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from empresas.models import Empresa, Plano
from cadastros.models import Porto
from cadastros.forms import PortoForm


class PortoTestCase(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_unique_constraint_empresa_codigo(self):
        Porto.objects.create(empresa=self.empresa, codigo='BRBEL', nome='Belém', pais='BR', cidade='Belém')
        with self.assertRaises(IntegrityError):
            Porto.objects.create(empresa=self.empresa, codigo='BRBEL', nome='Belém2', pais='BR', cidade='Belém')

    def test_porto_form_clean_codigo_uniqueness(self):
        Porto.objects.create(empresa=self.empresa, codigo='BRREC', nome='Recife', pais='BR', cidade='Recife')
        form = PortoForm(data={'codigo': 'brrec', 'nome': 'Recife', 'pais': 'BR', 'cidade': 'Recife', 'tipo': 'MARITIMO', 'ativo': True}, empresa=self.empresa)
        self.assertFalse(form.is_valid())
        self.assertIn('codigo', form.errors)

    def test_create_porto_via_view(self):
        url = reverse('cadastros:porto_create')
        data = {'codigo': 'BRRIO', 'nome': 'Rio de Janeiro', 'pais': 'BR', 'cidade': 'Rio', 'tipo': 'MARITIMO', 'ativo': True}
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Porto.objects.filter(empresa=self.empresa, codigo='BRRIO').exists())

    def test_porto_list_view(self):
        Porto.objects.create(empresa=self.empresa, codigo='BRSSA', nome='Salvador', pais='BR', cidade='Salvador')
        url = reverse('cadastros:porto_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Salvador')
