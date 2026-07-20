from datetime import date
from decimal import Decimal
from django.test import TestCase
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Fazenda, Cultura, Area, Talhao, Safra
from cadastros.forms import SafraForm, SafraCulturaForm


class SafraCulturaFormTest(TestCase):
    def test_safra_cultura_period_validation(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=Decimal('1.00'))
        empresa = Empresa.objects.create(nome='E', plano=plano)
        cultura = Cultura.objects.create(empresa=empresa, nome='C')

        data_inicio = date(2025, 10, 1)
        data_fim = date(2025, 9, 1)

        form = SafraCulturaForm(data={'cultura': cultura.pk, 'periodo_inicio': data_inicio, 'periodo_fim': data_fim, 'status': 'PLANEJADA'}, empresa=empresa)
        self.assertFalse(form.is_valid())


class SafraFormTest(TestCase):
    def test_safra_uniqueness_validation(self):
        plano = Plano.objects.create(codigo='PEQ2', nome='P2', valor_mensal=Decimal('1.00'))
        empresa = Empresa.objects.create(nome='E2', plano=plano)
        user = Usuario.objects.create(username='u2')
        fazenda = Fazenda.objects.create(empresa=empresa, nome='F2', cnpj_cpf='11.1', area_total=Decimal('100'))

        Safra.objects.create(nome='S1', fazenda=fazenda, ano=2025)

        form = SafraForm(data={'fazenda': fazenda.pk, 'ano': 2025}, user=user)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)

    def test_safra_composite_year_normalization(self):
        plano = Plano.objects.create(codigo='PEQ3', nome='P3', valor_mensal=Decimal('1.00'))
        empresa = Empresa.objects.create(nome='E3', plano=plano)
        user = Usuario.objects.create(username='u3')
        fazenda = Fazenda.objects.create(empresa=empresa, nome='F3', cnpj_cpf='22.2', area_total=Decimal('100'))

        # User provides composite ano like 202526 directly
        form = SafraForm(data={'fazenda': fazenda.pk, 'ano': 202526}, user=user)
        self.assertTrue(form.is_valid(), form.errors)
        safra = form.save()
        self.assertEqual(safra.ano, 2025)
