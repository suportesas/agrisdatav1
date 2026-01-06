from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente, PrazoPagamentoPadrao


class ClienteSaveFlowTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='saveuser', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_login(self.user)

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
        # Post with empty cnpj for a NACIONAL client
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
        self.assertIn('vat', form.errors)
        self.assertIn('porto_destino', form.errors)

    def test_prazo_pagamento_padrao_post_saves(self):
        # create a preset and ensure assigning it via POST saves it
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

    def test_create_view_requires_inscricao_for_contribuinte_and_sets_indicador(self):
        url = reverse('cadastros:cliente_create')
        # Missing inscrição estadual while marcado como contribuinte -> form should error
        data = {
            'razao_social': 'Cli Contrib',
            'cnpj_cpf': '99999999999999',
            'tipo_cliente': 'NACIONAL',
            'tipo_pessoa': 'PJ',
            'contribuinte_icms': 'on'
        }
        resp = self.client.post(url, data)
        self.assertNotEqual(resp.status_code, 302)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        self.assertIn('inscricao_estadual', form.errors)

        # Now provide inscrição and expect success and indicador set
        data['inscricao_estadual'] = '123456'
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Cli Contrib')
        self.assertEqual(c.indicador_ie, '1')
