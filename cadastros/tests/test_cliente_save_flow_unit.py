from django.test import TestCase, Client
from django.core.exceptions import ValidationError
from django.urls import reverse

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Cliente, Moeda, PrazoPagamentoPadrao


class ClienteSaveFlowTests(TestCase):
    """Testes unitarios (Django test client) do fluxo de salvar Cliente via views.

    Nome distinto de tests/e2e/test_cliente_save_flow.py (Playwright) para
    evitar confusao - cobrem o mesmo fluxo em camadas diferentes.
    """

    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='saveuser', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='saveuser', password='pass')

    def test_edit_client_valid_post_redirect(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Orig', cnpj_cpf='11111111111111')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        data = {
            'razao_social': 'Updated',
            'cnpj_cpf': c.cnpj_cpf,
            'tipo_cliente': c.tipo_cliente,
            'tipo_pessoa': c.tipo_pessoa,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.razao_social, 'Updated')

    def test_edit_client_missing_cnpj_shows_error(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Orig', cnpj_cpf='11111111111111')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        data = {
            'razao_social': 'Updated',
            'cnpj_cpf': '',
            'tipo_cliente': 'NACIONAL',
            'tipo_pessoa': c.tipo_pessoa,
        }
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 302)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        self.assertIn('cnpj_cpf', form.errors)

    def test_edit_client_importador_requires_fields(self):
        """ClienteForm.clean() so exige eori/vat/porto ao TRANSFORMAR um
        cliente ja existente em IMPORTADOR (nao na criacao) - ver
        test_cliente_models.py:test_importador_update_to_importador_requires_vat."""
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Orig', cnpj_cpf='11111111111111')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        data = {
            'razao_social': 'Updated Importador',
            'cnpj_cpf': c.cnpj_cpf,
            'tipo_cliente': 'IMPORTADOR',
            'tipo_pessoa': c.tipo_pessoa,
            # missing eori, vat, porto_destino
        }
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 302)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        self.assertIn('eori', form.errors)

    def test_prazo_pagamento_padrao_post_saves(self):
        preset = PrazoPagamentoPadrao.objects.create(empresa=self.empresa, nome='30 dias', termos='30', ativo=True)
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Orig', cnpj_cpf='11111111111111')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        data = {
            'razao_social': 'Updated',
            'cnpj_cpf': c.cnpj_cpf,
            'tipo_cliente': c.tipo_cliente,
            'tipo_pessoa': c.tipo_pessoa,
            'prazo_pagamento_padrao': str(preset.pk),
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.prazo_pagamento_padrao, preset)

    def test_create_client_post_redirect(self):
        url = reverse('cadastros:cliente_create')
        data = {
            'razao_social': 'Cliente Novo',
            'nome_comercial': 'Comercial Novo',
            'cnpj_cpf': '12345678901',
            'tipo_cliente': 'NACIONAL',
            'tipo_pessoa': 'PJ'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Cliente.objects.filter(razao_social='Cliente Novo', empresa=self.user.empresa).exists())

    def test_create_client_with_contact_and_suframa(self):
        url = reverse('cadastros:cliente_create')
        data = {
            'razao_social': 'Cliente Contato',
            'nome_comercial': 'Comercial Contato',
            'cnpj_cpf': '12345678901',
            'tipo_cliente': 'NACIONAL',
            'tipo_pessoa': 'PJ',
            'contato_principal_nome': 'Fulano',
            'contato_principal_telefone': '11999990000',
            'contato_principal_email': 'fulano@example.com',
            'inscricao_suframa': 'SUF12345'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Cliente Contato')
        self.assertEqual(c.contato_principal_nome, 'Fulano')
        self.assertEqual(c.contato_principal_telefone, '11999990000')
        self.assertEqual(c.contato_principal_email, 'fulano@example.com')
        self.assertEqual(c.inscricao_suframa, 'SUF12345')

    def test_importador_without_eori_vat_porto_saves_with_warnings(self):
        """Importador sem EORI/VAT/Porto deve salvar e registrar avisos em observacoes_comerciais"""
        url = reverse('cadastros:cliente_create')
        data = {
            'razao_social': 'Importador Test',
            'tipo_cliente': 'IMPORTADOR',
            'tipo_pessoa': 'PJ',
            'pais': 'Estados Unidos'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Importador Test')
        self.assertIn('Avisos importador', (c.observacoes_comerciais or ''))

    def test_inscricao_estadual_validation_blocks_when_invalid(self):
        """Se contribuinte ICMS e IE invalida para UF BR, deve bloquear"""
        c = Cliente(empresa=self.empresa, tipo_cliente='NACIONAL', tipo_pessoa='PJ', razao_social='IE Fail', cnpj_cpf='12345678901234', contribuinte_icms=True, inscricao_estadual='INVALID')
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_create_moeda_ajax_validation_error(self):
        url = reverse('cadastros:moeda_create_ajax')
        resp = self.client.post(url, {'codigo': ''})
        self.assertEqual(resp.status_code, 400)
        json_data = resp.json()
        self.assertFalse(json_data.get('success'))

    def test_create_moeda_ajax_duplicate(self):
        Moeda.objects.create(codigo='EUR', nome='Euro')
        url = reverse('cadastros:moeda_create_ajax')
        resp = self.client.post(url, {'codigo': 'EUR', 'nome': 'Euro'})
        self.assertEqual(resp.status_code, 409)
        json_data = resp.json()
        self.assertFalse(json_data.get('success'))
