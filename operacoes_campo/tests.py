from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cadastros.models import Area, Cultura, Fazenda, Safra, Talhao
from embalagem.models import OrdemEmbalagem, TipoEmbalagem
from empresas.models import Empresa
from estoque.models import Armazem, Lote, MovimentacaoEstoque
from produtos.models import Categoria, Produto, UnidadeMedida

from .models import LoteProducao


class LoteRecepcaoPackingTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.empresa = Empresa.objects.create(nome='Empresa Colheita Teste')
        self.user = User.objects.create(username='operador_campo', empresa=self.empresa, is_superuser=True)

        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda Teste', area_total=Decimal('100'))
        self.area = Area.objects.create(empresa=self.empresa, fazenda=self.fazenda, nome='Área 1', area_total=Decimal('50'))
        self.talhao = Talhao.objects.create(
            area=self.area, fazenda=self.fazenda, nome='Talhão 1', codigo='TL-01', area_hac=Decimal('10'),
        )
        self.safra = Safra.objects.create(fazenda=self.fazenda, nome='Safra 2026', ano=2026)
        self.cultura = Cultura.objects.create(empresa=self.empresa, nome='Melão')

        self.armazem = Armazem.objects.create(empresa=self.empresa, nome='Packing House', tipo='PACKING')

        self.unidade = UnidadeMedida.objects.create(nome='Quilograma', sigla='KG', tipo='PESO', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-01', nome='Frutas')
        from cadastros.models import NCM
        self.ncm = NCM.objects.create(codigo='08071900', nome='Melão')
        self.produto = Produto.objects.create(
            nome='Melão in natura',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )

        self.tipo_embalagem = TipoEmbalagem.objects.create(
            empresa=self.empresa,
            nome='Caixa 10kg Melão',
            peso_liquido_cx=Decimal('10.000'),
            peso_bruto_cx=Decimal('10.500'),
            caixas_por_pallet=80,
        )

        self.lote = LoteProducao.objects.create(
            empresa=self.empresa,
            talhao=self.talhao,
            safra=self.safra,
            cultura=self.cultura,
            peso_total_colhido_kg=Decimal('5000.000'),
            status='COLHIDO',
        )

        self.client.force_login(self.user)
        self.url = reverse('operacoes_campo:lote_recepcao', args=[self.lote.pk])

    def _post(self, **overrides):
        data = {
            'armazem_destino': self.armazem.pk,
            'produto': self.produto.pk,
            'tipo_embalagem': self.tipo_embalagem.pk,
            'quantidade_kg': '5000.000',
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_cria_lote_estoque_e_ordem_embalagem(self):
        response = self._post()
        self.assertEqual(response.status_code, 302)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, 'RECEBIDO_PACKING')

        lote_estoque = Lote.objects.get(produto=self.produto, empresa=self.empresa)
        self.assertEqual(lote_estoque.quantidade_atual, Decimal('5000.000'))
        self.assertEqual(lote_estoque.quantidade_inicial, Decimal('5000.000'))

        mov = MovimentacaoEstoque.objects.get(lote=lote_estoque)
        self.assertEqual(mov.tipo, 'ENTRADA')
        self.assertEqual(mov.origem, 'PRODUCAO')
        self.assertEqual(mov.status, 'EXECUTADO')

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, Decimal('5000.000'))

        ordem = OrdemEmbalagem.objects.get(lote_producao=self.lote)
        self.assertEqual(ordem.lote_origem_id, lote_estoque.pk)
        self.assertEqual(list(ordem.tipos_embalagem.values_list('pk', flat=True)), [self.tipo_embalagem.pk])
        self.assertTrue(ordem.numero)

    def test_exige_produto(self):
        response = self._post(produto='')
        self.assertEqual(response.status_code, 200)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, 'COLHIDO')
        self.assertFalse(Lote.objects.filter(empresa=self.empresa).exists())
        self.assertFalse(OrdemEmbalagem.objects.filter(lote_producao=self.lote).exists())

    def test_falha_nao_deixa_lote_preso(self):
        outra_empresa = Empresa.objects.create(nome='Outra Empresa')
        outro_categoria = Categoria.objects.create(empresa=outra_empresa, codigo='CAT-02', nome='Outra')
        outro_produto = Produto.objects.create(
            nome='Produto de Outra Empresa',
            categoria=outro_categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )

        response = self._post(produto=outro_produto.pk)
        self.assertEqual(response.status_code, 200)

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.status, 'COLHIDO')
        self.assertFalse(Lote.objects.filter(empresa=self.empresa).exists())
        self.assertFalse(OrdemEmbalagem.objects.filter(lote_producao=self.lote).exists())

    def test_idempotente_apos_recepcao(self):
        self._post()
        self.assertEqual(Lote.objects.filter(empresa=self.empresa).count(), 1)

        response = self._post()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lote.objects.filter(empresa=self.empresa).count(), 1)
        self.assertEqual(OrdemEmbalagem.objects.filter(lote_producao=self.lote).count(), 1)
