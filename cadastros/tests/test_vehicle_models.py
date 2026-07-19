from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from empresas.models import Plano, Empresa
from frota.models import Vehicle, VehiclePlate
from rh.models import FuncaoFuncionario


class VehicleModelTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            codigo='PEQ', nome='Plano Teste', valor_mensal=0.0, valor_anual=0.0
        )
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=self.plano)
        self.funcao = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')

    def test_plate_current_and_switch(self):
        v = Vehicle.objects.create(empresa=self.empresa, marca='VW', modelo='Delivery')
        today = timezone.now().date()
        p1 = VehiclePlate.objects.create(vehicle=v, placa='ABC-1234', vigencia_inicio=today - timedelta(days=30), atual=True)
        self.assertEqual(v.get_current_plate(), 'ABC-1234')
        p2 = VehiclePlate.objects.create(vehicle=v, placa='XYZ-9999', vigencia_inicio=today, atual=True)
        # reload plates
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertFalse(p1.atual)
        self.assertTrue(p2.atual)
        self.assertEqual(v.get_current_plate(), 'XYZ-9999')



    def test_optional_vehicle_fields_saved(self):
        # Testa se os campos opcionais do veículo são guardados corretamente
        v = Vehicle.objects.create(
            empresa=self.empresa,
            marca='Novo',
            modelo='Modelo',
            renavam='REN-001',
            chassis='CHS123456',
            numero_motor='MTR789',
            tipo_combustivel='DIESEL',
            codigo_patrimonio='PAT-0001',
            consumo_medio='8.75'
        )
        v.refresh_from_db()
        self.assertEqual(v.renavam, 'REN-001')
        self.assertEqual(v.chassis, 'CHS123456')
        self.assertEqual(v.numero_motor, 'MTR789')
        self.assertEqual(v.tipo_combustivel, 'DIESEL')
        self.assertEqual(v.codigo_patrimonio, 'PAT-0001')
        self.assertEqual(str(v.consumo_medio), '8.75')

    def test_tank_capacity_and_estimated_range(self):
        # Provide consumo in L/km (8 L/100km -> 0.08 L/km)
        v = Vehicle.objects.create(empresa=self.empresa, marca='Auto', modelo='Range', consumo_medio='0.08', tank_capacity='50.00', consumo_unidade='L_KM')
        v.refresh_from_db()
        self.assertEqual(str(v.tank_capacity), '50.00')
        # Estimated range = (tank_capacity / consumo_medio) => (50 / 0.08) = 625.00 km
        self.assertEqual(str(v.estimated_range_km), '625.00')
