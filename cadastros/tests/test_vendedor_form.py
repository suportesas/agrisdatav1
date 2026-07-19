from datetime import date
from decimal import Decimal
from django.test import TestCase

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Vendedor
from cadastros.forms import VendedorForm


class VendedorFormTest(TestCase):
    """Reescrito como TestCase: a versao anterior era uma funcao solta com
    @pytest.mark.django_db, nunca coletada pelo `manage.py test`
    (descoberta baseada em unittest.TestCase) nem pelo pytest (restrito a
    tests/e2e/*.py) — esse teste nunca rodava de verdade."""

    def test_vendedor_form_renders_cnh_and_iso_dates(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=Decimal('1.00'))
        empresa = Empresa.objects.create(nome='Emp T', plano=plano)

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

        self.assertIn('cnh', form.fields)
        self.assertEqual(form['cnh'].value(), '12345678')

        # Date inputs should expose ISO format values for browser date inputs
        dn_val = form['data_nascimento'].value()
        if isinstance(dn_val, date):
            self.assertEqual(dn_val, date(1970, 6, 5))
        else:
            self.assertEqual(dn_val, '1970-06-05')

        da_val = form['data_admissao'].value()
        if isinstance(da_val, date):
            self.assertEqual(da_val, date(2013, 5, 6))
        else:
            self.assertEqual(da_val, '2013-05-06')
