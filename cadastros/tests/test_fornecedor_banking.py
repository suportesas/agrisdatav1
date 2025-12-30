from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fornecedor, FornecedorDadoBancario


class FornecedorBankingTests(TestCase):
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

    def test_create_bank_account(self):
        url = reverse('cadastros:fornecedor_conta_create', args=[self.fornecedor.pk])
        data = {'banco': 'Banco X', 'conta': '123', 'conta_digito': '5'}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FornecedorDadoBancario.objects.filter(fornecedor=self.fornecedor, banco='Banco X').exists())

    def test_principal_account_uniqueness(self):
        a1 = FornecedorDadoBancario.objects.create(fornecedor=self.fornecedor, banco='B1', conta='1', conta_principal=True)
        a2 = FornecedorDadoBancario.objects.create(fornecedor=self.fornecedor, banco='B2', conta='2', conta_principal=True)
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertFalse(a1.conta_principal)
        self.assertTrue(a2.conta_principal)

    def test_update_delete_bank_account(self):
        a = FornecedorDadoBancario.objects.create(fornecedor=self.fornecedor, banco='B', conta='9')
        url = reverse('cadastros:fornecedor_conta_update', args=[self.fornecedor.pk, a.pk])
        resp = self.client.post(url, {'banco': 'Bnovo', 'conta': '99'})
        self.assertEqual(resp.status_code, 302)
        a.refresh_from_db()
        self.assertEqual(a.banco, 'Bnovo')
        # delete
        url = reverse('cadastros:fornecedor_conta_delete', args=[self.fornecedor.pk, a.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(FornecedorDadoBancario.objects.filter(pk=a.pk).exists())
