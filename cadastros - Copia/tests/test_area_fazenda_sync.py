from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from cadastros.models import Fazenda, Area

User = get_user_model()


class AreaFazendaSyncTests(TestCase):
    def setUp(self):
        # cria usuário e empresa mínima via fixtures do projeto (assume estrutura simples)
        self.user = User.objects.create(username='testuser')
        # cria fazenda
        self.fazenda = Fazenda.objects.create(
            empresa=getattr(self.user, 'empresa', None),
            nome='Fazenda Teste',
            area_total=Decimal('100.00'),
        )

    def test_area_creation_updates_fazenda(self):
        # cria área com plantável = 10
        a1 = Area.objects.create(
            fazenda=self.fazenda,
            nome='Area 1',
            area_total=Decimal('20.00'),
            area_plantavel=Decimal('10.00'),
        )
        self.fazenda.refresh_from_db()
        self.assertEqual(self.fazenda.area_agricultavel, Decimal('10.00'))

    def test_area_update_updates_fazenda(self):
        a1 = Area.objects.create(
            fazenda=self.fazenda,
            nome='Area 1',
            area_total=Decimal('20.00'),
            area_plantavel=Decimal('10.00'),
        )
        a1.area_plantavel = Decimal('15.00')
        a1.save()
        self.fazenda.refresh_from_db()
        self.assertEqual(self.fazenda.area_agricultavel, Decimal('15.00'))

    def test_area_delete_updates_fazenda(self):
        a1 = Area.objects.create(
            fazenda=self.fazenda,
            nome='Area 1',
            area_total=Decimal('20.00'),
            area_plantavel=Decimal('10.00'),
        )
        a1.delete()
        self.fazenda.refresh_from_db()
        self.assertEqual(self.fazenda.area_agricultavel, Decimal('0.00'))

    def test_area_sum_validation(self):
        # cria uma área existente com plantável 60
        Area.objects.create(
            fazenda=self.fazenda,
            nome='Area A',
            area_total=Decimal('60.00'),
            area_plantavel=Decimal('60.00'),
        )
        # agora tenta criar nova área com plantavel 50 => soma 110 > fazenda.area_total (100)
        from cadastros.forms import AreaForm
        form_data = {
            'fazenda': self.fazenda.id,
            'nome': 'Area B',
            'area_total': '40.00',
            'area_plantavel': '50.00'
        }
        form = AreaForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('area_plantavel', form.errors)
