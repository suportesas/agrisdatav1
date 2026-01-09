from django.test import TestCase
from empresas.models import Plano, Empresa
from cadastros.models import Transportadora, Viagem

class ViagemModelTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.t = Transportadora.objects.create(empresa=self.empresa, razao_social='T1')

    def test_create_viagem_and_str(self):
        v = Viagem.objects.create(transportadora=self.t, origem='Orig', destino='Dest', data='2025-01-01', valor_frete=123.45)
        self.assertIn('Orig', str(v))
        self.assertIn('Dest', str(v))
        self.assertIn('T1', str(v))
