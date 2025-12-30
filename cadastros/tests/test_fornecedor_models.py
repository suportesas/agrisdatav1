from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from empresas.models import Empresa, Plano
from cadastros.models import Fornecedor, FornecedorEndereco


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
        with self.assertRaises(IntegrityError):
            # Duplicate cnpj for same empresa should raise at DB level
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
        # Reload from DB
        e1.refresh_from_db()
        e2.refresh_from_db()
        self.assertFalse(e1.padrao)
        self.assertTrue(e2.padrao)
