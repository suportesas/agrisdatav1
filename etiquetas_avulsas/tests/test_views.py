from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from empresas.models import Empresa, Plano
from etiquetas_avulsas.models import EtiquetaAvulsa, LoteEtiquetaAvulsa

User = get_user_model()


class LoteEtiquetaAvulsaViewTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
        self.user = User.objects.create_user(username='u1', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u1', password='pass')

    def test_lote_create_gera_n_etiquetas_sequenciais(self):
        url = reverse('etiquetas_avulsas:lote_create')
        resp = self.client.post(url, {
            'fazenda_texto': 'Agricola Salutaris',
            'cliente_texto': '4 Fruit Company BV',
            'produto_texto': 'Melon',
            'variedade': 'Goldex',
            'embalagem': '10 KG',
            'caixas': 98,
            'quantidade': 5,
        })
        self.assertEqual(resp.status_code, 302)
        lote = LoteEtiquetaAvulsa.objects.get(empresa=self.empresa)
        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        self.assertEqual(len(etiquetas), 5)
        self.assertEqual(etiquetas[0].caixas, 98)
        self.assertEqual(etiquetas[0].produto_texto, 'Melon')

    def test_lote_etiquetas_pdf_gera_pdf_e_marca_impressas(self):
        create_url = reverse('etiquetas_avulsas:lote_create')
        self.client.post(create_url, {
            'fazenda_texto': 'Fazenda X',
            'caixas': 10,
            'quantidade': 3,
        })
        lote = LoteEtiquetaAvulsa.objects.get(empresa=self.empresa)
        ids = list(lote.etiquetas.values_list('pk', flat=True))

        pdf_url = reverse('etiquetas_avulsas:lote_etiquetas_pdf', args=[lote.pk])
        resp = self.client.post(pdf_url, {'etiqueta_ids': ids})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertGreater(len(resp.content), 0)

        self.assertEqual(
            EtiquetaAvulsa.objects.filter(pk__in=ids, status='IMPRESSA').count(), 3)

    def test_lote_detail_isola_por_empresa(self):
        outra_empresa = Empresa.objects.create(nome='Outra', plano=self.empresa.plano)
        outro_lote = LoteEtiquetaAvulsa.objects.create(
            empresa=outra_empresa, numero_lote='LTA-2026-9999', total_pallets=1,
        )
        url = reverse('etiquetas_avulsas:lote_detail', args=[outro_lote.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_etiqueta_update_altera_so_o_pallet_editado(self):
        create_url = reverse('etiquetas_avulsas:lote_create')
        self.client.post(create_url, {
            'fazenda_texto': 'Fazenda X', 'caixas': 50, 'quantidade': 3,
        })
        lote = LoteEtiquetaAvulsa.objects.get(empresa=self.empresa)
        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        alvo = etiquetas[1]

        url = reverse('etiquetas_avulsas:etiqueta_update', args=[alvo.pk])
        resp = self.client.post(url, {'caixas': 77})
        self.assertEqual(resp.status_code, 302)

        alvo.refresh_from_db()
        self.assertEqual(alvo.caixas, 77)
        outros = EtiquetaAvulsa.objects.filter(lote=lote).exclude(pk=alvo.pk)
        self.assertTrue(all(e.caixas == 50 for e in outros))

    def test_etiqueta_cancelar_nao_pode_ser_reimpressa(self):
        create_url = reverse('etiquetas_avulsas:lote_create')
        self.client.post(create_url, {
            'fazenda_texto': 'Fazenda X', 'caixas': 10, 'quantidade': 3,
        })
        lote = LoteEtiquetaAvulsa.objects.get(empresa=self.empresa)
        etiquetas = list(lote.etiquetas.order_by('numero_sequencial'))
        cancelar = etiquetas[0]

        cancel_url = reverse('etiquetas_avulsas:etiqueta_cancelar', args=[cancelar.pk])
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 302)
        cancelar.refresh_from_db()
        self.assertEqual(cancelar.status, 'CANCELADA')
        self.assertTrue(cancelar.ativo)  # continua visível na lista, só não é mais impressa

        ids = [e.pk for e in etiquetas]
        pdf_url = reverse('etiquetas_avulsas:lote_etiquetas_pdf', args=[lote.pk])
        resp_pdf = self.client.post(pdf_url, {'etiqueta_ids': ids})
        self.assertEqual(resp_pdf.status_code, 200)

        cancelar.refresh_from_db()
        self.assertEqual(cancelar.status, 'CANCELADA')
        outros_impressos = EtiquetaAvulsa.objects.filter(
            pk__in=[e.pk for e in etiquetas if e.pk != cancelar.pk], status='IMPRESSA').count()
        self.assertEqual(outros_impressos, 2)


class LoteAdicionarConcluirViewTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQUENO', nome='Pequeno', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='Empresa Teste', plano=plano)
        self.user = User.objects.create_user(username='u2', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u2', password='pass')

        self.client.post(reverse('etiquetas_avulsas:lote_create'), {
            'fazenda_texto': 'Fazenda X', 'produto_texto': 'Melão', 'caixas': 10, 'quantidade': 5,
        })
        self.lote = LoteEtiquetaAvulsa.objects.get(empresa=self.empresa)

    def test_lote_adicionar_pallets_happy_path(self):
        url = reverse('etiquetas_avulsas:lote_adicionar_pallets', args=[self.lote.pk])
        resp = self.client.post(url, {'produto_texto': 'Melão', 'caixas': 10, 'quantidade': 3})
        self.assertEqual(resp.status_code, 302)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.total_pallets, 8)
        self.assertEqual(self.lote.etiquetas.count(), 8)

    def test_lote_adicionar_pallets_com_produto_diferente(self):
        """Uma carga pode misturar mais de um produto entre levas."""
        url = reverse('etiquetas_avulsas:lote_adicionar_pallets', args=[self.lote.pk])
        resp = self.client.post(url, {'produto_texto': 'Melancia', 'caixas': 20, 'quantidade': 2})
        self.assertEqual(resp.status_code, 302)

        nova_leva = self.lote.etiquetas.filter(produto_texto='Melancia')
        self.assertEqual(nova_leva.count(), 2)
        self.assertTrue(all(e.caixas == 20 for e in nova_leva))

    def test_lote_adicionar_pallets_rejeitado_quando_concluida(self):
        self.client.post(reverse('etiquetas_avulsas:lote_concluir', args=[self.lote.pk]))
        url = reverse('etiquetas_avulsas:lote_adicionar_pallets', args=[self.lote.pk])
        resp = self.client.post(url, {'produto_texto': 'Melão', 'caixas': 10, 'quantidade': 2})
        self.assertEqual(resp.status_code, 302)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.etiquetas.count(), 5)
        self.assertEqual(self.lote.total_pallets, 5)

    def test_lote_concluir_happy_path(self):
        url = reverse('etiquetas_avulsas:lote_concluir', args=[self.lote.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, 'CONCLUIDA')

    def test_impressao_funciona_antes_e_depois_de_concluir(self):
        ids = list(self.lote.etiquetas.values_list('pk', flat=True))
        pdf_url = reverse('etiquetas_avulsas:lote_etiquetas_pdf', args=[self.lote.pk])

        resp1 = self.client.post(pdf_url, {'etiqueta_ids': ids})
        self.assertEqual(resp1.status_code, 200)

        self.client.post(reverse('etiquetas_avulsas:lote_concluir', args=[self.lote.pk]))

        resp2 = self.client.post(pdf_url, {'etiqueta_ids': ids})
        self.assertEqual(resp2.status_code, 200)

    def test_lote_detail_botoes_conforme_status(self):
        url = reverse('etiquetas_avulsas:lote_detail', args=[self.lote.pk])
        resp_aberta = self.client.get(url)
        self.assertContains(resp_aberta, 'Concluir Carga')
        self.assertContains(resp_aberta, 'Adicionar mais pallets')

        self.client.post(reverse('etiquetas_avulsas:lote_concluir', args=[self.lote.pk]))
        resp_concluida = self.client.get(url)
        self.assertNotContains(resp_concluida, 'Concluir Carga')
        self.assertNotContains(resp_concluida, 'Adicionar mais pallets')
