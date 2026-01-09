from django.test import TestCase
from empresas.models import Plano, Empresa
from cadastros.forms import TransportadoraForm


class TransportadoraFormTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)

    def test_form_valid_minimal(self):
        data = {
            'razao_social': 'Transportadora X',
            'cnpj': '11.111.111/1111-11',
            'frete_padrao': '100.00',
            'ativa': True
        }
        form = TransportadoraForm(data=data, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)
        t = form.save()
        self.assertEqual(t.empresa, self.empresa)
