from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from empresas.models import Plano, Empresa
from cadastros.models import FuncaoFuncionario
from cadastros.forms import FuncionarioForm


class FuncionarioFormTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(codigo='T', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='E', plano=self.plano)
        self.funcao_motor = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')

    def test_requires_cnh_when_funcao_is_motorista(self):
        data = {
            'nome_completo': 'Joao Motorista',
            'cpf': '00000000001',
            'funcao': self.funcao_motor.pk,
            'salario': '0',
            'tipo_contrato': 'CLT'
        }
        form = FuncionarioForm(data=data, empresa=self.empresa)
        self.assertFalse(form.is_valid())
        self.assertIn('cnh', form.errors)
        self.assertIn('cnh_validade', form.errors)

    def test_accepts_valid_cnh_for_motorista(self):
        data = {
            'nome_completo': 'Maria Motorista',
            'cpf': '00000000002',
            'funcao': self.funcao_motor.pk,
            'salario': '0',
            'tipo_contrato': 'CLT',
            'cnh': 'ABC123',
            'cnh_validade': (timezone.now().date() + timedelta(days=365)).isoformat()
        }
        form = FuncionarioForm(data=data, empresa=self.empresa)
        self.assertTrue(form.is_valid())
