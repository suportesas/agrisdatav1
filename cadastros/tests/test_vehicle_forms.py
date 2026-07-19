from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from empresas.models import Plano, Empresa
from frota.models import Vehicle

class VehicleFormTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(codigo='T', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='E', plano=self.plano)

    def test_vehicle_form_accepts_optional_fields(self):
        from frota.forms import VehicleForm
        data = {
            'tipo': 'LEVE',
            'marca': 'Test',
            'modelo': 'X',
            'renavam': 'REN-02',
            'chassis': 'CHS-02',
            'numero_motor': 'MTR-02',
            'tipo_combustivel': 'GASOLINA',
            'codigo_patrimonio': 'PAT-02',
            # Example: 6.5 L/100km -> 0.065 L/km if using L/km units
            'consumo_medio': '0.065',
            'consumo_unidade': 'L_KM'
        }
        form = VehicleForm(data=data, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)
        v = form.save()
        v.refresh_from_db()
        self.assertEqual(v.renavam, 'REN-02')
        self.assertEqual(v.chassis, 'CHS-02')
        self.assertEqual(v.numero_motor, 'MTR-02')
        self.assertEqual(v.tipo_combustivel, 'GASOLINA')
        self.assertEqual(v.codigo_patrimonio, 'PAT-02')
        self.assertEqual(str(v.consumo_medio), '6.50')
        # test tank capacity through the form
        data_with_tank = data.copy()
        data_with_tank['tank_capacity'] = '60.00'
        form2 = VehicleForm(data=data_with_tank, empresa=self.empresa)
        self.assertTrue(form2.is_valid(), form2.errors)
        v2 = form2.save()
        v2.refresh_from_db()
        self.assertEqual(str(v2.tank_capacity), '60.00')
        # estimated range = (60 / 6.5) * 100 = 923.08 km
        self.assertEqual(str(v2.estimated_range_km), '923.08')

    def test_apply_variation_requires_value(self):
        from frota.forms import VehicleForm
        data = {'tipo': 'LEVE', 'marca': 'V', 'modelo': 'Z', 'percentual_variacao': '5.00', 'tipo_variacao': 'VAL', 'aplicar_variacao_agora': True}
        form = VehicleForm(data=data, empresa=self.empresa)
        self.assertFalse(form.is_valid())
        self.assertIn('valor_atual', form.errors)

    def test_apply_variation_applies_correctly_and_creates_history(self):
        from frota.forms import VehicleForm
        data = {'tipo': 'LEVE', 'marca': 'V', 'modelo': 'Z', 'valor_atual': '100.00', 'percentual_variacao': '10.00', 'tipo_variacao': 'VAL', 'aplicar_variacao_agora': True}
        form = VehicleForm(data=data, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)
        v = form.save()
        v.refresh_from_db()
        self.assertEqual(str(v.valor_atual), '110.00')
        # check history
        from frota.models import VehicleValueHistory
        history = VehicleValueHistory.objects.filter(vehicle=v).first()
        self.assertIsNotNone(history)
        self.assertEqual(str(history.previous_value), '100.00')
        self.assertEqual(str(history.new_value), '110.00')
        self.assertEqual(str(history.percentual), '10.00')
