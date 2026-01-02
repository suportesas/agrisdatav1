from django.test import TestCase
from django.core.exceptions import ValidationError
from empresas.models import Empresa
from cadastros.models import Cliente, EnderecoCliente


class ClienteValidatorsTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Validadora')

    def test_isento_aceito_para_nao_contribuinte(self):
        c = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Cliente Isento', cnpj_cpf='00000000000001', inscricao_estadual='ISENTO', contribuinte_icms=False)
        # Should pass validation
        c.full_clean()

    def test_isento_rejeitado_para_contribuinte(self):
        c = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Contribuinte Isento', cnpj_cpf='00000000000002', inscricao_estadual='ISENTO', contribuinte_icms=True)
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_ie_por_uf_valida_e_invalida(self):
        c = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente IE', cnpj_cpf='00000000000003', tipo_pessoa='PJ', contribuinte_icms=True)
        # Sem endereço padrão, só verifica presença (already enforced)
        c.inscricao_estadual = '123'  # short
        # If no UF info, generic regex enforces >=3 digits; here it should pass presence but format check may be lax
        with self.assertRaises(ValidationError):
            c.full_clean()

        # Criar endereço padrão em SP e testar formatos
        e = EnderecoCliente.objects.create(cliente=c, tipo='PRINCIPAL', cep='01000-000', logradouro='Rua Teste', bairro='Centro', cidade='São Paulo', uf='SP', padrao=True)
        c.inscricao_estadual = '123456789012'  # 12 dígitos (SP expected)
        c.full_clean()  # should pass

        c.inscricao_estadual = '12345'  # invalid for SP
        with self.assertRaises(ValidationError):
            c.full_clean()

    def test_exterior_skips_uf_validation(self):
        # Cliente sem Brasil: pais != 'Brasil' should skip IE/UF validation
        c = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Cliente Exterior', cnpj_cpf='77777777777777', pais='Argentina', contribuinte_icms=False)
        # With empty IE should pass
        c.inscricao_estadual = ''
        c.full_clean()

        # Even if contribuinte_icms=True, IE validation for Brazilian UF should be skipped for exterior
        c2 = Cliente(empresa=self.empresa, tipo_pessoa='PJ', razao_social='Importador Exterior', cnpj_cpf='88888888888888', pais='Chile', contribuinte_icms=True, eori='EORI123')
        c2.inscricao_estadual = ''
        c2.full_clean()

        # If address has UF='EX' it should also skip
        c3 = Cliente.objects.create(empresa=self.empresa, razao_social='Com Endereco Exterior', cnpj_cpf='99999999999999')
        from cadastros.models import EnderecoCliente
        EnderecoCliente.objects.create(cliente=c3, tipo='PRINCIPAL', cep='00000-000', logradouro='Rua Ext', bairro='B', cidade='CidadeX', uf='EX', pais='Argentina', padrao=True)
        c3.inscricao_estadual = ''
        c3.full_clean()

    def test_endereco_form_sets_uf_ex_for_foreign(self):
        from cadastros.forms import EnderecoClienteForm
        data = {
            'tipo': 'PRINCIPAL',
            'cep': '00000-000',
            'logradouro': 'Rua Ext',
            'bairro': 'B',
            'cidade': 'C',
            'uf': '',
            'pais': 'Argentina',
            'padrao': True,
        }
        form = EnderecoClienteForm(data=data)
        self.assertTrue(form.is_valid())
        cleaned = form.clean()
        self.assertEqual(cleaned.get('uf'), 'EX')
