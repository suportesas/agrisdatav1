
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from cadastros.models import Fazenda, Area
from cadastros.models import Talhao, Cultura, HistoricoTalhao
from django.urls import reverse
from datetime import date
from empresas.models import Empresa

User = get_user_model()


class AreaFazendaSyncTests(TestCase):
	def setUp(self):
		# cria usuário mínimo
		self.user = User.objects.create(username='testuser')
		# cria empresa e fazenda
		self.empresa = Empresa.objects.create(nome='Empresa Teste')
		self.fazenda = Fazenda.objects.create(
			empresa=self.empresa,
			nome='Fazenda Teste',
			area_total=Decimal('100.00'),
		)

	def test_area_creation_updates_fazenda(self):
		a1 = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area 1',
			area_total=Decimal('20.00'),
			area_plantavel=Decimal('10.00'),
		)
		self.fazenda.refresh_from_db()
		self.assertEqual(self.fazenda.area_agricultavel, Decimal('10.00'))

	def test_area_update_updates_fazenda(self):
		a1 = Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
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
			empresa=self.empresa,
			nome='Area 1',
			area_total=Decimal('20.00'),
			area_plantavel=Decimal('10.00'),
		)
		a1.delete()
		self.fazenda.refresh_from_db()
		self.assertEqual(self.fazenda.area_agricultavel, Decimal('0.00'))

	def test_area_sum_validation(self):
		Area.objects.create(
			fazenda=self.fazenda,
			empresa=self.empresa,
			nome='Area A',
			area_total=Decimal('60.00'),
			area_plantavel=Decimal('60.00'),
		)
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


class HistoricoTalhaoTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username='huser', password='pass')
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
			'data_plantio': date.today().isoformat(),
			'producao_real': '1200.50',
			'custo_total': '500.00'
		}
		resp = self.client.post(url, data, follow=True)
		self.assertEqual(resp.status_code, 200)
		# Mensagem de sucesso deve estar presente
		messages = list(resp.context['messages'])
		self.assertTrue(any('✅ Histórico registrado' in str(m) for m in messages))
		exists = HistoricoTalhao.objects.filter(talhao=self.talhao, cultura=self.cultura).exists()
		self.assertTrue(exists)
		# Redirecionou para a página do talhão e contém o nome do talhão
		self.assertContains(resp, self.talhao.nome, status_code=200)

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
		# Ensure no historico initially
		self.assertFalse(HistoricoTalhao.objects.filter(talhao=self.talhao).exists())
		# Set cultura and change status
		self.talhao.cultura_atual = self.cultura
		self.talhao.data_plantio_atual = date.today()
		self.talhao.status = 'PLANTADO'
		self.talhao.save()

		self.assertTrue(HistoricoTalhao.objects.filter(talhao=self.talhao, data_plantio=date.today(), cultura=self.cultura).exists())

	def test_ajax_talhoes_por_fazenda(self):
		# usuário e empresa já configurados in setUp
		self.client.login(username='huser', password='pass')
		url = reverse('cadastros:ajax_talhoes_fazenda', args=[self.fazenda.pk])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		data = resp.json()
		# Deve retornar lista com pelo menos um talhão e conter campos esperados
		self.assertIsInstance(data, list)
		self.assertTrue(any(t['id'] == self.talhao.id for t in data))

