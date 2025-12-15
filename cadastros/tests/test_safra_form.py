import pytest
from datetime import date
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Fazenda, Cultura, Area, Talhao, Safra
from cadastros.forms import SafraForm
from decimal import Decimal


@pytest.mark.django_db
def test_safra_period_validation():
    plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=Decimal('1.00'))
    empresa = Empresa.objects.create(nome='E', plano=plano)
    user = Usuario.objects.create(username='u')
    fazenda = Fazenda.objects.create(empresa=empresa, nome='F', cnpj_cpf='00.0', area_total=Decimal('100'))
    cultura = Cultura.objects.create(empresa=empresa, nome='C')

    data_inicio = date(2025, 10, 1)
    data_fim = date(2025, 9, 1)

    form = SafraForm(data={'fazenda': fazenda.pk, 'cultura': cultura.pk, 'periodo_inicio': data_inicio, 'periodo_fim': data_fim, 'ano': 2025}, user=user)
    assert not form.is_valid()
    assert 'periodo_inicio' in form.errors


@pytest.mark.django_db
def test_safra_uniqueness_validation():
    plano = Plano.objects.create(codigo='PEQ2', nome='P2', valor_mensal=Decimal('1.00'))
    empresa = Empresa.objects.create(nome='E2', plano=plano)
    user = Usuario.objects.create(username='u2')
    fazenda = Fazenda.objects.create(empresa=empresa, nome='F2', cnpj_cpf='11.1', area_total=Decimal('100'))
    cultura = Cultura.objects.create(empresa=empresa, nome='C2')

    Safra.objects.create(nome='S1', fazenda=fazenda, cultura=cultura, ano=2025)

    form = SafraForm(data={'fazenda': fazenda.pk, 'cultura': cultura.pk, 'ano': 2025}, user=user)
    assert not form.is_valid()
    assert '__all__' in form.errors or form.errors.get('__all__') is not None
