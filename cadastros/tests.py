
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from cadastros.models import Fazenda, Area
from cadastros.models import Talhao, Cultura, HistoricoTalhao
from django.urls import reverse
from datetime import date
from empresas.models import Empresa, Plano
from cadastros.models import FuncaoFuncionario, Fornecedor, FornecedorEndereco, FornecedorContato, FornecedorDadoBancario

User = get_user_model()


class AreaFazendaSyncTests(TestCase):
	def setUp(self):
		# cria usuário mínimo
		self.user = User.objects.create(username='testuser')
		# cria empresa e fazenda
		self.empresa = Empresa.objects.create(nome='Empresa Teste')
		self.fazenda = Fazenda.objects.create(
			empresa=self.empresa,
			nome='Fazenda Teste',
			area_total=Decimal('100.00'),
		)

	def test_area_creation_updates_fazenda(self):
		a1 = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area 1',
			area_total=Decimal('20.00'),
			area_plantavel=Decimal('10.00'),
		)
		self.fazenda.refresh_from_db()
		self.assertEqual(self.fazenda.area_agricultavel, Decimal('10.00'))

	def test_area_update_updates_fazenda(self):
		a1 = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area 1',
			area_total=Decimal('20.00'),
			area_plantavel=Decimal('10.00'),
		)
		a1.area_plantavel = Decimal('15.00')
		a1.save()
		self.fazenda.refresh_from_db()
		self.assertEqual(self.fazenda.area_agricultavel, Decimal('15.00'))

	def test_area_delete_updates_fazenda(self):
		a1 = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area 1',
			area_total=Decimal('20.00'),
			area_plantavel=Decimal('10.00'),
		)
		a1.delete()
		self.fazenda.refresh_from_db()
		self.assertEqual(self.fazenda.area_agricultavel, Decimal('0.00'))

	def test_area_sum_validation(self):
		Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area A',
			area_total=Decimal('60.00'),
			area_plantavel=Decimal('60.00'),
		)
		from cadastros.forms import AreaForm
		form_data = {
			'fazenda': self.fazenda.id,
			'nome': 'Area B',
			'area_total': '40.00',
			'area_plantavel': '50.00'
		}
		form = AreaForm(data=form_data, user=self.user)
		self.assertFalse(form.is_valid())
		self.assertIn('area_plantavel', form.errors)


class HistoricoTalhaoTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='huser', password='pass')
		self.empresa = Empresa.objects.create(nome='Empresa H')
		self.user.empresa = self.empresa
		self.user.save()

		self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda H', area_total=Decimal('100.00'))
		self.area = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area H',
			area_total=Decimal('10.00'),
			area_plantavel=Decimal('8.00')
		)
		self.talhao = Talhao.objects.create(
			area=self.area,
			fazenda=self.fazenda,
			nome='T1',
			codigo='T001',
			area_hac=Decimal('1.00'),
			empresa=self.empresa
		)
		self.cultura = Cultura.objects.create(empresa=self.empresa, nome='Melancia')

	def test_create_historico_via_view(self):
		self.client.login(username='huser', password='pass')
		url = reverse('cadastros:historico_create', args=[self.talhao.pk])
		data = {
			'talhao': self.talhao.pk,
			'cultura': self.cultura.pk,
			'data_plantio': date.today().isoformat(),
			'producao_real': '1200.50',
			'custo_total': '500.00'
		}
		resp = self.client.post(url, data, follow=True)
		self.assertEqual(resp.status_code, 200)
		# Mensagem de sucesso deve estar presente
		messages = list(resp.context['messages'])
		self.assertTrue(any('✅ Histórico registrado' in str(m) for m in messages))
		exists = HistoricoTalhao.objects.filter(talhao=self.talhao, cultura=self.cultura).exists()
		self.assertTrue(exists)
		# Redirecionou para a página do talhão e contém o nome do talhão
		self.assertContains(resp, self.talhao.nome, status_code=200)

	def test_update_and_delete_historico(self):
		hist = HistoricoTalhao.objects.create(
			talhao=self.talhao,
			cultura=self.cultura,
			data_plantio=date.today(),
			empresa=self.empresa
		)
		self.client.login(username='huser', password='pass')
		url_edit = reverse('cadastros:historico_update', args=[hist.pk])
		resp = self.client.post(url_edit, {
			'talhao': self.talhao.pk,
			'cultura': self.cultura.pk,
			'data_plantio': date.today().isoformat(),
			'producao_real': '333.00',
			'custo_total': '0.00'
		}, follow=True)
		self.assertEqual(resp.status_code, 200)
		hist.refresh_from_db()
		self.assertEqual(hist.producao_real, Decimal('333.00'))

		url_del = reverse('cadastros:historico_delete', args=[hist.pk])
		resp = self.client.post(url_del, follow=True)
		self.assertEqual(resp.status_code, 200)
		self.assertFalse(HistoricoTalhao.objects.filter(pk=hist.pk).exists())

	def test_signal_creates_historico_on_status_change(self):
		# Ensure no historico initially
		self.assertFalse(HistoricoTalhao.objects.filter(talhao=self.talhao).exists())
		# Set cultura and change status
		self.talhao.cultura_atual = self.cultura
		self.talhao.data_plantio_atual = date.today()
		self.talhao.status = 'PLANTADO'
		self.talhao.save()

		self.assertTrue(HistoricoTalhao.objects.filter(talhao=self.talhao, data_plantio=date.today(), cultura=self.cultura).exists())

	def test_ajax_talhoes_por_fazenda(self):
		# usuário e empresa já configurados in setUp
		self.client.login(username='huser', password='pass')
		url = reverse('cadastros:ajax_talhoes_fazenda', args=[self.fazenda.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		# Deve retornar lista com pelo menos um talhão e conter campos esperados
		self.assertIsInstance(data, list)
		self.assertTrue(any(t['id'] == self.talhao.id for t in data))


class FuncaoAjaxTests(TestCase):
	def setUp(self):
		plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
		self.empresa = Empresa.objects.create(nome='E', plano=plano)
		User = get_user_model()
		self.user = User.objects.create_user(username='u', password='pass')
		self.user.empresa = self.empresa
		self.user.save()
		self.client.login(username='u', password='pass')

	def test_create_funcao_ajax_success(self):
		url = reverse('cadastros:funcao_create_ajax')
		data = {'nome': 'Tratorista', 'descricao': 'Operador', 'salario_base': '1500.00', 'ativa': 'on'}
		resp = self.client.post(url, data)
		self.assertEqual(resp.status_code, 200)
		json_data = resp.json()
		self.assertTrue(json_data.get('sucesso'))
		self.assertTrue(FuncaoFuncionario.objects.filter(nome='Tratorista').exists())

	def test_create_funcao_ajax_validation_error(self):
		url = reverse('cadastros:funcao_create_ajax')
		data = {'descricao': 'Sem nome'}
		resp = self.client.post(url, data)
		self.assertEqual(resp.status_code, 400)
		json_data = resp.json()
		self.assertFalse(json_data.get('sucesso'))
		self.assertIn('nome', json_data.get('erros', {}))


# === Tests added: Fornecedor models ===

class FornecedorModelTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()

    def test_unique_constraint_empresa_cnpj(self):
        f1 = Fornecedor.objects.create(empresa=self.empresa, nome='F1', cnpj_cpf='00.000.000/0000-00')
        with self.assertRaises(Exception):
            Fornecedor.objects.create(empresa=self.empresa, nome='F2', cnpj_cpf='00.000.000/0000-00')

    def test_get_primary_address_prefers_local_fields(self):
        f = Fornecedor.objects.create(
            empresa=self.empresa,
            nome='LocalAddr',
            cep='12345-678',
            endereco='Rua A',
            cidade='CidadeX',
            uf='SP'
        )
        addr = f.get_primary_address()
        self.assertIsNotNone(addr)
        self.assertEqual(addr['cep'], '12345-678')
        self.assertEqual(addr['logradouro'], 'Rua A')

    def test_endereco_padrao_uniqueness(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='ComEnd', cnpj_cpf='11.111.111/1111-11')
        e1 = FornecedorEndereco.objects.create(fornecedor=f, cidade='C1', uf='SP', padrao=True)
        e2 = FornecedorEndereco.objects.create(fornecedor=f, cidade='C2', uf='PR', padrao=True)
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertFalse(e1.padrao)
        self.assertTrue(e2.padrao)


# === Fornecedor views ===

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


class FornecedorViewsDiagnosticTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='diag', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='diag', password='pass')

    def test_create_view_response_contains_errors(self):
        url = reverse('cadastros:fornecedor_create')
        data = {'nome': 'Novo Fornecedor', 'cnpj_cpf': '22.222.222/2222-22', 'telefone': '1111-1111'}
        resp = self.client.post(url, data, follow=True)
        content = resp.content.decode('utf-8')
        # provide debug info if fails
        if not Fornecedor.objects.filter(nome='Novo Fornecedor').exists():
            print('RESP STATUS', resp.status_code)
            print('REDIRECT_CHAIN', resp.redirect_chain)
            print('CONTENT SNIPPET', content[:1000])
        self.assertTrue(Fornecedor.objects.filter(nome='Novo Fornecedor').exists(), 'Fornecedor was not created; see debug prints above')

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


# === Fornecedor contatos ===

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


# === Fornecedor banking ===

# === Diagnostic: form validation checks ===
class FornecedorFormValidationTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()

    def test_fornecedor_form_valid(self):
        from cadastros.forms import FornecedorForm
        data = {
            'nome': 'Novo Fornecedor',
            'cnpj_cpf': '22.222.222/2222-22',
            'telefone': '1111-1111',
            'inscricao_municipal': '12345',
            'eori': 'EORI12345',
            'classificacao_risco': 'MEDIO',
            'data_homologacao': '2025-01-01',
            'validade_homologacao': '2026-01-01',
            'prazo_pagamento_padrao': '30',
            'prazo_entrega_medio': '7',
            'observacoes': 'Observação de teste'
        }
        form = FornecedorForm(data=data, empresa=self.empresa, usuario=self.user)
        if not form.is_valid():
            self.fail(f'FornecedorForm invalid: {form.errors}')

    def test_fornecedor_contato_form_valid(self):
        from cadastros.forms import FornecedorContatoForm
        form = FornecedorContatoForm(data={'nome':'João','telefone':'1111-1111','tipo':'PRINCIPAL'})
        if not form.is_valid():
            self.fail(f'FornecedorContatoForm invalid: {form.errors}')

    def test_fornecedor_conta_form_valid(self):
        from cadastros.forms import FornecedorDadoBancarioForm
        form = FornecedorDadoBancarioForm(data={'banco':'Banco X','conta':'123','conta_digito':'5'})
        if not form.is_valid():
            self.fail(f'FornecedorDadoBancarioForm invalid: {form.errors}')

    def test_fornecedor_form_save(self):
        from cadastros.forms import FornecedorForm
        from cadastros.models import CategoriaFornecedor, SubcategoriaFornecedor
        cat = CategoriaFornecedor.objects.create(nome='Teste Cat', empresa=self.empresa)
        sub = SubcategoriaFornecedor.objects.create(categoria=cat, nome='Teste Sub')
        data = {
            'nome': 'Salvo Forn',
            'cnpj_cpf': '33.333.333/3333-33',
            'inscricao_municipal': '98765',
            'eori': 'EORI98765',
            'regime_tributario': 'SIMPLES',
            'categorias': [str(cat.pk)],
            'subcategorias': [str(sub.pk)],
            'classificacao_risco': 'BAIXO',
            'data_homologacao': '2025-02-01',
            'validade_homologacao': '2026-02-01',
            'prazo_pagamento_padrao': '45',
            'prazo_entrega_medio': '10',
            'observacoes': 'Observações no save'
        }
        form = FornecedorForm(data=data, empresa=self.empresa, usuario=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertTrue(obj.pk)
        self.assertTrue(Fornecedor.objects.filter(pk=obj.pk).exists())
        obj.refresh_from_db()
        self.assertEqual(obj.inscricao_municipal, '98765')
        self.assertEqual(obj.eori, 'EORI98765')
        self.assertTrue(obj.categorias.filter(pk=cat.pk).exists())
        self.assertTrue(obj.subcategorias.filter(pk=sub.pk).exists())
        self.assertEqual(obj.classificacao_risco, 'BAIXO')
        self.assertEqual(obj.prazo_pagamento_padrao, 45)
        self.assertEqual(obj.prazo_entrega_medio, 10)
        self.assertEqual(obj.observacoes, 'Observações no save')


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


class FornecedorDocumentoTests(TestCase):
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

    def test_document_upload(self):
        url = reverse('cadastros:fornecedor_documento_create', args=[self.fornecedor.pk])
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile('doc.pdf', b'PDFDATA', content_type='application/pdf')
        data = {
            'tipo': 'OUTROS',
            'titulo': 'Doc Teste',
            'arquivo': f,
        }
        resp = self.client.post(url, data)
        # Should redirect on success
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.fornecedor.documentos.filter(titulo='Doc Teste').exists())

    def test_document_delete(self):
        # create a document
        from cadastros.models import DocumentoFornecedor
        doc = DocumentoFornecedor.objects.create(fornecedor=self.fornecedor, tipo='OUTROS', titulo='ToDelete', arquivo='fornecedores/documentos/test.pdf')
        url = reverse('cadastros:fornecedor_documento_delete', args=[self.fornecedor.pk, doc.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(DocumentoFornecedor.objects.filter(pk=doc.pk).exists())
    def test_update_delete_bank_account(self):
        a = FornecedorDadoBancario.objects.create(fornecedor=self.fornecedor, banco='B', conta='9')
        url = reverse('cadastros:fornecedor_conta_update', args=[self.fornecedor.pk, a.pk])
        resp = self.client.post(url, {'banco': 'Bnovo', 'conta': '99'})
        self.assertEqual(resp.status_code, 302)
        a.refresh_from_db()
        self.assertEqual(a.banco, 'Bnovo')
        url = reverse('cadastros:fornecedor_conta_delete', args=[self.fornecedor.pk, a.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(FornecedorDadoBancario.objects.filter(pk=a.pk).exists())
