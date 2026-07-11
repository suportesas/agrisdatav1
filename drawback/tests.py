from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.db.models.signals import post_save
from django.test import TestCase

from cadastros.models import NCM
from empresas.models import Empresa, Plano
from empresas import signals as empresa_signals
from produtos.models import Categoria, Produto, TipoProduto, UnidadeMedida
from usuarios.models import Usuario

from .models import AtoConcessorio, DrawbackProdutoAC
from .services import produto_do_recebimento, sugerir_vinculo_entrada, sugerir_vinculo_saida


class DrawbackServicesTestCase(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(
            codigo='PEQUENO', nome='Plano Teste', valor_mensal=Decimal('100'),
        )
        self.empresa = self._criar_empresa_sem_seeds()
        self.usuario = Usuario.objects.create(username='tester', empresa=self.empresa)

        self.unidade_kg, _ = UnidadeMedida.objects.get_or_create(
            empresa=self.empresa, sigla='KG', defaults={'nome': 'Quilograma', 'tipo': 'PESO'},
        )
        self.categoria, _ = Categoria.objects.get_or_create(
            empresa=self.empresa, codigo='GER', defaults={'nome': 'Geral', 'condiciona_campos': False},
        )
        self.tipo_produto, _ = TipoProduto.objects.get_or_create(
            empresa=self.empresa, codigo='REV', defaults={'nome': 'Revenda'},
        )
        self.ncm, _ = NCM.objects.get_or_create(codigo='48191000', defaults={'nome': 'NCM teste'})

        self.insumo = self._build_produto('Caixa de Papelão')
        self.produto_final = self._build_produto('Manga Exportação')

    def _criar_empresa_sem_seeds(self):
        receivers = [
            empresa_signals.create_default_roles,
            empresa_signals.seed_ncms_on_create,
            empresa_signals.seed_cfops_on_create,
            empresa_signals.seed_pragas_on_create,
            empresa_signals.seed_defensivos_on_create,
            empresa_signals.seed_categorias_on_create,
        ]
        for receiver in receivers:
            post_save.disconnect(receiver, sender=Empresa)
        try:
            return Empresa.objects.create(
                nome='Empresa Teste LTDA', cnpj='12.345.678/0001-99', plano=self.plano,
            )
        finally:
            for receiver in receivers:
                post_save.connect(receiver, sender=Empresa)

    def _build_produto(self, nome):
        return Produto.objects.create(
            nome=nome,
            categoria=self.categoria,
            tipo_produto=self.tipo_produto,
            ncm=self.ncm,
            unidade_medida=self.unidade_kg,
            unidade_compra=self.unidade_kg,
            unidade_venda=self.unidade_kg,
            fator_conversao=Decimal('1'),
        )

    def _criar_ac(self, numero, dias_para_vencer=365, status='ATIVO'):
        return AtoConcessorio.objects.create(
            empresa=self.empresa,
            numero_ac=numero,
            data_inicio=date.today() - timedelta(days=30),
            data_vencimento=date.today() + timedelta(days=dias_para_vencer),
            status=status,
            criado_por=self.usuario,
        )

    def _criar_produto_ac(self, ac, produto, tipo_produto, autorizado='1000'):
        return DrawbackProdutoAC.objects.create(
            ato_concessorio=ac,
            produto=produto,
            tipo_produto=tipo_produto,
            ncm=self.ncm.codigo,
            descricao_mercadoria=produto.nome,
            unidade_medida=self.unidade_kg,
            quantidade_autorizada=Decimal(autorizado),
        )

    # ── produto_do_recebimento ──────────────────────────────────────────────

    def test_produto_do_recebimento_usa_produto_direto(self):
        item = SimpleNamespace(produto_id=self.insumo.pk, produto=self.insumo, item_pedido_id=None)
        self.assertEqual(produto_do_recebimento(item), self.insumo)

    def test_produto_do_recebimento_usa_item_pedido_quando_produto_nulo(self):
        item_pedido = SimpleNamespace(produto=self.insumo)
        item = SimpleNamespace(produto_id=None, produto=None, item_pedido_id=1, item_pedido=item_pedido)
        self.assertEqual(produto_do_recebimento(item), self.insumo)

    def test_produto_do_recebimento_retorna_none_sem_referencia(self):
        item = SimpleNamespace(produto_id=None, produto=None, item_pedido_id=None)
        self.assertIsNone(produto_do_recebimento(item))

    # ── sugerir_vinculo_entrada ──────────────────────────────────────────────

    def test_sugere_ac_ativo_com_saldo(self):
        ac = self._criar_ac('23/0000001-0')
        produto_ac = self._criar_produto_ac(ac, self.insumo, 'MERCADO_INTERNO')
        item = SimpleNamespace(produto_id=self.insumo.pk, produto=self.insumo, item_pedido_id=None)

        sugestao = sugerir_vinculo_entrada(item, self.empresa)
        self.assertEqual(sugestao, produto_ac)

    def test_ignora_ac_nao_ativo(self):
        ac = self._criar_ac('23/0000002-0', status='ENCERRADO')
        self._criar_produto_ac(ac, self.insumo, 'MERCADO_INTERNO')
        item = SimpleNamespace(produto_id=self.insumo.pk, produto=self.insumo, item_pedido_id=None)

        self.assertIsNone(sugerir_vinculo_entrada(item, self.empresa))

    def test_ignora_ac_sem_saldo_disponivel(self):
        ac = self._criar_ac('23/0000003-0')
        produto_ac = self._criar_produto_ac(ac, self.insumo, 'MERCADO_INTERNO', autorizado='10')
        from .models import EntradaDrawback
        EntradaDrawback.objects.create(
            ato_concessorio=ac, drawback_produto=produto_ac,
            fornecedor=None, numero_nf='1', data_nf=date.today(),
            data_recebimento=date.today(), quantidade=Decimal('10'),
            tipo_compra='MERCADO_INTERNO', origem='MANUAL',
            registrado_por=self.usuario,
        )
        item = SimpleNamespace(produto_id=self.insumo.pk, produto=self.insumo, item_pedido_id=None)

        self.assertIsNone(sugerir_vinculo_entrada(item, self.empresa))

    def test_prioriza_ac_que_vence_mais_cedo(self):
        ac_longe = self._criar_ac('23/0000004-0', dias_para_vencer=700)
        ac_perto = self._criar_ac('23/0000005-0', dias_para_vencer=10)
        self._criar_produto_ac(ac_longe, self.insumo, 'MERCADO_INTERNO')
        produto_ac_perto = self._criar_produto_ac(ac_perto, self.insumo, 'MERCADO_INTERNO')
        item = SimpleNamespace(produto_id=self.insumo.pk, produto=self.insumo, item_pedido_id=None)

        self.assertEqual(sugerir_vinculo_entrada(item, self.empresa), produto_ac_perto)

    # ── sugerir_vinculo_saida ────────────────────────────────────────────────

    def test_sugere_ac_para_exportacao(self):
        ac = self._criar_ac('23/0000006-0')
        produto_ac = self._criar_produto_ac(ac, self.produto_final, 'EXPORTACAO')
        item_nfe = SimpleNamespace(produto_id=self.produto_final.pk)

        self.assertEqual(sugerir_vinculo_saida(item_nfe, self.empresa), produto_ac)

    def test_saida_nao_considera_produto_de_insumo(self):
        ac = self._criar_ac('23/0000007-0')
        self._criar_produto_ac(ac, self.insumo, 'MERCADO_INTERNO')
        item_nfe = SimpleNamespace(produto_id=self.insumo.pk)

        self.assertIsNone(sugerir_vinculo_saida(item_nfe, self.empresa))
