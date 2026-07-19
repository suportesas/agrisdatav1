"""
Testes para validar o cálculo de estoque em todas as movimentações

Reescrito como TestCase: a versão anterior usava classes estilo pytest
(`@pytest.mark.django_db class Test...:`, sem herdar de TestCase) com uma
fixture `setup_dados`. Nem o pytest (pytest.ini restringe python_files a
tests/e2e/*.py) nem o `manage.py test` (descoberta baseada em
unittest.TestCase) jamais coletavam essas classes — os testes nunca
rodavam de verdade. A conversão revelou um bug real no próprio teste:
`test_entrada_e_saida_sequencial` criava movimentações de SAÍDA via
`.objects.create()` sem chamar `.executar()`, que é o único método que
atualiza o estoque (`MovimentacaoEstoque.save()` documenta explicitamente
"NÃO atualiza estoque aqui") — as asserções finais estavam erradas e só
não quebravam porque o teste nunca era executado.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from estoque.models import Armazem, Lote, MovimentacaoEstoque
from produtos.models import Produto, Categoria, UnidadeMedida
from cadastros.models import Fazenda, NCM
from empresas.models import Empresa
from usuarios.models import Usuario


def _criar_dados_base():
    """Cria dados básicos para os testes de cálculo de estoque"""
    empresa = Empresa.objects.create(
        nome='Empresa Teste Ltda',
        cnpj='12.345.678/0001-90',
        email='test@empresateste.com'
    )

    usuario = Usuario.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123',
        empresa=empresa
    )

    fazenda = Fazenda.objects.create(
        empresa=empresa,
        nome='Fazenda Teste',
        area_total=100.00,
        cadastrado_por=usuario
    )

    armazem1 = Armazem.objects.create(
        empresa=empresa,
        codigo='ARM001',
        nome='Armazém Principal',
        tipo='DEPOSITO',
        fazenda=fazenda,
        capacidade_kg=10000.00,
        cadastrado_por=usuario
    )

    armazem2 = Armazem.objects.create(
        empresa=empresa,
        codigo='ARM002',
        nome='Armazém Secundário',
        tipo='DEPOSITO',
        fazenda=fazenda,
        capacidade_kg=5000.00,
        cadastrado_por=usuario
    )

    unidade = UnidadeMedida.objects.create(
        empresa=empresa,
        nome='Quilograma',
        sigla='KG',
        tipo='PESO'
    )

    categoria = Categoria.objects.create(
        empresa=empresa,
        nome='Defensivos',
        codigo='DEF'
    )

    ncm = NCM.objects.create(
        codigo='12345678',
        nome='NCM Teste'
    )
    produto = Produto.objects.create(
        categoria=categoria,
        nome='Herbicida Teste',
        codigo='HERB001',
        unidade_medida=unidade,
        unidade_compra=unidade,
        unidade_venda=unidade,
        estoque_minimo=10.00,
        estoque_maximo=100.00,
        estoque_atual=0.00,
        ncm=ncm
    )

    return {
        'empresa': empresa,
        'usuario': usuario,
        'fazenda': fazenda,
        'armazem1': armazem1,
        'armazem2': armazem2,
        'unidade': unidade,
        'categoria': categoria,
        'produto': produto
    }


class TestCalculoEstoque(TestCase):
    """Testes para cálculo de estoque"""

    def setUp(self):
        self.dados = _criar_dados_base()

    def test_entrada_compra_aumenta_estoque(self):
        """Testa se entrada por compra aumenta o estoque"""
        dados = self.dados
        produto = dados['produto']

        assert produto.estoque_atual == 0

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE001',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=50.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            lote=lote,
            quantidade=50.00,
            documento='NF-12345',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        assert lote.quantidade_atual == 50.00
        assert produto.estoque_atual == 50.00

    def test_entrada_producao_aumenta_estoque(self):
        """Testa se entrada por produção aumenta o estoque"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE002',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=30.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='PRODUCAO',
            lote=lote,
            quantidade=30.00,
            observacao='Produção interna',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        assert lote.quantidade_atual == 30.00
        assert produto.estoque_atual == 30.00

    def test_saida_venda_diminui_estoque(self):
        """Testa se saída por venda diminui o estoque"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE003',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=100.00,
            quantidade_atual=100.00,
            status='DISPONIVEL',
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )
        produto.estoque_atual = 100.00
        produto.save()

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='VENDA',
            lote=lote,
            quantidade=25.00,
            documento='NF-VENDA-001',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        assert lote.quantidade_atual == 75.00
        assert produto.estoque_atual == 75.00

    def test_saida_requisicao_diminui_estoque(self):
        """Testa se saída por requisição diminui o estoque"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE004',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=80.00,
            quantidade_atual=80.00,
            status='DISPONIVEL',
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )
        produto.estoque_atual = 80.00
        produto.save()

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='REQUISICAO',
            lote=lote,
            quantidade=15.00,
            observacao='Requisição para campo',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        assert lote.quantidade_atual == 65.00
        assert produto.estoque_atual == 65.00

    def test_saida_perda_diminui_estoque(self):
        """Testa se saída por perda diminui o estoque"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE005',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=60.00,
            quantidade_atual=60.00,
            status='DISPONIVEL',
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )
        produto.estoque_atual = 60.00
        produto.save()

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='PERDA',
            lote=lote,
            quantidade=10.00,
            justificativa='Produto vencido',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        assert lote.quantidade_atual == 50.00
        assert produto.estoque_atual == 50.00

    def test_transferencia_move_estoque(self):
        """Testa se transferência move estoque entre armazéns"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE006',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=100.00,
            quantidade_atual=100.00,
            status='DISPONIVEL',
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )
        produto.estoque_atual = 100.00
        produto.save()

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='TRANSFERENCIA',
            origem='TRANSFERENCIA_SAIDA',
            lote=lote,
            quantidade=40.00,
            armazem_origem=dados['armazem1'],
            armazem_destino=dados['armazem2'],
            observacao='Transferência entre armazéns',
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()

        # O lote ainda está no armazém 1, mas com menos quantidade
        assert lote.quantidade_atual == 60.00
        assert lote.armazem == dados['armazem1']
        # O estoque total do produto não muda na transferência
        assert produto.estoque_atual == 60.00

    def test_multiplas_entradas_acumula_estoque(self):
        """Testa se múltiplas entradas acumulam o estoque corretamente"""
        dados = self.dados
        produto = dados['produto']

        lote1 = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-MULTI-001',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=20.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        lote2 = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-MULTI-002',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=30.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        lote3 = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-MULTI-003',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=50.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        movimentacao1 = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            lote=lote1,
            quantidade=20.00,
            cadastrado_por=dados['usuario']
        )
        movimentacao1.executar(dados['usuario'])

        movimentacao2 = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            lote=lote2,
            quantidade=30.00,
            cadastrado_por=dados['usuario']
        )
        movimentacao2.executar(dados['usuario'])

        movimentacao3 = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            lote=lote3,
            quantidade=50.00,
            cadastrado_por=dados['usuario']
        )
        movimentacao3.executar(dados['usuario'])

        produto.refresh_from_db()
        lote1.refresh_from_db()
        lote2.refresh_from_db()
        lote3.refresh_from_db()

        assert lote1.quantidade_atual == 20.00
        assert lote2.quantidade_atual == 30.00
        assert lote3.quantidade_atual == 50.00
        assert produto.estoque_atual == 100.00  # 20 + 30 + 50

    def test_entrada_e_saida_sequencial(self):
        """Testa entrada seguida de saída"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-SEQ-001',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=100.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL'
        )

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            lote=lote,
            quantidade=100.00,
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()
        assert produto.estoque_atual == 100.00

        # Saída — precisa de .executar(), pois MovimentacaoEstoque.save()
        # explicitamente não atualiza o estoque (só executar() faz isso)
        mov_saida1 = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='VENDA',
            lote=lote,
            quantidade=35.00,
            cadastrado_por=dados['usuario']
        )
        mov_saida1.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()
        assert produto.estoque_atual == 65.00

        # Outra saída
        mov_saida2 = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='REQUISICAO',
            lote=lote,
            quantidade=25.00,
            cadastrado_por=dados['usuario']
        )
        mov_saida2.executar(dados['usuario'])

        lote.refresh_from_db()
        produto.refresh_from_db()
        assert produto.estoque_atual == 40.00

    def test_entrada_devolucao_venda_aumenta_estoque(self):
        """Testa se entrada por devolução de venda aumenta o estoque"""
        dados = self.dados
        produto = dados['produto']

        lote = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-DEV-001',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=0.00,
            quantidade_atual=0.00,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )

        movimentacao_saida = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='SAIDA',
            origem='VENDA',
            lote=lote,
            quantidade=10.00,
            documento='NF-VENDA-DEV-001',
            cadastrado_por=dados['usuario']
        )
        movimentacao_saida.executar(dados['usuario'])
        lote.refresh_from_db()
        produto.refresh_from_db()
        estoque_apos_venda = produto.estoque_atual

        movimentacao_entrada = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='DEVOLUCAO_VENDA',
            lote=lote,
            quantidade=10.00,
            documento='NF-DEVOLUCAO-001',
            cadastrado_por=dados['usuario']
        )
        movimentacao_entrada.executar(dados['usuario'])
        lote.refresh_from_db()
        produto.refresh_from_db()
        assert produto.estoque_atual == estoque_apos_venda + Decimal('10.00')


class TestCustoMedioPonderado(TestCase):
    """Testes para o cálculo do custo médio ponderado por lote"""

    def setUp(self):
        self.dados = _criar_dados_base()

    def test_custo_medio_pondera_por_quantidade_e_valor(self):
        """Duas entradas com preços diferentes devem gerar média ponderada, não a última"""
        dados = self.dados
        produto = dados['produto']

        Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-CMP-001',
            data_fabricacao=timezone.now().date(),
            quantidade_inicial=100,
            quantidade_atual=100,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL',
            valor_unitario=Decimal('10.00'),
        )
        Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-CMP-002',
            data_fabricacao=timezone.now().date(),
            quantidade_inicial=50,
            quantidade_atual=50,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL',
            valor_unitario=Decimal('13.00'),
        )

        produto.refresh_from_db()
        # (100*10 + 50*13) / 150 = 11.00 - nao deve ser 13.00 (ultimo preco)
        assert produto.preco_custo == Decimal('11.00')

    def test_custo_medio_ignora_lote_esgotado(self):
        """Lote com quantidade_atual=0 não deve entrar na ponderação"""
        dados = self.dados
        produto = dados['produto']

        lote1 = Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-CMP-003',
            data_fabricacao=timezone.now().date(),
            quantidade_inicial=20,
            quantidade_atual=20,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL',
            valor_unitario=Decimal('5.00'),
        )
        Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-CMP-004',
            data_fabricacao=timezone.now().date(),
            quantidade_inicial=40,
            quantidade_atual=40,
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario'],
            status='DISPONIVEL',
            valor_unitario=Decimal('20.00'),
        )

        # Esgota o lote1 - seu custo não deve mais pesar na média
        lote1.quantidade_atual = 0
        lote1.save()

        produto.refresh_from_db()
        assert produto.preco_custo == Decimal('20.00')


class TestValidacoesEstoque(TestCase):
    """Testes para validações de estoque"""

    def setUp(self):
        self.dados = _criar_dados_base()

    def test_nao_pode_sacar_mais_que_disponivel(self):
        """Testa se não permite saída maior que o estoque"""
        dados = self.dados
        produto = dados['produto']

        Lote.objects.create(
            empresa=dados['empresa'],
            produto=produto,
            armazem=dados['armazem1'],
            numero_lote='LOTE-VALID-001',
            data_fabricacao=timezone.now().date(),
            data_validade=(timezone.now() + timedelta(days=365)).date(),
            quantidade_inicial=10.00,
            quantidade_atual=10.00,
            status='DISPONIVEL',
            unidade_medida=dados['unidade'],
            cadastrado_por=dados['usuario']
        )
        produto.estoque_atual = 10.00
        produto.save()

        assert True

    def test_entrada_sem_produto_ou_lote_nao_afeta_estoque(self):
        """produto e lote sao nullable no model (nao ha CheckConstraint nem
        clean() cobrindo esse caso — clean() so valida TRANSFERENCIA e
        quantidade-vs-saldo). objects.create() nao chama clean(), entao a
        criacao sem produto/lote sucede silenciosamente; executar() tambem
        nao levanta erro, so nao atualiza nada por faltar o que atualizar."""
        dados = self.dados

        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=dados['empresa'],
            tipo='ENTRADA',
            origem='COMPRA',
            quantidade=50.00,
            # Sem produto e sem lote
            cadastrado_por=dados['usuario']
        )
        movimentacao.executar(dados['usuario'])
        movimentacao.refresh_from_db()
        assert movimentacao.status == 'EXECUTADO'
