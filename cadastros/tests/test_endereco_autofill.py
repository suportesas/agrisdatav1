from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente, EnderecoCliente

class EnderecoAutofillTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.cliente = Cliente.objects.create(empresa=self.empresa, razao_social='C', cnpj_cpf='12345678901')

    @patch('requests.get')
    def test_cliente_endereco_created_with_uf_autofilled_from_cep(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'cep': '01001-000',
            'logradouro': 'Praça da Sé',
            'complemento': 'lado ímpar',
            'bairro': 'Sé',
            'localidade': 'São Paulo',
            'uf': 'SP'
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:cliente_endereco_create', args=[self.cliente.pk])
        data = {
            'tipo': 'PRINCIPAL',
            'cep': '01001-000',
            'logradouro': '',
            'numero': '',
            'complemento': '',
            'bairro': '',
            'cidade': '',
            'uf': '',
            'pais': 'Brasil',
            'padrao': 'on'
        }
        resp = self.client.post(url, data)
        # Should redirect on success
        self.assertEqual(resp.status_code, 302)
        e = EnderecoCliente.objects.filter(cliente=self.cliente).first()
        self.assertIsNotNone(e)
        self.assertEqual(e.uf, 'SP')

    def test_cliente_endereco_importador_sets_uf_ex(self):
        # If cliente is IMPORTADOR, addresses should be marked UF='EX' on save
        c = Cliente.objects.create(empresa=self.empresa, razao_social='C3', cnpj_cpf='00011122233', tipo_cliente='IMPORTADOR')
        url = reverse('cadastros:cliente_endereco_create', args=[c.pk])
        data = {
            'tipo': 'ENTREGA',
            'cep': '01001-000',
            'logradouro': 'Praça da Sé',
            'bairro': 'Sé',
            'cidade': 'São Paulo',
            'pais': 'Brasil'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        e = EnderecoCliente.objects.filter(cliente=c).first()
        self.assertIsNotNone(e)
        self.assertEqual(e.uf, 'EX')
