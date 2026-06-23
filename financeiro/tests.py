from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import Fornecedor
from empresas.models import Empresa, Plano

from .models import ContaPagar


class ContaPagarParcelamentoAutomaticoTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(codigo='PEQ', nome='Plano Teste', valor_mensal=Decimal('1.00'))
        self.empresa = Empresa.objects.create(nome='Empresa Teste Financeiro', plano=self.plano)
        self.user = get_user_model().objects.create_user(username='financeiro', password='senha123', empresa=self.empresa)
        self.fornecedor = Fornecedor.objects.create(
            empresa=self.empresa,
            nome='Fornecedor Teste',
            cnpj_cpf='12.345.678/0001-99',
        )

    def test_criacao_de_conta_gera_parcelas_automaticamente(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('financeiro:conta_pagar_create'), {
            'numero': 'CP-TESTE-24',
            'fornecedor': self.fornecedor.pk,
            'empresa': self.empresa.pk,
            'recebimento': '',
            'data_emissao': date(2026, 1, 10),
            'valor_total': '2400.00',
            'desconto_negociado': '0.00',
            'requer_aprovacao': '',
            'conta_contabil': '',
            'centro_custo': '',
            'observacoes': 'Parcelamento de teste',
            'quantidade_parcelas': '24',
            'intervalo_dias': '30',
            'primeira_data_vencimento': date(2026, 2, 10),
        })

        self.assertEqual(response.status_code, 302)

        conta = ContaPagar.objects.get(numero='CP-TESTE-24')
        parcelas = list(conta.parcelas.order_by('numero_parcela'))

        self.assertEqual(len(parcelas), 24)
        self.assertEqual(parcelas[0].numero_parcela, 1)
        self.assertEqual(parcelas[0].data_vencimento, date(2026, 2, 10))
        self.assertEqual(parcelas[1].data_vencimento, date(2026, 3, 12))
        self.assertEqual(parcelas[-1].numero_parcela, 24)
        self.assertEqual(sum(parcela.valor_parcela for parcela in parcelas), Decimal('2400.00'))

    def test_listagem_de_parcelas_exibe_identificacao_atual_sobre_total(self):
        conta = ContaPagar.objects.create(
            empresa=self.empresa,
            fornecedor=self.fornecedor,
            numero='CP-LISTA-24',
            valor_total=Decimal('2400.00'),
            valor_ajustado=Decimal('2400.00'),
            data_emissao=date(2026, 1, 10),
            criado_por=self.user,
        )

        for indice in range(1, 25):
            status = 'PAGA' if indice <= 12 else 'ABERTA'
            conta.parcelas.create(
                numero_parcela=indice,
                valor_parcela=Decimal('100.00'),
                valor_total_parcela=Decimal('100.00'),
                data_vencimento=date(2026, 2, 10) + timedelta(days=(indice - 1) * 30),
                status=status,
            )

        self.client.force_login(self.user)
        response = self.client.get(reverse('financeiro:parcela_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1/24')
        self.assertContains(response, '12/24 pagas')
