import pytest
from datetime import date
from decimal import Decimal

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Vendedor
from cadastros.forms import VendedorForm


@pytest.mark.django_db
def test_vendedor_form_renders_cnh_and_iso_dates():
    plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=Decimal('1.00'))
    empresa = Empresa.objects.create(nome='Emp T', plano=plano)
    user = Usuario.objects.create(username='vend_t')

    # Create vendedor with dates and CNH
    v = Vendedor.objects.create(
        empresa=empresa,
        nome_completo='Teste Vendedor',
        cpf='12345678901',
        telefone_principal='(84)99999-9999',
        email_corporativo='v@t.com',
        data_nascimento=date(1970, 6, 5),
        data_admissao=date(2013, 5, 6),
        cnh='12345678'
    )

    form = VendedorForm(instance=v)

    assert 'cnh' in form.fields
    assert form['cnh'].value() == '12345678'

    # Date inputs should expose ISO format values for browser date inputs
    dn_val = form['data_nascimento'].value()
    if isinstance(dn_val, date):
        assert dn_val == date(1970, 6, 5)
    else:
        assert dn_val == '1970-06-05'

    da_val = form['data_admissao'].value()
    if isinstance(da_val, date):
        assert da_val == date(2013, 5, 6)
    else:
        assert da_val == '2013-05-06'
