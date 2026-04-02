from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal
import io
from unittest.mock import patch

from .models import SolicitacaoCompra, ItemSolicitacaoCompra, Cotacao, ItemCotacao, FornecedorCotacao, RecebimentoCompra
from .nfe_parser import NFEImportError, parse_nfe_xml
from cadastros.models import Fornecedor, NCM
from empresas.models import Empresa
from produtos.models import Categoria, Produto, UnidadeMedida, ProdutoFornecedor

class FluxoCotacaoTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        self.empresa = Empresa.objects.create(nome='Empresa Fluxo Cotacao')
        self.empresa_id = self.empresa.id
        self.user = User.objects.create(username='comprador', empresa=self.empresa)
        self.fornecedor = Fornecedor.objects.create(
            nome='Fornecedor 1',
            nome_fantasia='Fornecedor 1',
            ativa=True,
            empresa=self.empresa,
        )
        self.unidade = UnidadeMedida.objects.create(nome='Unidade', sigla='UN', tipo='UNIDADE', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-TEST', nome='Categoria Teste')
        self.ncm = NCM.objects.create(codigo='12011000', nome='NCM Teste')
        self.produto = Produto.objects.create(
            nome='Produto Teste',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )
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
        self.assertEqual(item_cot.status_item, 'PARCIALMENTE_COTADO')
        # Conclui cotação
        cotacao.concluir()
        self.assertEqual(cotacao.status, 'CONCLUIDA')
        self.assertEqual(cotacao.solicitacao.status, 'TOTALMENTE_COTADA')


class NFEParserTestCase(TestCase):
        def test_parse_nfe_xml_retorna_campos_principais(self):
                xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc>
    <NFe>
        <infNFe Id="NFe35111111111111111111111111111111111111111111">
            <ide>
                <nNF>12345</nNF>
                <serie>1</serie>
                <dhEmi>2026-03-31T10:15:00-03:00</dhEmi>
            </ide>
            <emit>
                <CNPJ>12345678000199</CNPJ>
                <xNome>Fornecedor XML LTDA</xNome>
            </emit>
            <det nItem="1">
                <prod>
                    <cProd>0001</cProd>
                    <cEAN>7891234567890</cEAN>
                    <xProd>Produto Teste</xProd>
                    <qCom>10.0000</qCom>
                    <vUnCom>25.50</vUnCom>
                    <uCom>UN</uCom>
                    <NCM>12011000</NCM>
                    <CFOP>5102</CFOP>
                </prod>
            </det>
            <total>
                <ICMSTot>
                    <vNF>255.00</vNF>
                    <vFrete>10.00</vFrete>
                    <vDesc>5.00</vDesc>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
    <protNFe>
        <infProt>
            <chNFe>35111111111111111111111111111111111111111111</chNFe>
        </infProt>
    </protNFe>
</nfeProc>"""

                parsed = parse_nfe_xml(xml_content)

                self.assertEqual(parsed['nota_fiscal'], '12345')
                self.assertEqual(parsed['serie_nota'], '1')
                self.assertEqual(parsed['chave_nfe'], '35111111111111111111111111111111111111111111')
                self.assertEqual(parsed['fornecedor_nome'], 'Fornecedor XML LTDA')
                self.assertEqual(parsed['fornecedor_documento'], '12345678000199')
                self.assertEqual(parsed['data_emissao_nf'], '2026-03-31')
                self.assertEqual(parsed['valor_total_nf'], '255.00')
                self.assertEqual(len(parsed['produtos']), 1)
                self.assertEqual(parsed['produtos'][0]['codigo_fornecedor'], '0001')
                self.assertEqual(parsed['produtos'][0]['codigo_barras'], '7891234567890')
                self.assertEqual(parsed['produtos'][0]['nome'], 'Produto Teste')
                self.assertEqual(Decimal(parsed['produtos'][0]['quantidade']), Decimal('10.0000'))

        def test_parse_nfe_xml_invalido_dispara_erro(self):
                with self.assertRaises(NFEImportError):
                        parse_nfe_xml('<xml><sem-fechamento>')


# ---------------------------------------------------------------------------
# XML válido reutilizável nos testes de view
# ---------------------------------------------------------------------------
_VALID_NFE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc>
    <NFe>
        <infNFe Id="NFe35111111111111111111111111111111111111111111">
            <ide>
                <nNF>99999</nNF>
                <serie>1</serie>
                <dhEmi>2026-03-31T10:15:00-03:00</dhEmi>
            </ide>
            <emit>
                <CNPJ>12345678000199</CNPJ>
                <xNome>Fornecedor View Test</xNome>
            </emit>
            <det nItem="1">
                <prod>
                    <cProd>COD-XYZ-001</cProd>
                    <xProd>Produto View Test</xProd>
                    <qCom>5.0000</qCom>
                    <vUnCom>10.00</vUnCom>
                    <uCom>UN</uCom>
                    <NCM>12011000</NCM>
                    <CFOP>5102</CFOP>
                </prod>
            </det>
            <total>
                <ICMSTot>
                    <vNF>50.00</vNF>
                    <vFrete>0.00</vFrete>
                    <vDesc>0.00</vDesc>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
    <protNFe>
        <infProt>
            <chNFe>35111111111111111111111111111111111111111111</chNFe>
        </infProt>
    </protNFe>
</nfeProc>"""

_URL = '/compras/recebimentos/entrada-direta/'


class EntradaDiretaNFViewTestCase(TestCase):
    """Testes de view para entrada_direta_nf com importação de XML."""

    def setUp(self):
        User = get_user_model()
        # Patch call_command to skip slow NCM/CFOP CSV import signals on Empresa creation
        with patch('empresas.signals.call_command'):
            self.empresa = Empresa.objects.create(nome='Empresa Teste View')
        self.user = User.objects.create_user(
            username='comprador_view',
            password='senha123',
            empresa=self.empresa,
        )
        self.fornecedor = Fornecedor.objects.create(
            nome='Fornecedor View Test',
            nome_fantasia='Fornecedor View Test',
            cnpj_cpf='12.345.678/0001-99',
            empresa=self.empresa,
            ativa=True,
        )
        self.unidade = UnidadeMedida.objects.create(
            nome='Unidade',
            sigla='UN',
            tipo='UNIDADE',
            empresa=self.empresa,
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa,
            codigo='CAT-VIEW',
            nome='Categoria View',
        )
        self.ncm = NCM.objects.create(codigo='12011000', nome='NCM View Test')
        self.produto = Produto.objects.create(
            nome='Cola Adesiva Hotmelt',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
            codigo_barras='7891234567890',
        )
        ProdutoFornecedor.objects.create(
            produto=self.produto,
            fornecedor=self.fornecedor,
            codigo_fornecedor='COD-XYZ-001',
            preco_compra=10,
        )
        self.client.force_login(self.user)

    # ------------------------------------------------------------------
    # 1. GET com flag OFF não exibe xml_import_enabled=True
    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': False})
    def test_flag_desligada_context_xml_import_disabled(self):
        response = self.client.get(_URL)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['xml_import_enabled'])

    # ------------------------------------------------------------------
    # 2. GET com flag ON exibe xml_import_enabled=True
    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': True})
    def test_flag_habilitada_context_xml_import_enabled(self):
        response = self.client.get(_URL)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['xml_import_enabled'])

    # ------------------------------------------------------------------
    # 3. POST extract_xml com XML válido popula cache de sessão
    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': True})
    def test_extract_xml_valido_popula_sessao(self):
        xml_file = io.BytesIO(_VALID_NFE_XML.encode('utf-8'))
        xml_file.name = 'nota.xml'
        response = self.client.post(
            _URL,
            {'action': 'extract_xml', 'xml_file': xml_file},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('entrada_direta_xml_cache', self.client.session)
        cache = self.client.session['entrada_direta_xml_cache']
        self.assertEqual(cache['filename'], 'nota.xml')
        # xml_data should be populated in context
        xml_data = response.context['xml_data']
        self.assertEqual(xml_data.get('nota_fiscal'), '99999')
        # Fornecedor must have been matched by CNPJ
        self.assertEqual(xml_data.get('fornecedor_id'), self.fornecedor.pk)
        # Produto must have been matched by supplier code (cProd)
        self.assertEqual(xml_data.get('produtos')[0].get('produto_id'), self.produto.pk)

    # ------------------------------------------------------------------
    # 4. POST extract_xml com XML inválido exibe erro, não quebra

    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': True})
    def test_extract_xml_invalido_exibe_erro_sem_excecao(self):
        xml_file = io.BytesIO(b'<xml-corrompido><sem-fechamento>')
        xml_file.name = 'corrompido.xml'
        response = self.client.post(
            _URL,
            {'action': 'extract_xml', 'xml_file': xml_file},
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(
            any('Nao foi possivel' in str(m) or 'extrair' in str(m).lower() for m in messages_list),
            'Esperado mensagem de erro sobre XML inválido',
        )
        self.assertNotIn('entrada_direta_xml_cache', self.client.session)

    # ------------------------------------------------------------------
    # 5. Chave NF-e duplicada bloqueia o salvamento
    # ------------------------------------------------------------------
    def test_chave_nfe_duplicada_bloqueia_salvar(self):
        chave = '35111111111111111111111111111111111111111111'
        # Cria um recebimento com essa chave
        RecebimentoCompra.objects.create(
            empresa=self.empresa,
            fornecedor=self.fornecedor,
            numero='REC-TEST-001',
            nota_fiscal='99999',
            chave_nfe=chave,
            data_emissao_nf='2026-03-31',
            data_recebimento='2026-03-31',
            hora_recebimento='10:00:00',
            recebido_por=self.user,
            status='CONFERIDO',
            valor_total_nf='50.00',
        )
        # Tenta registrar nova entrada com a mesma chave
        response = self.client.post(_URL, {
            'fornecedor': self.fornecedor.pk,
            'nota_fiscal': '99999',
            'serie_nota': '1',
            'chave_nfe': chave,
            'data_emissao_nf': '2026-03-31',
            'data_recebimento': '2026-03-31',
            'hora_recebimento': '11:00',
            'valor_total_nf': '50.00',
            'valor_frete': '0',
            'valor_desconto': '0',
            'itens_count': '0',
        })
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context['messages'])
        self.assertTrue(
            any('chave' in str(m).lower() or 'duplicad' in str(m).lower() for m in messages_list),
            'Esperado mensagem de erro sobre chave NF-e duplicada',
        )


class PedidoGerarViewTestCase(TestCase):
    def setUp(self):
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        User = get_user_model()
        self.empresa = Empresa.objects.create(nome='Empresa Pedido Teste')
        self.user = User.objects.create_user(
            username='comprador_pedido',
            password='senha123',
            empresa=self.empresa,
        )
        self.client.force_login(self.user)

        self.fornecedor = Fornecedor.objects.create(
            nome='Fornecedor Pedido',
            nome_fantasia='Fornecedor Pedido',
            empresa=self.empresa,
            ativa=True,
        )
        self.unidade = UnidadeMedida.objects.create(nome='Unidade', sigla='UN', tipo='UNIDADE', empresa=self.empresa)
        self.categoria = Categoria.objects.create(empresa=self.empresa, codigo='CAT-PED', nome='Categoria Pedido')
        self.ncm = NCM.objects.create(codigo='22011000', nome='NCM Pedido')
        self.produto = Produto.objects.create(
            nome='Produto Pedido',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )

        self.solicitacao = SolicitacaoCompra.objects.create(
            empresa=self.empresa,
            numero='SC-TEST-PED-001',
            solicitante=self.user,
            data_necessidade='2026-04-02',
            status='APROVADA',
        )
        self.item_solicitacao = ItemSolicitacaoCompra.objects.create(
            solicitacao=self.solicitacao,
            produto=self.produto,
            quantidade=5,
            unidade_medida=self.unidade,
            selecionado_para_cotar=True,
            status_item='SELECIONADO',
        )
        self.cotacao = Cotacao.objects.create(
            empresa=self.empresa,
            solicitacao=self.solicitacao,
            comprador=self.user,
            status='EM_ANDAMENTO',
        )
        self.item_cotacao = ItemCotacao.objects.create(
            cotacao=self.cotacao,
            item_solicitacao=self.item_solicitacao,
            produto=self.produto,
            quantidade=5,
            unidade_medida=self.unidade,
        )
        FornecedorCotacao.objects.create(
            item_cotacao=self.item_cotacao,
            fornecedor=self.fornecedor,
            preco_unitario=Decimal('10.00'),
            preco_total=Decimal('50.00'),
            prazo_entrega=3,
            selecionado=False,
        )

    def test_pedido_gerar_redireciona_em_vez_de_404_quando_cotacao_nao_concluida(self):
        response = self.client.get(reverse('compras:pedido_gerar', args=[self.cotacao.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('compras:cotacao_item_comparativo', args=[self.cotacao.pk]))


# ---------------------------------------------------------------------------
# Vinculação manual de produto (pendência assistida no XML import)
# ---------------------------------------------------------------------------

_NFE_XML_SEM_PRODUTO = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc>
    <NFe>
        <infNFe Id="NFe35221111111111111111111111111111111111111111">
            <ide>
                <nNF>88888</nNF>
                <serie>1</serie>
                <dhEmi>2026-04-01T10:00:00-03:00</dhEmi>
            </ide>
            <emit>
                <CNPJ>12345678000199</CNPJ>
                <xNome>Fornecedor View Test</xNome>
            </emit>
            <det nItem="1">
                <prod>
                    <cProd>CODIGO-INEXISTENTE-9999</cProd>
                    <xProd>Produto Desconhecido XYZ</xProd>
                    <qCom>2.0000</qCom>
                    <vUnCom>5.00</vUnCom>
                    <uCom>UN</uCom>
                    <NCM>12011000</NCM>
                    <CFOP>5102</CFOP>
                </prod>
            </det>
            <total>
                <ICMSTot>
                    <vNF>10.00</vNF>
                    <vFrete>0.00</vFrete>
                    <vDesc>0.00</vDesc>
                </ICMSTot>
            </total>
        </infNFe>
    </NFe>
    <protNFe>
        <infProt>
            <chNFe>35221111111111111111111111111111111111111111</chNFe>
        </infProt>
    </protNFe>
</nfeProc>"""


class VincularProdutoTestCase(TestCase):
    """Testes para o fluxo de vinculação manual assistida na importação XML."""

    def setUp(self):
        patcher = patch('empresas.signals.call_command')
        self.addCleanup(patcher.stop)
        patcher.start()

        User = get_user_model()
        self.empresa = Empresa.objects.create(nome='Empresa Vincular Test')
        self.user = User.objects.create_user(
            username='comprador_vincular',
            password='senha123',
            empresa=self.empresa,
        )
        self.fornecedor = Fornecedor.objects.create(
            nome='Fornecedor View Test',
            nome_fantasia='Fornecedor View Test',
            cnpj_cpf='12345678000199',
            empresa=self.empresa,
            ativa=True,
        )
        self.unidade = UnidadeMedida.objects.create(
            nome='Unidade', sigla='UN', tipo='UNIDADE', empresa=self.empresa,
        )
        self.categoria = Categoria.objects.create(
            empresa=self.empresa, codigo='CAT-VIN', nome='Categoria Vincular',
        )
        self.ncm = NCM.objects.create(codigo='12011000', nome='NCM Vincular')
        self.produto = Produto.objects.create(
            nome='Produto Cadastrado',
            categoria=self.categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=self.ncm,
        )
        self.client.force_login(self.user)

    # ------------------------------------------------------------------
    # 1. Produto sem match marcado como pendente no extract_xml
    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': True})
    def test_item_sem_match_marcado_pendente(self):
        xml_file = io.BytesIO(_NFE_XML_SEM_PRODUTO.encode('utf-8'))
        xml_file.name = 'sem_produto.xml'
        response = self.client.post(
            _URL,
            {'action': 'extract_xml', 'xml_file': xml_file},
        )
        self.assertEqual(response.status_code, 200)
        xml_data = response.context['xml_data']
        item = xml_data['produtos'][0]
        self.assertIsNone(item['produto_id'])
        self.assertTrue(item['pendente'])
        self.assertEqual(xml_data['itens_pendentes'], 1)

    # ------------------------------------------------------------------
    # 2. Produto com cProd conhecido não é marcado como pendente
    # ------------------------------------------------------------------
    @override_settings(FEATURE_FLAGS={'COMPRAS_XML_IMPORT': True})
    def test_item_com_cprod_conhecido_nao_pendente(self):
        ProdutoFornecedor.objects.create(
            produto=self.produto,
            fornecedor=self.fornecedor,
            codigo_fornecedor='CODIGO-INEXISTENTE-9999',
            preco_compra=5,
        )
        xml_file = io.BytesIO(_NFE_XML_SEM_PRODUTO.encode('utf-8'))
        xml_file.name = 'com_vinculo.xml'
        response = self.client.post(
            _URL,
            {'action': 'extract_xml', 'xml_file': xml_file},
        )
        self.assertEqual(response.status_code, 200)
        xml_data = response.context['xml_data']
        item = xml_data['produtos'][0]
        self.assertEqual(item['produto_id'], self.produto.pk)
        self.assertFalse(item['pendente'])
        self.assertEqual(xml_data['itens_pendentes'], 0)

    # ------------------------------------------------------------------
    # 3. produto_busca_ajax retorna produtos da empresa
    # ------------------------------------------------------------------
    def test_produto_busca_ajax_retorna_produtos(self):
        response = self.client.get(
            reverse('compras:produto_busca_ajax'),
            {'q': 'Produto Cadastrado'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('produtos', data)
        ids = [p['id'] for p in data['produtos']]
        self.assertIn(self.produto.pk, ids)

    # ------------------------------------------------------------------
    # 4. produto_busca_ajax não retorna produtos de outra empresa
    # ------------------------------------------------------------------
    def test_produto_busca_ajax_isolamento_empresa(self):
        with patch('empresas.signals.call_command'):
            outra_empresa = Empresa.objects.create(nome='Outra Empresa')
        outra_categoria = Categoria.objects.create(
            empresa=outra_empresa, codigo='CAT-OUT', nome='Categoria Outra',
        )
        outro_ncm = NCM.objects.create(codigo='99990000', nome='NCM Outra')
        Produto.objects.create(
            nome='Produto Outra Empresa',
            categoria=outra_categoria,
            unidade_medida=self.unidade,
            unidade_compra=self.unidade,
            unidade_venda=self.unidade,
            ncm=outro_ncm,
        )
        response = self.client.get(
            reverse('compras:produto_busca_ajax'),
            {'q': 'Produto'},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        nomes = [p['nome'] for p in data['produtos']]
        self.assertNotIn('Produto Outra Empresa', nomes)
        self.assertIn('Produto Cadastrado', nomes)

    # ------------------------------------------------------------------
    # 5. salvar_vinculo_xml_ajax cria ProdutoFornecedor com codigo
    # ------------------------------------------------------------------
    def test_salvar_vinculo_cria_produto_fornecedor(self):
        import json
        response = self.client.post(
            reverse('compras:salvar_vinculo_xml_ajax'),
            data=json.dumps({
                'fornecedor_id': self.fornecedor.pk,
                'produto_id': self.produto.pk,
                'codigo_fornecedor': 'COD-NOVO-123',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertTrue(
            ProdutoFornecedor.objects.filter(
                fornecedor=self.fornecedor,
                produto=self.produto,
                codigo_fornecedor='COD-NOVO-123',
            ).exists()
        )

    # ------------------------------------------------------------------
    # 6. salvar_vinculo_xml_ajax rejeita fornecedor de outra empresa
    # ------------------------------------------------------------------
    def test_salvar_vinculo_rejeita_fornecedor_externo(self):
        import json
        with patch('empresas.signals.call_command'):
            outra_empresa = Empresa.objects.create(nome='Empresa Invasora')
        forn_externo = Fornecedor.objects.create(
            nome='Fornecedor Externo',
            nome_fantasia='Fornecedor Externo',
            empresa=outra_empresa,
            ativa=True,
        )
        response = self.client.post(
            reverse('compras:salvar_vinculo_xml_ajax'),
            data=json.dumps({
                'fornecedor_id': forn_externo.pk,
                'produto_id': self.produto.pk,
                'codigo_fornecedor': 'COD-HACK',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
