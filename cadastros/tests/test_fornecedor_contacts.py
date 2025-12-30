from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fornecedor, FornecedorContato


class FornecedorContatoTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome='F')

    def test_create_contact(self):
        url = reverse('cadastros:fornecedor_contato_create', args=[self.fornecedor.pk])
        data = {'nome': 'João', 'telefone': '1111-1111', 'tipo': 'PRINCIPAL'}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FornecedorContato.objects.filter(fornecedor=self.fornecedor, nome='João').exists())

    def test_update_contact(self):
        c = FornecedorContato.objects.create(fornecedor=self.fornecedor, nome='Antigo', telefone='000')
        url = reverse('cadastros:fornecedor_contato_update', args=[self.fornecedor.pk, c.pk])
        resp = self.client.post(url, {'nome': 'Novo', 'telefone': '999'})
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.nome, 'Novo')

    def test_delete_contact(self):
        c = FornecedorContato.objects.create(fornecedor=self.fornecedor, nome='ToDelete')
        url = reverse('cadastros:fornecedor_contato_delete', args=[self.fornecedor.pk, c.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(FornecedorContato.objects.filter(pk=c.pk).exists())
