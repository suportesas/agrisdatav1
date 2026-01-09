from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from empresas.models import Plano, Empresa
from django.contrib.auth import get_user_model
from cadastros.models import Transportadora

User = get_user_model()


class TransportadoraModelTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()

    def test_unique_constraint_empresa_cnpj(self):
        t1 = Transportadora.objects.create(empresa=self.empresa, razao_social='T1', cnpj='00.000.000/0000-00')
        with self.assertRaises(Exception):
            Transportadora.objects.create(empresa=self.empresa, razao_social='T2', cnpj='00.000.000/0000-00')

    def test_cnpj_validation_raises(self):
        t = Transportadora(empresa=self.empresa, razao_social='T3', cnpj='123')
        with self.assertRaises(ValidationError):
            t.clean()

    def test_str_returns_nome(self):
        t = Transportadora.objects.create(empresa=self.empresa, razao_social='Transp A', cnpj='11.111.111/1111-11')
        self.assertEqual(str(t), 'Transp A')

    def test_contribuinte_icms_requires_inscricao_and_sets_indicador(self):
        t = Transportadora(empresa=self.empresa, razao_social='T ICMS', cnpj='11.111.111/1111-22', contribuinte_icms=True)
        # missing inscricao_estadual should raise on clean()
        with self.assertRaises(Exception):
            t.clean()

        # with inscricao, should set indicador_ie to '1'
        t.inscricao_estadual = '12345'
        t.clean()
        self.assertEqual(t.indicador_ie, '1')

    def test_indicador_ie_defaults_to_2_when_not_contribuinte(self):
        t = Transportadora(empresa=self.empresa, razao_social='T ICMS No', cnpj='11.111.111/1111-33')
        t.clean()
        self.assertEqual(t.indicador_ie, '2')

    def test_tipo_conta_and_tipo_pix_choices_and_rntc_saving(self):
        t = Transportadora.objects.create(
            empresa=self.empresa,
            razao_social='T Bank',
            conta='12345-6',
            tipo_conta='CC',
            tipo_pix='CPF',
            pix_key='12345678901',
            rntc='RNTC-001'
        )
        self.assertEqual(t.tipo_conta, 'CC')
        self.assertEqual(t.tipo_pix, 'CPF')
        self.assertEqual(t.rntc, 'RNTC-001')

