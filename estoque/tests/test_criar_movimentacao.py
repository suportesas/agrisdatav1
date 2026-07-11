"""
Testes para `estoque.services.criar_movimentacao` (Fase 1.1 do plano de
completar o processo venda -> exportação).

Cobre a correção do bug em que `MovimentacaoEstoque.objects.create(status='EXECUTADO')`
gravava só o registro de auditoria sem nunca debitar/creditar `Lote.quantidade_atual`
— o saldo só é atualizado por `_atualizar_estoque()`, chamado apenas por `.executar()`.
"""
import pytest
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from cadastros.models import Fazenda
from empresas.models import Empresa
from estoque.models import Armazem, Lote
from estoque.services import criar_movimentacao
from produtos.models import Categoria, Produto, UnidadeMedida
from usuarios.models import Usuario


@pytest.fixture
def setup_dados(db):
    empresa = Empresa.objects.create(
        nome='Empresa Teste CriarMovimentacao',
        cnpj='98.765.432/0001-10',
        email='criarmov@empresateste.com',
    )
    usuario = Usuario.objects.create_user(
        username='testuser_criarmov',
        email='criarmov@test.com',
        password='testpass123',
        empresa=empresa,
    )
    fazenda = Fazenda.objects.create(
        empresa=empresa, nome='Fazenda Teste', area_total=100.00, cadastrado_por=usuario,
    )
    armazem = Armazem.objects.create(
        empresa=empresa, codigo='ARMCM1', nome='Armazém Teste', tipo='PROPRIO',
        fazenda=fazenda, capacidade_kg=10000.00, cadastrado_por=usuario,
    )
    unidade = UnidadeMedida.objects.create(empresa=empresa, nome='Quilograma', sigla='KG')
    categoria = Categoria.objects.create(empresa=empresa, nome='Grãos', codigo='GRA')
    produto = Produto.objects.create(
        categoria=categoria, nome='Melão Teste', codigo='MEL001',
        unidade_medida=unidade, unidade_compra=unidade, unidade_venda=unidade,
        estoque_minimo=0, estoque_maximo=1000, estoque_atual=0,
    )
    lote = Lote.objects.create(
        empresa=empresa, produto=produto, armazem=armazem, numero_lote='LOTECM01',
        data_fabricacao=timezone.now().date(),
        data_validade=(timezone.now() + timedelta(days=30)).date(),
        quantidade_inicial=Decimal('100.000'), quantidade_atual=Decimal('100.000'),
        unidade_medida=unidade, cadastrado_por=usuario, status='DISPONIVEL',
    )
    return {
        'empresa': empresa, 'usuario': usuario, 'produto': produto, 'lote': lote,
    }


@pytest.mark.django_db
class TestCriarMovimentacao:
    def test_saida_debita_lote_e_recalcula_produto(self, setup_dados):
        lote = setup_dados['lote']
        produto = setup_dados['produto']

        criar_movimentacao(
            empresa=setup_dados['empresa'],
            tipo='SAIDA',
            origem='PEDIDO_VENDA',
            quantidade=Decimal('30.000'),
            usuario=setup_dados['usuario'],
            lote=lote,
            documento='TESTE-001',
        )

        lote.refresh_from_db()
        produto.refresh_from_db()
        assert lote.quantidade_atual == Decimal('70.000')
        assert produto.estoque_atual == Decimal('70.000')

    def test_entrada_credita_lote(self, setup_dados):
        lote = setup_dados['lote']

        criar_movimentacao(
            empresa=setup_dados['empresa'],
            tipo='ENTRADA',
            origem='DEVOLUCAO_VENDA',
            quantidade=Decimal('15.000'),
            usuario=setup_dados['usuario'],
            lote=lote,
            documento='TESTE-002',
        )

        lote.refresh_from_db()
        assert lote.quantidade_atual == Decimal('115.000')

    def test_saida_maior_que_saldo_dispara_erro_e_nao_debita(self, setup_dados):
        lote = setup_dados['lote']

        with pytest.raises(ValidationError):
            criar_movimentacao(
                empresa=setup_dados['empresa'],
                tipo='SAIDA',
                origem='PEDIDO_VENDA',
                quantidade=Decimal('999.000'),
                usuario=setup_dados['usuario'],
                lote=lote,
                documento='TESTE-003',
            )

        lote.refresh_from_db()
        assert lote.quantidade_atual == Decimal('100.000')
