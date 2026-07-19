from django.test import TestCase

from empresas.models import Empresa, Plano
from usuarios.models import Usuario


class FornecedorFormValidationTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
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
        form = FornecedorContatoForm(data={'nome': 'João', 'telefone': '1111-1111', 'tipo': 'PRINCIPAL'})
        if not form.is_valid():
            self.fail(f'FornecedorContatoForm invalid: {form.errors}')

    def test_fornecedor_conta_form_valid(self):
        from cadastros.forms import FornecedorDadoBancarioForm
        form = FornecedorDadoBancarioForm(data={'banco': 'Banco X', 'conta': '123', 'conta_digito': '5'})
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
        self.assertTrue(obj.__class__.objects.filter(pk=obj.pk).exists())
        obj.refresh_from_db()
        self.assertEqual(obj.inscricao_municipal, '98765')
        self.assertEqual(obj.eori, 'EORI98765')
        self.assertTrue(obj.categorias.filter(pk=cat.pk).exists())
        self.assertTrue(obj.subcategorias.filter(pk=sub.pk).exists())
        self.assertEqual(obj.classificacao_risco, 'BAIXO')
        self.assertEqual(obj.prazo_pagamento_padrao, 45)
        self.assertEqual(obj.prazo_entrega_medio, 10)
        self.assertEqual(obj.observacoes, 'Observações no save')
