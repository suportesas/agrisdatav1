from django.contrib.auth import get_user_model
from django.test import TestCase

from empresas.models import Empresa
from .models import Booking, SolicitacaoBooking


class ExportacaoModelsTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Teste')
        User = get_user_model()
        if hasattr(User.objects, 'create_user'):
            self.user = User.objects.create_user(username='testuser', password='password', empresa=self.empresa)
        else:
            self.user = User.objects.create(username='testuser', empresa=self.empresa)

    def test_create_solicitacao_booking(self):
        solicitacao = SolicitacaoBooking.objects.create(
            empresa=self.empresa,
            nome='Solicitação de Exportação',
            status='ABERTO',
        )
        self.assertEqual(str(solicitacao), 'Solicitação de Exportação (Aberto)')

    def test_booking_relaciona_solicitacao(self):
        solicitacao = SolicitacaoBooking.objects.create(
            empresa=self.empresa,
            nome='Solicitação de Exportação',
            status='ABERTO',
        )
        booking = Booking.objects.create(
            empresa=self.empresa,
            solicitacao=solicitacao,
            codigo='BKG-001',
            status='ABERTO',
        )
        self.assertEqual(booking.solicitacao, solicitacao)
        self.assertEqual(str(booking).startswith('BKG-001'), True)
