from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import NCM
from empresas.models import Empresa
from estoque.models import Armazem, Lote, MovimentacaoEstoque
from produtos.models import Categoria, Produto, UnidadeMedida

from .models import OrdemEmbalagem, PalletEmbalado, TipoEmbalagem


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
            tipo_embalagem=self.tipo_embalagem,
            lote_origem=self.lote_granel,
            quantidade_entrada_kg=Decimal('500.000'),
            armazem_destino=self.armazem,
            status='ABERTA',
            criado_por=self.user,
        )

        self.client.force_login(self.user)
        self.url = reverse('embalagem:ordem_gerar_pallets', args=[self.ordem.pk])

    def test_gera_pallets_e_lanca_entrada_estoque_produto_final(self):
        response = self.client.post(self.url)
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
        self.assertEqual(self.ordem.status, 'CONCLUIDA')

    def test_bloqueia_sem_produto_no_tipo_embalagem(self):
        self.tipo_embalagem.produto = None
        self.tipo_embalagem.save(update_fields=['produto'])

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

        self.assertFalse(PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).exists())
        self.assertFalse(Lote.objects.filter(empresa=self.empresa).exclude(pk=self.lote_granel.pk).exists())
        self.lote_granel.refresh_from_db()
        self.assertEqual(self.lote_granel.quantidade_atual, Decimal('1000.000'))
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, 'ABERTA')

    def test_idempotente_apos_gerar_pallets(self):
        self.client.post(self.url)
        self.assertEqual(Lote.objects.filter(produto=self.produto_final).count(), 1)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lote.objects.filter(produto=self.produto_final).count(), 1)
        self.assertEqual(PalletEmbalado.objects.filter(ordem_embalagem=self.ordem).count(), 5)
