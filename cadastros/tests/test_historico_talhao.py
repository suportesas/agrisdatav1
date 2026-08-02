from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from cadastros.models import Area, Cultura, Fazenda, HistoricoTalhao, Talhao
from empresas.models import Empresa
from usuarios.models import Usuario


class HistoricoTalhaoTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='huser', password='pass')
        self.empresa = Empresa.objects.create(nome='Empresa H')
        self.user.empresa = self.empresa
        self.user.save()

        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda H', area_total=Decimal('100.00'))
        self.area = Area.objects.create(
            fazenda=self.fazenda,
            empresa=self.empresa,
            nome='Area H',
            area_total=Decimal('10.00'),
            area_plantavel=Decimal('8.00')
        )
        self.talhao = Talhao.objects.create(
            area=self.area,
            fazenda=self.fazenda,
            nome='T1',
            codigo='T001',
            area_hac=Decimal('1.00'),
            empresa=self.empresa
        )
        self.cultura = Cultura.objects.create(empresa=self.empresa, nome='Melancia')

    def test_create_historico_via_view(self):
        self.client.login(username='huser', password='pass')
        url = reverse('cadastros:historico_create', args=[self.talhao.pk])
        data = {
            'talhao': self.talhao.pk,
            'cultura': self.cultura.pk,
            'idiarn': '24.003071.318.22.0064006',
            'data_plantio': date.today().isoformat(),
            'producao_real': '1200.50',
            'custo_total': '500.00'
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        messages = list(resp.context['messages'])
        self.assertTrue(any('✅ Histórico registrado' in str(m) for m in messages))
        exists = HistoricoTalhao.objects.filter(talhao=self.talhao, cultura=self.cultura).exists()
        self.assertTrue(exists)
        self.assertContains(resp, self.talhao.nome, status_code=200)

    def test_create_historico_via_view_requires_idiarn(self):
        self.client.login(username='huser', password='pass')
        url = reverse('cadastros:historico_create', args=[self.talhao.pk])
        data = {
            'talhao': self.talhao.pk,
            'cultura': self.cultura.pk,
            'data_plantio': date.today().isoformat(),
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(HistoricoTalhao.objects.filter(talhao=self.talhao, cultura=self.cultura).exists())
        self.assertFormError(resp.context['form'], 'idiarn', 'Este campo é obrigatório.')

    def test_update_and_delete_historico(self):
        hist = HistoricoTalhao.objects.create(
            talhao=self.talhao,
            cultura=self.cultura,
            data_plantio=date.today(),
            empresa=self.empresa
        )
        self.client.login(username='huser', password='pass')
        url_edit = reverse('cadastros:historico_update', args=[hist.pk])
        resp = self.client.post(url_edit, {
            'talhao': self.talhao.pk,
            'cultura': self.cultura.pk,
            'data_plantio': date.today().isoformat(),
            'producao_real': '333.00',
            'custo_total': '0.00'
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        hist.refresh_from_db()
        self.assertEqual(hist.producao_real, Decimal('333.00'))

        url_del = reverse('cadastros:historico_delete', args=[hist.pk])
        resp = self.client.post(url_del, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(HistoricoTalhao.objects.filter(pk=hist.pk).exists())

    def test_signal_creates_historico_on_status_change(self):
        self.assertFalse(HistoricoTalhao.objects.filter(talhao=self.talhao).exists())
        self.talhao.cultura_atual = self.cultura
        self.talhao.data_plantio_atual = date.today()
        self.talhao.status = 'PLANTADO'
        self.talhao.save()

        self.assertTrue(HistoricoTalhao.objects.filter(talhao=self.talhao, data_plantio=date.today(), cultura=self.cultura).exists())

    def test_iniciar_cultivo_cria_historico_com_idiarn(self):
        historico = self.talhao.iniciar_cultivo(
            cultura=self.cultura, data_plantio=date.today(), idiarn='24.003071.318.22.0064006'
        )
        self.assertIsNotNone(historico)
        self.assertEqual(historico.idiarn, '24.003071.318.22.0064006')
        self.talhao.refresh_from_db()
        self.assertEqual(self.talhao.status, 'PLANTADO')

    def test_iniciar_cultivo_bloqueia_segundo_ciclo_aberto(self):
        self.talhao.iniciar_cultivo(cultura=self.cultura, data_plantio=date.today())
        outra_cultura = Cultura.objects.create(empresa=self.empresa, nome='Soja')
        with self.assertRaises(ValidationError):
            self.talhao.iniciar_cultivo(cultura=outra_cultura, data_plantio=date.today())

    def test_iniciar_cultivo_permite_novo_ciclo_apos_colheita(self):
        historico1 = self.talhao.iniciar_cultivo(cultura=self.cultura, data_plantio=date.today())
        historico1.data_colheita = date.today()
        historico1.save()
        self.talhao.finalizar_cultivo()

        outra_cultura = Cultura.objects.create(empresa=self.empresa, nome='Soja')
        historico2 = self.talhao.iniciar_cultivo(cultura=outra_cultura, data_plantio=date.today())
        self.assertIsNotNone(historico2)
        self.assertNotEqual(historico1.pk, historico2.pk)

    def test_ajax_talhoes_por_fazenda(self):
        self.client.login(username='huser', password='pass')
        url = reverse('cadastros:ajax_talhoes_fazenda', args=[self.fazenda.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(t['id'] == self.talhao.id for t in data))
