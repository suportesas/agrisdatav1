from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import SolicitacaoCompra, ItemSolicitacaoCompra, Cotacao, ItemCotacao, FornecedorCotacao
from cadastros.models import Fornecedor
from produtos.models import Produto, UnidadeMedida, ProdutoFornecedor

class FluxoCotacaoTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.empresa_id = 1
        self.user = User.objects.create(username='comprador', empresa_id=self.empresa_id)
        self.fornecedor = Fornecedor.objects.create(nome_fantasia='Fornecedor 1', ativa=True, empresa_id=self.empresa_id)
        self.produto = Produto.objects.create(nome='Produto Teste', empresa_id=self.empresa_id)
        self.unidade = UnidadeMedida.objects.create(sigla='UN', empresa_id=self.empresa_id)
        ProdutoFornecedor.objects.create(produto=self.produto, fornecedor=self.fornecedor)

    def test_criar_fluxo_cotacao(self):
        # Cria solicitação
        solicitacao = SolicitacaoCompra.objects.create(
            empresa_id=self.empresa_id,
            numero='SC-000001',
            solicitante=self.user,
            data_necessidade='2026-02-01',
            status='APROVADA'
        )
        item = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=self.produto,
            quantidade=10,
            unidade_medida=self.unidade,
            selecionado_para_cotar=True,
            status_item='SELECIONADO'
        )
        # Cria cotação
        cotacao = Cotacao.objects.create(
            empresa_id=self.empresa_id,
            solicitacao=solicitacao,
            comprador=self.user,
            status='EM_ANDAMENTO'
        )
        item_cot = ItemCotacao.objects.create(
            cotacao=cotacao,
            item_solicitacao=item,
            produto=self.produto,
            quantidade=10,
            unidade_medida=self.unidade
        )
        # Cria proposta do fornecedor
        proposta = FornecedorCotacao.objects.create(
            item_cotacao=item_cot,
            fornecedor=self.fornecedor,
            preco_unitario=100,
            preco_total=1000,
            prazo_entrega=5
        )
        # Atualiza status do item
        item_cot.atualizar_status()
        self.assertEqual(item_cot.status_item, 'COTADO')
        # Conclui cotação
        cotacao.concluir()
        self.assertEqual(cotacao.status, 'CONCLUIDA')
        self.assertEqual(cotacao.solicitacao.status, 'TOTALMENTE_COTADA')
