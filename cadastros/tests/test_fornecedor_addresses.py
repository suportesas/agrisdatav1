from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fornecedor, FornecedorEndereco


class FornecedorEnderecoTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome='Fornecedor X')
        self.endereco = FornecedorEndereco.objects.create(
            fornecedor=self.fornecedor,
            tipo='ENTREGA',
            cep='12345000',
            logradouro='Rua Teste',
            numero='100',
            complemento='Apto 1',
            bairro='Centro',
            cidade='Cidade',
            uf='ST',
            pais='Brasil',
            padrao=True
        )

    def test_edit_address_form_prefills_values(self):
        url = reverse('cadastros:fornecedor_endereco_update', args=[self.fornecedor.pk, self.endereco.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Check that form contains existing values
        self.assertContains(resp, 'value="Rua Teste"')
        self.assertContains(resp, 'value="100"')
        self.assertContains(resp, 'value="Centro"')
        self.assertContains(resp, 'value="Cidade"')

    def test_post_update_address_saves(self):
        url = reverse('cadastros:fornecedor_endereco_update', args=[self.fornecedor.pk, self.endereco.pk])
        data = {
            'tipo': 'FATURAMENTO',
            'cep': '99999999',
            'logradouro': 'Outra Rua',
            'numero': '200',
            'complemento': 'Bloco B',
            'bairro': 'Bairro B',
            'cidade': 'Outra Cidade',
            'uf': 'OC',
            'pais': 'Brasil',
            'padrao': True,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.endereco.refresh_from_db()
        self.assertEqual(self.endereco.logradouro, 'Outra Rua')
        self.assertEqual(self.endereco.numero, '200')