from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from cadastros.models import NCM

User = get_user_model()

class TestNCMModel(TestCase):
    def test_codigo_validation(self):
        n = NCM(codigo='12A34', nome='Teste')
        with self.assertRaises(ValidationError):
            n.full_clean()

        n.codigo = '01012100'
        n.full_clean()  # OK
        n.save()
        self.assertEqual(NCM.objects.count(), 1)

class TestNCMViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.client.force_login(self.user)

    def test_crud_flow(self):
        # Create
        url = reverse('cadastros:ncm_create')
        resp = self.client.post(url, {'codigo': '01012100', 'nome': 'Trigo', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        n = NCM.objects.get(codigo='01012100')
        self.assertEqual(n.nome, 'Trigo')

        # Update
        url = reverse('cadastros:ncm_update', args=[n.pk])
        resp = self.client.post(url, {'codigo': '01012100', 'nome': 'Trigo Alterado', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        n.refresh_from_db()
        self.assertEqual(n.nome, 'Trigo Alterado')

        # Autocomplete
        url = reverse('cadastros:ncm_autocomplete') + '?q=010'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue('items' in data and len(data['items'])>0)

        # Delete
        url = reverse('cadastros:ncm_delete', args=[n.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(NCM.objects.filter(pk=n.pk).exists())
