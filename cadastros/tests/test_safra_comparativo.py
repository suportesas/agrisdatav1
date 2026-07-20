from decimal import Decimal
from django.test import TestCase

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Fazenda, Cultura, Area, Talhao, Safra, SafraPlan, SafraReal


class SafraComparativoTest(TestCase):
    """Reescrito como TestCase: a versao anterior era uma funcao solta com
    @pytest.mark.django_db, que nunca era coletada nem pelo pytest (pytest.ini
    restringe python_files a tests/e2e/*.py) nem pelo `manage.py test`
    (descoberta baseada em unittest.TestCase, ignora funcoes soltas) —
    esse teste nunca rodava de verdade."""

    def test_safra_planned_vs_real_production(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='P', valor_mensal=Decimal('10.00'))
        empresa = Empresa.objects.create(nome='Empresa Test', plano=plano)
        user = Usuario.objects.create(username='u', email='u@example.com')

        fazenda = Fazenda.objects.create(empresa=empresa, nome='Fazenda 1', cnpj_cpf='00.000.000/0000-00', area_total=Decimal('100'))

        area = Area.objects.create(fazenda=fazenda, nome='Área 1', area_total=Decimal('10'), empresa=empresa)
        talhao1 = Talhao.objects.create(area=area, fazenda=fazenda, nome='T1', codigo='T1', area_hac=Decimal('2.5'), empresa=empresa)
        talhao2 = Talhao.objects.create(area=area, fazenda=fazenda, nome='T2', codigo='T2', area_hac=Decimal('3.0'), empresa=empresa)

        safra = Safra.objects.create(nome='Safra 2025', fazenda=fazenda, ano=2025, cadastrado_por=user)
        safra.talhoes.set([talhao1, talhao2])

        # Planejado: 50 ton
        SafraPlan.objects.create(safra=safra, planned_production=Decimal('50.00'))

        # Reais: talhao1 = 20, talhao2 = 25 => total 45
        SafraReal.objects.create(safra=safra, talhao=talhao1, production=Decimal('20.00'), registrado_por=user)
        SafraReal.objects.create(safra=safra, talhao=talhao2, production=Decimal('25.00'), registrado_por=user)

        self.assertEqual(safra.planned_production(), Decimal('50.00'))
        self.assertEqual(safra.real_production(), Decimal('45.00'))

        var = safra.production_variation_percent()
        # (45 - 50) / 50 * 100 = -10
        self.assertEqual(round(var, 6), Decimal('-10'))
