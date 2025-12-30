from django.test import TestCase
from empresas.models import Empresa
from cadastros.models import Fornecedor, FornecedorEndereco


class FornecedorAddressSyncTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='TestCo')

    def test_post_save_fornecedor_endereco_updates_fornecedor(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='F1')
        fe = FornecedorEndereco.objects.create(
            fornecedor=f,
            padrao=True,
            cep='11111-111',
            logradouro='Rua A',
            numero='10',
            bairro='BairroX',
            cidade='CidadeY',
            uf='SP',
            pais='Brasil'
        )
        f.refresh_from_db()
        self.assertEqual(f.cep, '11111-111')
        self.assertEqual(f.endereco, 'Rua A')
        self.assertEqual(f.numero, '10')
        self.assertEqual(f.cidade, 'CidadeY')

    def test_fornecedor_save_creates_padrao_endereco(self):
        f = Fornecedor(empresa=self.empresa, nome='F2', cep='22222-222', endereco='Av B', numero='20', cidade='D', uf='MG')
        f.save()
        fe = f.enderecos.filter(padrao=True).first()
        self.assertIsNotNone(fe)
        self.assertEqual(fe.cep, '22222-222')
        self.assertEqual(fe.logradouro, 'Av B')

    def test_deleting_padrao_promotes_other(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='F3')
        fe1 = FornecedorEndereco.objects.create(fornecedor=f, padrao=True, cep='33333-333', logradouro='R1')
        fe2 = FornecedorEndereco.objects.create(fornecedor=f, padrao=False, cep='44444-444', logradouro='R2')
        fe1.delete()
        fe2.refresh_from_db()
        self.assertTrue(fe2.padrao)
        f.refresh_from_db()
        self.assertEqual(f.cep, '44444-444')

    def test_changing_padrao_updates_fornecedor(self):
        f = Fornecedor.objects.create(empresa=self.empresa, nome='F4')
        fe1 = FornecedorEndereco.objects.create(fornecedor=f, padrao=True, cep='55555-555', logradouro='Orig')
        fe2 = FornecedorEndereco.objects.create(fornecedor=f, padrao=False, cep='66666-666', logradouro='Novo')
        # Switch padrao to fe2
        fe2.padrao = True
        fe2.save()
        fe1.refresh_from_db()
        self.assertFalse(fe1.padrao)
        f.refresh_from_db()
        self.assertEqual(f.cep, '66666-666')
        self.assertEqual(f.endereco, 'Novo')
