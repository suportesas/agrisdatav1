from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from empresas.models import Plano, Empresa
from cadastros.models import (
    FuncaoFuncionario, Funcionario, Vehicle, VehiclePlate, VehicleAssignment
)


class VehicleModelTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            codigo='PEQ', nome='Plano Teste', valor_mensal=0.0, valor_anual=0.0
        )
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=self.plano)
        self.funcao = FuncaoFuncionario.objects.create(nome='Motorista')

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

    def test_assignment_requires_cnh(self):
        # funcionario sem CNH
        f = Funcionario.objects.create(
            empresa=self.empresa, nome_completo='Joao', cpf='00000000191', funcao=self.funcao, salario=0
        )
        v = Vehicle.objects.create(empresa=self.empresa, marca='Ford', modelo='Cargo')
        a = VehicleAssignment(vehicle=v, motorista=f, data_inicio=timezone.now())
        with self.assertRaises(ValidationError):
            a.full_clean()

    def test_assignment_snapshots_plate_on_save(self):
        # funcionario com CNH válida
        validade = timezone.now().date() + timedelta(days=365)
        f = Funcionario.objects.create(
            empresa=self.empresa, nome_completo='Maria', cpf='00000000272', funcao=self.funcao, salario=0, cnh='123456789', cnh_validade=validade
        )
        v = Vehicle.objects.create(empresa=self.empresa, marca='Scania', modelo='R')
        VehiclePlate.objects.create(vehicle=v, placa='ZZZ-0000', vigencia_inicio=timezone.now().date(), atual=True)
        a = VehicleAssignment.objects.create(vehicle=v, motorista=f, data_inicio=timezone.now())
        self.assertEqual(a.placa, v.get_current_plate())
