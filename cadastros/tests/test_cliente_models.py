from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from empresas.models import Empresa
from cadastros.models import Cliente, EnderecoCliente, ContaBancariaCliente, Porto
from cadastros.models import Vendedor


class ClienteModelTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Teste')
        # Porto necessário para importador tests
        self.porto = Porto.objects.create(empresa=self.empresa, codigo='PT01', nome='Porto Teste', pais='Brasil', cidade='Salvador')
        self.vendedor = Vendedor.objects.create(empresa=self.empresa, nome='Vendedor Teste')

    def test_codigo_gerado_por_empresa(self):
        c1 = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente A', cnpj_cpf='00.000.000/0000-01')
        c2 = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente B', cnpj_cpf='00.000.000/0000-02')
        self.assertTrue(c1.codigo.startswith('CLI-'))
        self.assertTrue(c2.codigo.startswith('CLI-'))
        self.assertNotEqual(c1.codigo, c2.codigo)

    def test_indicador_ie_regras(self):
        # PF -> indicador_ie = 9
        c_pf = Cliente(empresa=self.empresa, tipo_pessoa='PF', razao_social='Pessoa Fisica', cnpj_cpf='00000000001')
        c_pf.full_clean()
        self.assertEqual(c_pf.indicador_ie, '9')

        # PJ e nao contribuinte -> indicador_ie = 2
        c_pj = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Pessoa Juridica', cnpj_cpf='11111111111111')
        c_pj.full_clean()
        self.assertEqual(c_pj.indicador_ie, '2')

        # contribuinte_icms True exige inscricao_estadual e indicador 1
        c_sub = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Contribuinte', cnpj_cpf='22222222222222', contribuinte_icms=True)
        with self.assertRaises(ValidationError):
            c_sub.full_clean()
        c_sub.inscricao_estadual = '123456'
        c_sub.full_clean()
        self.assertEqual(c_sub.indicador_ie, '1')

    def test_importador_requires_fields(self):
        c = Cliente(empresa=self.empresa, tipo_cliente='IMPORTADOR', tipo_pessoa='PJ', razao_social='Importador', cnpj_cpf='33333333333333')
        with self.assertRaises(ValidationError):
            c.full_clean()
        c.eori = 'EORI123'
        with self.assertRaises(ValidationError):
            c.full_clean()
        c.pais = 'Brasil'
        with self.assertRaises(ValidationError):
            c.full_clean()
        c.porto_destino = self.porto
        c.full_clean()  # Now should pass

    def test_unique_cnpj_por_empresa(self):
        Cliente.objects.create(empresa=self.empresa, razao_social='Cliente 1', cnpj_cpf='44444444444444')
        with self.assertRaises(IntegrityError):
            Cliente.objects.create(empresa=self.empresa, razao_social='Cliente 2', cnpj_cpf='44444444444444')

    def test_unico_endereco_padrao(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Com Enderecos', cnpj_cpf='55555555555555')
        e1 = EnderecoCliente.objects.create(cliente=c, tipo='PRINCIPAL', cep='40000-000', logradouro='Rua A', bairro='B', cidade='C', uf='BA', padrao=True)
        e2 = EnderecoCliente.objects.create(cliente=c, tipo='FATURAMENTO', cep='40000-001', logradouro='Rua B', bairro='B', cidade='C', uf='BA', padrao=True)
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertFalse(e1.padrao)
        self.assertTrue(e2.padrao)

    def test_unica_conta_principal(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Com Contas', cnpj_cpf='66666666666666')
        b1 = ContaBancariaCliente.objects.create(cliente=c, banco='Banco A', conta='123', conta_principal=True)
        b2 = ContaBancariaCliente.objects.create(cliente=c, banco='Banco B', conta='456', conta_principal=True)
        b1.refresh_from_db(); b2.refresh_from_db()
        self.assertFalse(b1.conta_principal)
        self.assertTrue(b2.conta_principal)

    def test_create_subresources_via_views(self):
        from django.urls import reverse
        from usuarios.models import Usuario
        from django.core.files.uploadedfile import SimpleUploadedFile

        user = Usuario.objects.create_user(username='sub', password='pass')
        user.empresa = self.empresa
        user.save()
        self.client.force_login(user)

        # Create client
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente Sub', cnpj_cpf='99999999999999')

        # Add endereco
        data_end = {'tipo': 'PRINCIPAL', 'cep': '40000-000', 'logradouro': 'Rua Teste', 'numero': '10', 'bairro': 'Centro', 'cidade': 'Cidade', 'uf': 'BA', 'pais': 'Brasil', 'padrao': 'on'}
        resp = self.client.post(reverse('cadastros:cliente_endereco_create', args=[c.pk]), data_end)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(c.enderecos.count(), 1)

        # Add contato
        data_cont = {'nome': 'Contato Teste', 'telefone': '7133334444', 'email': 'contato@x.com', 'preferencial': 'on'}
        resp = self.client.post(reverse('cadastros:cliente_contato_create', args=[c.pk]), data_cont)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(c.contatos.count(), 1)

        # Add conta bancaria
        data_acc = {'banco': 'Banco Teste', 'agencia': '0001', 'conta': '12345', 'conta_digito': '6', 'conta_principal': 'on'}
        resp = self.client.post(reverse('cadastros:cliente_conta_create', args=[c.pk]), data_acc)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(c.contas_bancarias.count(), 1)

        # Add documento (upload)
        content = b"PDFTEST"
        f = SimpleUploadedFile('doc.pdf', content, content_type='application/pdf')
        data_doc = {'tipo': 'CONTRATO', 'titulo': 'Contrato Teste', 'numero_documento': 'ABC123', 'data_emissao': '2025-01-01', 'data_validade': '2030-01-01', 'gerar_alerta_vencimento': 'on', 'dias_antecedencia_alerta': '30'}
        resp = self.client.post(reverse('cadastros:cliente_documento_create', args=[c.pk]), data_doc, FILES={'arquivo': f})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(c.documentos.count(), 1)

    def test_cliente_edit_handles_missing_empresa_without_500(self):
        # Create client normally
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Orphaned', cnpj_cpf='12121212121212')
        # Simulate DB row with missing empresa (bypass ORM constraints)
        Cliente.objects.filter(pk=c.pk).update(empresa_id=None)

        # Login as user from another company
        from usuarios.models import Usuario
        user = Usuario.objects.create_user(username='other', password='pass')
        other_emp = Empresa.objects.create(nome='Other')
        user.empresa = other_emp
        user.save()
        self.client.force_login(user)

        # GET the edit view - should return 404 not 500
        from django.urls import reverse
        resp = self.client.get(reverse('cadastros:cliente_update', args=[c.pk]))
        self.assertIn(resp.status_code, (404, 302, 200))
        # If 200 or 302, ensure it did not raise RelatedObjectDoesNotExist

    def test_vendedor_can_be_selected_and_saved_via_view(self):
        # Create and login a user associated to the empresa
        from django.urls import reverse
        from usuarios.models import Usuario
        user = Usuario.objects.create_user(username='u_cli', password='pass')
        user.empresa = self.empresa
        user.save()
        self.client.force_login(user)

        data = {
            'razao_social': 'Cliente Vendedor',
            'cnpj_cpf': '77777777777777',
            'tipo_pessoa': 'PJ',
            'tipo_cliente': 'NACIONAL',
            'vendedor_responsavel': str(self.vendedor.pk),
        }
        resp = self.client.post(reverse('cadastros:cliente_create'), data)
        # Should redirect to detail view
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Cliente Vendedor')
        self.assertIsNotNone(c.vendedor_responsavel)
        self.assertEqual(c.vendedor_responsavel.pk, self.vendedor.pk)

    def test_prazo_pagamento_presets_and_selection(self):
        from django.urls import reverse
        from usuarios.models import Usuario
        # Create preset
        from .models import PrazoPagamentoPadrao
        preset = PrazoPagamentoPadrao.objects.create(empresa=self.empresa, nome='30/60/90', termos='30,60,90')

        user = Usuario.objects.create_user(username='u_prazo', password='pass')
        user.empresa = self.empresa
        user.save()
        self.client.force_login(user)

        data = {
            'razao_social': 'Cliente Prazo',
            'cnpj_cpf': '88888888888888',
            'tipo_pessoa': 'PJ',
            'tipo_cliente': 'NACIONAL',
            'prazo_pagamento_padrao': str(preset.pk),
            'prazo_pagamento': '60'
        }
        resp = self.client.post(reverse('cadastros:cliente_create'), data)
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Cliente Prazo')
        self.assertIsNotNone(c.prazo_pagamento_padrao)
        self.assertEqual(c.prazo_pagamento, 60)

    def test_endereco_get_endereco_completo(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Enderecos', cnpj_cpf='10101010101010')
        e = EnderecoCliente.objects.create(cliente=c, tipo='PRINCIPAL', cep='01001-000', logradouro='Praça da Sé', numero='1', complemento='lado ímpar', bairro='Sé', cidade='São Paulo', uf='SP')
        self.assertIn('Praça da Sé', e.get_endereco_completo())
        self.assertIn('São Paulo/SP', e.get_endereco_completo())

    def test_vendedor_filter_importador_and_nacional(self):
        # Create two vendors: interno and externo
        v_int = Vendedor.objects.create(empresa=self.empresa, nome_completo='Vendedor Int', cpf='00000000002', tipo_mercado='INTERNO')
        v_ext = Vendedor.objects.create(empresa=self.empresa, nome_completo='Vendedor Ext', cpf='00000000003', tipo_mercado='EXTERNO')

        from django.urls import reverse
        from usuarios.models import Usuario
        user = Usuario.objects.create_user(username='vtest', password='pass')
        user.empresa = self.empresa
        user.save()
        self.client.force_login(user)

        # Attempt to create IMPORTADOR with internal vendor -> should not be allowed (form invalid)
        data = {'razao_social': 'Cliente X', 'cnpj_cpf': '12121212121212', 'tipo_pessoa': 'PJ', 'tipo_cliente': 'IMPORTADOR', 'vendedor_responsavel': str(v_int.pk), 'eori': 'E123', 'pais': 'Brasil', 'porto_destino': str(self.porto.pk)}
        resp = self.client.post(reverse('cadastros:cliente_create'), data)
        self.assertNotEqual(resp.status_code, 302)

        # Now create IMPORTADOR with external vendor -> should pass
        data['vendedor_responsavel'] = str(v_ext.pk)
        resp2 = self.client.post(reverse('cadastros:cliente_create'), data)
        self.assertEqual(resp2.status_code, 302)
