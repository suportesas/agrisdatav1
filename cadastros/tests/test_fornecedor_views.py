from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fornecedor


class FornecedorViewsTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_list_view_shows_fornecedor(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='Fornecedor A')
        url = reverse('cadastros:fornecedor_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Fornecedor A')

    def test_create_view_creates_fornecedor(self):
        url = reverse('cadastros:fornecedor_create')
        data = {
            'nome': 'Novo Fornecedor',
            'cnpj_cpf': '22.222.222/2222-22',
            'telefone': '1111-1111'
        }
        resp = self.client.post(url, data)
        # should redirect to detail
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Fornecedor.objects.filter(nome='Novo Fornecedor').exists())

    def test_update_view_updates_fornecedor(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='Old Name')
        url = reverse('cadastros:fornecedor_update', args=[f.pk])
        data = {'nome': 'New Name'}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        f.refresh_from_db()
        self.assertEqual(f.nome, 'New Name')

    def test_delete_view_deletes_fornecedor(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='ToDelete')
        url = reverse('cadastros:fornecedor_delete', args=[f.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Fornecedor.objects.filter(pk=f.pk).exists())
