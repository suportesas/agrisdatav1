from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import NCM, Cliente, Transportadora
from empresas.models import Empresa
from estoque.models import Armazem, Lote, MovimentacaoEstoque
from produtos.models import Categoria, Produto, UnidadeMedida

from .models import (
    CargaFrete, CargaFreteError, ItemRomaneioVenda, OrdemEmbalagem, PalletEmbalado, RomaneioVenda,
    TipoEmbalagem,
)


class OrdemGerarPalletsTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.empresa = Empresa.objects.create(nome='Empresa Embalagem Teste')
        self.user = User.objects.create(username='operador_embalagem', empresa=self.empresa, is_superuser=True)

        self.armazem = Armazem.objects.create(empresa=self.empresa, nome='Packing House', tipo='PACKING')

        self.unidade = UnidadeMedida.objects.create(nome='Quilograma', sigla='KG', tipo='PESO', empresa=self.empresa)
        self.unidade_caixa = UnidadeMedida.objects.create(nome='Caixa', sigla='CX', tipo='UNIDADE', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-01', nome='Frutas')
        self.ncm = NCM.objects.create(codigo='08071900', nome='Melão')

        self.produto_granel = Produto.objects.create(
            nome='Melão in natura',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )
        self.produto_final = Produto.objects.create(
            nome='Melão Caixa 10kg',
            categoria=self.categoria,
            unidade_medida=self.unidade_caixa,
            unidade_compra=self.unidade_caixa,
            unidade_venda=self.unidade_caixa,
            ncm=self.ncm,
        )

        self.lote_granel = Lote.objects.create(
            empresa=self.empresa,
            produto=self.produto_granel,
            armazem=self.armazem,
            numero_lote='GRANEL-001',
            quantidade_inicial=Decimal('1000.000'),
            quantidade_atual=Decimal('1000.000'),
            unidade_medida=self.unidade,
            status='DISPONIVEL',
        )

        self.tipo_embalagem = TipoEmbalagem.objects.create(
            empresa=self.empresa,
            produto=self.produto_final,
            nome='Caixa 10kg Melão',
            peso_liquido_cx=Decimal('10.000'),
            peso_bruto_cx=Decimal('10.500'),
            caixas_por_pallet=10,
        )

        self.ordem = OrdemEmbalagem.objects.create(
            empresa=self.empresa,
            numero=OrdemEmbalagem._gerar_numero(self.empresa),
            lote_origem=self.lote_granel,
            quantidade_entrada_kg=Decimal('500.000'),
            armazem_destino=self.armazem,
            status='ABERTA',
            criado_por=self.user,
        )
        self.ordem.tipos_embalagem.set([self.tipo_embalagem])

        self.client.force_login(self.user)
        self.url = reverse('embalagem:ordem_gerar_pallets', args=[self.ordem.pk])

    def test_gera_pallets_e_lanca_entrada_estoque_produto_final(self):
        response = self.client.post(self.url, {'tipo_embalagem': self.tipo_embalagem.pk, 'n_pallets': 5})
        self.assertEqual(response.status_code, 302)

        n_pallets = PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).count()
        self.assertEqual(n_pallets, 5)  # 500kg / (10kg/cx * 10cx/pallet) = 5 pallets

        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('500.000'))

        lote_final = Lote.objects.get(produto=self.produto_final, empresa=self.empresa)
        self.assertEqual(lote_final.quantidade_atual, Decimal('50'))  # 5 pallets * 10 caixas

        mov = MovimentacaoEstoque.objects.get(lote=lote_final)
        self.assertEqual(mov.tipo, 'ENTRADA')
        self.assertEqual(mov.origem, 'PRODUCAO')
        self.assertEqual(mov.status, 'EXECUTADO')

        self.produto_final.refresh_from_db()
        self.assertEqual(self.produto_final.estoque_atual, Decimal('50'))

        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, 'EM_ANDAMENTO')

    def test_bloqueia_sem_produto_no_tipo_embalagem(self):
        self.tipo_embalagem.produto = None
        self.tipo_embalagem.save(update_fields=['produto'])

        response = self.client.post(self.url, {'tipo_embalagem': self.tipo_embalagem.pk, 'n_pallets': 5})
        self.assertEqual(response.status_code, 302)

        self.assertFalse(PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).exists())
        self.assertFalse(Lote.objects.filter(empresa=self.empresa).exclude(pk=self.lote_granel.pk).exists())
        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('1000.000'))
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, 'ABERTA')

    def test_permite_gerar_novo_lote_do_mesmo_tipo_enquanto_houver_saldo(self):
        self.client.post(self.url, {'tipo_embalagem': self.tipo_embalagem.pk, 'n_pallets': 5})
        self.assertEqual(Lote.objects.filter(produto=self.produto_final).count(), 1)

        response = self.client.post(self.url, {'tipo_embalagem': self.tipo_embalagem.pk, 'n_pallets': 5})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lote.objects.filter(produto=self.produto_final).count(), 2)
        self.assertEqual(PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).count(), 10)

        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('0.000'))

    def test_bloqueia_quando_saldo_insuficiente(self):
        response = self.client.post(self.url, {'tipo_embalagem': self.tipo_embalagem.pk, 'n_pallets': 11})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).exists())
        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('1000.000'))


class PalletMistoTestCase(TestCase):
    """Fluxo do modal de pallet misto: criar (AJAX) -> adicionar itens (AJAX) -> finalizar (AJAX),
    com baixa do granel e entrada dos produtos acabados de cada tipo usado na composição."""

    def setUp(self):
        User = get_user_model()
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.empresa = Empresa.objects.create(nome='Empresa Pallet Misto Teste')
        self.user = User.objects.create(username='operador_misto', empresa=self.empresa, is_superuser=True)

        self.armazem = Armazem.objects.create(empresa=self.empresa, nome='Packing House', tipo='PACKING')

        self.unidade = UnidadeMedida.objects.create(nome='Quilograma', sigla='KG', tipo='PESO', empresa=self.empresa)
        self.unidade_caixa = UnidadeMedida.objects.create(nome='Caixa', sigla='CX', tipo='UNIDADE', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-01', nome='Frutas')
        self.ncm = NCM.objects.create(codigo='08071900', nome='Melão')

        self.produto_granel = Produto.objects.create(
            nome='Melão in natura', categoria=self.categoria,
            unidade_medida=self.unidade, unidade_compra=self.unidade, unidade_venda=self.unidade, ncm=self.ncm,
        )
        self.produto_final_a = Produto.objects.create(
            nome='Melão Caixa 10kg', categoria=self.categoria,
            unidade_medida=self.unidade_caixa, unidade_compra=self.unidade_caixa,
            unidade_venda=self.unidade_caixa, ncm=self.ncm,
        )
        self.produto_final_b = Produto.objects.create(
            nome='Melão Caixa 5kg', categoria=self.categoria,
            unidade_medida=self.unidade_caixa, unidade_compra=self.unidade_caixa,
            unidade_venda=self.unidade_caixa, ncm=self.ncm,
        )

        self.lote_granel = Lote.objects.create(
            empresa=self.empresa, produto=self.produto_granel, armazem=self.armazem,
            numero_lote='GRANEL-MISTO-001', quantidade_inicial=Decimal('1000.000'),
            quantidade_atual=Decimal('1000.000'), unidade_medida=self.unidade, status='DISPONIVEL',
        )

        self.tipo_a = TipoEmbalagem.objects.create(
            empresa=self.empresa, produto=self.produto_final_a, nome='Caixa 10kg Melão',
            peso_liquido_cx=Decimal('10.000'), peso_bruto_cx=Decimal('10.500'), caixas_por_pallet=10,
        )
        self.tipo_b = TipoEmbalagem.objects.create(
            empresa=self.empresa, produto=self.produto_final_b, nome='Caixa 5kg Melão',
            peso_liquido_cx=Decimal('5.000'), peso_bruto_cx=Decimal('5.300'), caixas_por_pallet=20,
        )

        self.ordem = OrdemEmbalagem.objects.create(
            empresa=self.empresa, numero=OrdemEmbalagem._gerar_numero(self.empresa),
            lote_origem=self.lote_granel, quantidade_entrada_kg=Decimal('1000.000'),
            armazem_destino=self.armazem, status='ABERTA', criado_por=self.user,
        )
        self.ordem.tipos_embalagem.set([self.tipo_a, self.tipo_b])

        self.client.force_login(self.user)

    def _criar_pallet_misto(self):
        resp = self.client.post(reverse('embalagem:pallet_misto_create', args=[self.ordem.pk]))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        return data['pallet_pk']

    def test_cria_adiciona_itens_e_finaliza_com_baixa_de_estoque(self):
        pallet_pk = self._criar_pallet_misto()

        resp = self.client.post(
            reverse('embalagem:pallet_misto_add_item', args=[pallet_pk]),
            {'tipo_embalagem': self.tipo_a.pk, 'quantidade_caixas': 3},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])

        resp = self.client.post(
            reverse('embalagem:pallet_misto_add_item', args=[pallet_pk]),
            {'tipo_embalagem': self.tipo_b.pk, 'quantidade_caixas': 4},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['total_caixas'], 7)

        resp = self.client.post(
            reverse('embalagem:pallet_misto_finalizar', args=[pallet_pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])

        pallet = PalletEmbalado.objects.get(pk=pallet_pk)
        self.assertTrue(pallet.estoque_baixado)

        # 3cx*10kg (tipo A) + 4cx*5kg (tipo B) = 50kg debitados do granel
        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('950.000'))

        lote_a = Lote.objects.get(produto=self.produto_final_a, empresa=self.empresa)
        self.assertEqual(lote_a.quantidade_atual, Decimal('3'))
        lote_b = Lote.objects.get(produto=self.produto_final_b, empresa=self.empresa)
        self.assertEqual(lote_b.quantidade_atual, Decimal('4'))

        # Após finalizado, não pode mais adicionar item
        resp = self.client.post(
            reverse('embalagem:pallet_misto_add_item', args=[pallet_pk]),
            {'tipo_embalagem': self.tipo_a.pk, 'quantidade_caixas': 1},
        )
        self.assertEqual(resp.status_code, 400)

    def test_finalizar_sem_itens_retorna_erro_ajax(self):
        pallet_pk = self._criar_pallet_misto()
        resp = self.client.post(
            reverse('embalagem:pallet_misto_finalizar', args=[pallet_pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('erro', resp.json())


class CargaFreteTestCase(TestCase):
    """Rateio de frete/pedágio por caixa (método do maior resto) e ICMS de frete."""

    def setUp(self):
        User = get_user_model()
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.empresa = Empresa.objects.create(nome='Empresa Frete Teste')
        self.user = User.objects.create(username='operador_frete', empresa=self.empresa, is_superuser=True)

        self.armazem = Armazem.objects.create(empresa=self.empresa, nome='Packing House', tipo='PACKING')
        self.unidade_caixa = UnidadeMedida.objects.create(nome='Caixa', sigla='CX', tipo='UNIDADE', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-01', nome='Frutas')
        self.ncm = NCM.objects.create(codigo='08071900', nome='Melão')
        self.produto = Produto.objects.create(
            nome='Melão Caixa 10kg',
            categoria=self.categoria,
            unidade_medida=self.unidade_caixa,
            unidade_compra=self.unidade_caixa,
            unidade_venda=self.unidade_caixa,
            ncm=self.ncm,
        )
        self.tipo_embalagem = TipoEmbalagem.objects.create(
            empresa=self.empresa,
            produto=self.produto,
            nome='Caixa 10kg Melão',
            peso_liquido_cx=Decimal('10.000'),
            peso_bruto_cx=Decimal('10.500'),
            caixas_por_pallet=360,
        )
        self.lote_granel = Lote.objects.create(
            empresa=self.empresa,
            produto=self.produto,
            armazem=self.armazem,
            numero_lote='GRANEL-FRETE-001',
            quantidade_inicial=Decimal('20160.000'),
            quantidade_atual=Decimal('20160.000'),
            unidade_medida=self.unidade_caixa,
            status='DISPONIVEL',
        )
        self.ordem = OrdemEmbalagem.objects.create(
            empresa=self.empresa,
            numero=OrdemEmbalagem._gerar_numero(self.empresa),
            lote_origem=self.lote_granel,
            quantidade_entrada_kg=Decimal('20160.000'),
            armazem_destino=self.armazem,
            status='ABERTA',
            criado_por=self.user,
        )
        self.ordem.tipos_embalagem.set([self.tipo_embalagem])
        self.cliente = Cliente.objects.create(
            empresa=self.empresa, razao_social='Comprador Teste Ltda', cnpj_cpf='12345678000190',
        )
        self.transportadora = Transportadora.objects.create(empresa=self.empresa, razao_social='Transportadora Teste')

        self.carga = CargaFrete.objects.create(
            empresa=self.empresa,
            transportadora=self.transportadora,
            data_embarque='2026-07-28',
            valor_frete_total=Decimal('15000.00'),
            quantidade_caixas_total=2016,
            valor_pedagio_total=Decimal('600.00'),
        )

    def _criar_romaneio_com_caixas(self, caixas):
        rom = RomaneioVenda.objects.create(
            empresa=self.empresa,
            numero=RomaneioVenda._gerar_numero(self.empresa),
            tipo='MERCADO_INTERNO',
            cliente=self.cliente,
            carga_frete=self.carga,
        )
        pallet = PalletEmbalado.objects.create(
            empresa=self.empresa,
            codigo_pallet=f'PL-{rom.pk}',
            ordem_embalagem=self.ordem,
            tipo_embalagem=self.tipo_embalagem,
            numero_sequencial=rom.pk,
            quantidade_caixas=caixas,
            armazem=self.armazem,
        )
        ItemRomaneioVenda.objects.create(
            romaneio=rom, pallet=pallet, quantidade_caixas=caixas,
            peso_bruto_kg=Decimal('10.500') * caixas, peso_liquido_kg=Decimal('10.000') * caixas,
        )
        return rom

    def test_ratear_fecha_exato_com_metodo_maior_resto(self):
        rom_a = self._criar_romaneio_com_caixas(360)
        rom_b = self._criar_romaneio_com_caixas(1656)

        self.carga.ratear()
        rom_a.refresh_from_db()
        rom_b.refresh_from_db()

        # Reproduz o exemplo do usuário: 15000/2016 * 360 fecha em 2678.57 (não 2678.65,
        # que era o valor com erro de arredondamento do exemplo original).
        self.assertEqual(rom_a.valor_frete_rateado, Decimal('2678.57'))
        self.assertEqual(rom_b.valor_frete_rateado, Decimal('12321.43'))
        self.assertEqual(rom_a.valor_frete_rateado + rom_b.valor_frete_rateado, self.carga.valor_frete_total)

        self.assertEqual(rom_a.valor_pedagio_rateado, Decimal('107.14'))
        self.assertEqual(rom_b.valor_pedagio_rateado, Decimal('492.86'))
        self.assertEqual(rom_a.valor_pedagio_rateado + rom_b.valor_pedagio_rateado, self.carga.valor_pedagio_total)

        # ICMS com redução de 40% + alíquota de 12% (padrões copiados da carga)
        self.assertEqual(rom_a.metodo_icms_frete, 'REDUCAO')
        self.assertEqual(rom_a.valor_bc_icms_frete, Decimal('1607.14'))
        self.assertEqual(rom_a.valor_icms_frete, Decimal('192.86'))

    def test_ratear_levanta_erro_se_caixas_nao_batem_com_a_carga(self):
        self._criar_romaneio_com_caixas(360)  # só 360 de 2016 caixas vinculadas
        with self.assertRaises(CargaFreteError):
            self.carga.ratear()

    def test_calcular_icms_frete_metodo_cheio_ignora_reducao(self):
        rom = RomaneioVenda(
            metodo_icms_frete='CHEIO',
            percentual_reducao_bc=Decimal('40.00'),
            aliquota_icms_frete=Decimal('12.00'),
            valor_frete_rateado=Decimal('1000.00'),
        )
        rom.calcular_icms_frete()
        self.assertEqual(rom.valor_bc_icms_frete, Decimal('1000.00'))
        self.assertEqual(rom.valor_icms_frete, Decimal('120.00'))

    def test_gerar_cte_bloqueia_sem_rateio(self):
        rom = self._criar_romaneio_com_caixas(360)
        self.client.force_login(self.user)
        response = self.client.get(reverse('embalagem:romaneio_gerar_cte', args=[rom.pk]))
        self.assertRedirects(response, reverse('embalagem:romaneio_detail', args=[rom.pk]))

    def test_gerar_cte_redireciona_para_cte_create_apos_rateio(self):
        rom_a = self._criar_romaneio_com_caixas(360)
        self._criar_romaneio_com_caixas(1656)
        self.carga.ratear()
        rom_a.refresh_from_db()

        self.client.force_login(self.user)
        response = self.client.get(reverse('embalagem:romaneio_gerar_cte', args=[rom_a.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('faturamento:cte_create'), response.url)
        self.assertIn(f'romaneio_venda={rom_a.pk}', response.url)
