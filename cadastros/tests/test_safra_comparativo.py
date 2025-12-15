import pytest
from decimal import Decimal
from django.utils import timezone

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Fazenda, Cultura, Area, Talhao, Safra, SafraPlan, SafraReal


@pytest.mark.django_db
def test_safra_planned_vs_real_production():
    plano = Plano.objects.create(codigo='PEQUENO', nome='P', valor_mensal=Decimal('10.00'))
    empresa = Empresa.objects.create(nome='Empresa Test', plano=plano)
    user = Usuario.objects.create(username='u', email='u@example.com')

    fazenda = Fazenda.objects.create(empresa=empresa, nome='Fazenda 1', cnpj_cpf='00.000.000/0000-00', area_total=Decimal('100'))
    cultura = Cultura.objects.create(empresa=empresa, nome='Milho')

    area = Area.objects.create(fazenda=fazenda, nome='Área 1', area_total=Decimal('10'), empresa=empresa)
    talhao1 = Talhao.objects.create(area=area, fazenda=fazenda, nome='T1', codigo='T1', area_hac=Decimal('2.5'), empresa=empresa)
    talhao2 = Talhao.objects.create(area=area, fazenda=fazenda, nome='T2', codigo='T2', area_hac=Decimal('3.0'), empresa=empresa)

    safra = Safra.objects.create(nome='Safra 2025', fazenda=fazenda, cultura=cultura, ano=2025, cadastrado_por=user)
    safra.talhoes.set([talhao1, talhao2])

    # Planejado: 50 ton
    plano_safra = SafraPlan.objects.create(safra=safra, planned_production=Decimal('50.00'))

    # Reais: talhao1 = 20, talhao2 = 25 => total 45
    SafraReal.objects.create(safra=safra, talhao=talhao1, production=Decimal('20.00'), registrado_por=user)
    SafraReal.objects.create(safra=safra, talhao=talhao2, production=Decimal('25.00'), registrado_por=user)

    assert safra.planned_production() == Decimal('50.00')
    assert safra.real_production() == Decimal('45.00')

    var = safra.production_variation_percent()
    # (45 - 50) / 50 * 100 = -10
    assert round(var, 6) == Decimal('-10') or float(round(var, 6)) == -10.0
