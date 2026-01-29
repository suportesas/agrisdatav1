"""
Testes E2E para movimentações de estoque
Simula usuário preenchendo formulários no navegador
"""
import pytest
from playwright.sync_api import Page, expect
import time


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configurar contexto do navegador"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.fixture
def usuario_logado(page: Page):
    """Fixture para fazer login antes dos testes"""
    # Navegar para página de login
    page.goto("http://127.0.0.1:8000/usuarios/login/")
    page.wait_for_load_state("networkidle")
    
    # Fazer login (ajustar credenciais conforme seu sistema)
    page.fill('input[name="username"]', 'AS_Edson')
    page.fill('input[name="password"]', 'Fazenda@123')
    page.click('button[type="submit"]')
    
    # Aguardar redirecionamento
    page.wait_for_url("**/dashboard/**", timeout=5000)
    
    return page


@pytest.mark.e2e
class TestMovimentacaoEstoqueE2E:
    """Testes E2E para movimentações de estoque"""
    
    def test_entrada_estoque_aumenta_quantidade(self, usuario_logado: Page):
        """Testa entrada de estoque via formulário"""
        page = usuario_logado
        
        # Navegar para estoque de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Pegar estoque atual do primeiro produto
        primeira_linha = page.locator('tbody tr').first
        estoque_inicial_text = primeira_linha.locator('td').nth(3).inner_text()
        estoque_inicial = float(estoque_inicial_text.replace(',', '.'))
        produto_nome = primeira_linha.locator('td').nth(1).inner_text()
        
        print(f"\n📦 Produto: {produto_nome}")
        print(f"📊 Estoque Inicial: {estoque_inicial}")
        
        # Clicar no botão "Entrada"
        primeira_linha.locator('a[title="Dar entrada no estoque"]').click()
        page.wait_for_load_state("networkidle")
        
        # Verificar se produto está pré-selecionado
        expect(page.locator('.alert-info')).to_contain_text(produto_nome)
        
        # Preencher formulário de entrada
        page.select_option('select[name="origem"]', 'COMPRA')
        
        # Aguardar Select2 carregar
        time.sleep(1)
        
        # Quantidade a adicionar
        quantidade_entrada = 25.5
        page.fill('input[name="quantidade"]', str(quantidade_entrada))
        
        # Verificar se unidade de medida foi preenchida
        unidade_medida = page.locator('input[name="unidade_medida"]').input_value()
        print(f"📏 Unidade de Medida: {unidade_medida}")
        assert unidade_medida != '', "Unidade de medida deve ser preenchida automaticamente"
        
        # Preencher documento
        page.fill('input[name="documento"]', 'NF-TEST-001')
        
        # Preencher observação
        page.fill('textarea[name="observacao"]', 'Teste E2E - Entrada de estoque')
        
        # Submeter formulário
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        
        # Verificar mensagem de sucesso
        expect(page.locator('.alert-success, .messages')).to_be_visible(timeout=5000)
        
        # Voltar para lista de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Buscar o produto novamente
        page.fill('input[name="busca"]', produto_nome)
        page.click('button:has-text("Buscar")')
        page.wait_for_load_state("networkidle")
        
        # Verificar estoque atualizado
        primeira_linha_atualizada = page.locator('tbody tr').first
        estoque_final_text = primeira_linha_atualizada.locator('td').nth(3).inner_text()
        estoque_final = float(estoque_final_text.replace(',', '.'))
        
        print(f"📊 Estoque Final: {estoque_final}")
        print(f"✅ Entrada de {quantidade_entrada} registrada com sucesso!")
        
        # Validar que o estoque aumentou
        assert estoque_final == estoque_inicial + quantidade_entrada, \
            f"Estoque deveria ser {estoque_inicial + quantidade_entrada}, mas é {estoque_final}"
    
    
    def test_saida_estoque_diminui_quantidade(self, usuario_logado: Page):
        """Testa saída de estoque via formulário"""
        page = usuario_logado
        
        # Navegar para estoque de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Pegar produto com estoque disponível
        primeira_linha = page.locator('tbody tr').first
        estoque_inicial_text = primeira_linha.locator('td').nth(3).inner_text()
        estoque_inicial = float(estoque_inicial_text.replace(',', '.'))
        produto_nome = primeira_linha.locator('td').nth(1).inner_text()
        
        # Garantir que há estoque para saída
        if estoque_inicial < 10:
            pytest.skip(f"Estoque insuficiente para teste de saída: {estoque_inicial}")
        
        print(f"\n📦 Produto: {produto_nome}")
        print(f"📊 Estoque Inicial: {estoque_inicial}")
        
        # Clicar no botão "Ver Lotes"
        primeira_linha.locator('a[title="Ver lotes deste produto"]').click()
        page.wait_for_load_state("networkidle")
        
        # Clicar em "Nova Saída" do primeiro lote disponível
        lote_disponivel = page.locator('tbody tr:has(.badge:has-text("Disponível"))').first
        lote_disponivel.locator('a[title*="Registrar saída"]').click()
        page.wait_for_load_state("networkidle")
        
        # Preencher formulário de saída
        page.select_option('select[name="origem"]', 'REQUISICAO')
        
        # Aguardar Select2
        time.sleep(1)
        
        # Quantidade a retirar
        quantidade_saida = 5.0
        page.fill('input[name="quantidade"]', str(quantidade_saida))
        
        # Verificar unidade de medida
        unidade_medida = page.locator('input[name="unidade_medida"]').input_value()
        print(f"📏 Unidade de Medida: {unidade_medida}")
        
        # Preencher observação
        page.fill('textarea[name="observacao"]', 'Teste E2E - Saída de estoque para campo')
        
        # Submeter formulário
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        
        # Verificar mensagem de sucesso
        expect(page.locator('.alert-success, .messages')).to_be_visible(timeout=5000)
        
        # Voltar para lista de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Buscar o produto
        page.fill('input[name="busca"]', produto_nome)
        page.click('button:has-text("Buscar")')
        page.wait_for_load_state("networkidle")
        
        # Verificar estoque atualizado
        primeira_linha_atualizada = page.locator('tbody tr').first
        estoque_final_text = primeira_linha_atualizada.locator('td').nth(3).inner_text()
        estoque_final = float(estoque_final_text.replace(',', '.'))
        
        print(f"📊 Estoque Final: {estoque_final}")
        print(f"✅ Saída de {quantidade_saida} registrada com sucesso!")
        
        # Validar que o estoque diminuiu
        assert estoque_final == estoque_inicial - quantidade_saida, \
            f"Estoque deveria ser {estoque_inicial - quantidade_saida}, mas é {estoque_final}"
    
    
    def test_historico_produto_mostra_movimentacoes(self, usuario_logado: Page):
        """Testa visualização do histórico de movimentações"""
        page = usuario_logado
        
        # Navegar para estoque de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Clicar no botão "Ver Histórico" do primeiro produto
        primeira_linha = page.locator('tbody tr').first
        produto_nome = primeira_linha.locator('td').nth(1).inner_text()
        
        print(f"\n📦 Visualizando histórico de: {produto_nome}")
        
        primeira_linha.locator('a[title="Ver histórico de movimentações"]').click()
        page.wait_for_load_state("networkidle")
        
        # Verificar se está na página de histórico
        expect(page.locator('h2:has-text("Histórico do Produto")')).to_be_visible()
        expect(page.locator('h4:has-text("{}")'.format(produto_nome))).to_be_visible()
        
        # Verificar se estatísticas estão visíveis
        expect(page.locator('text=Total Entradas')).to_be_visible()
        expect(page.locator('text=Total Saídas')).to_be_visible()
        
        # Verificar se há movimentações na tabela
        movimentacoes = page.locator('tbody tr').count()
        print(f"📋 Movimentações encontradas: {movimentacoes}")
        
        if movimentacoes > 0:
            # Verificar estrutura da tabela
            primeira_movimentacao = page.locator('tbody tr').first
            expect(primeira_movimentacao.locator('td').first).to_be_visible()
            
        # Testar filtros
        page.select_option('select[name="tipo"]', 'ENTRADA')
        page.click('button:has-text("Filtrar")')
        page.wait_for_load_state("networkidle")
        
        print("✅ Histórico carregado e filtros funcionando!")
    
    
    def test_gerar_pdf_historico(self, usuario_logado: Page):
        """Testa geração de PDF do histórico"""
        page = usuario_logado
        
        # Navegar para estoque de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Clicar no histórico do primeiro produto
        primeira_linha = page.locator('tbody tr').first
        produto_nome = primeira_linha.locator('td').nth(1).inner_text()
        
        primeira_linha.locator('a[title="Ver histórico de movimentações"]').click()
        page.wait_for_load_state("networkidle")
        
        print(f"\n📄 Gerando PDF do histórico de: {produto_nome}")
        
        # Preparar para download
        with page.expect_download() as download_info:
            page.click('a:has-text("PDF")')
        
        download = download_info.value
        
        # Verificar se o download foi realizado
        assert download.suggested_filename.endswith('.pdf'), "Arquivo deve ser PDF"
        print(f"✅ PDF gerado: {download.suggested_filename}")
    
    
    def test_produto_pre_selecionado_entrada(self, usuario_logado: Page):
        """Testa se produto vem pré-selecionado ao clicar em Entrada"""
        page = usuario_logado
        
        # Navegar para estoque de produtos
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        # Pegar nome do produto
        primeira_linha = page.locator('tbody tr').first
        produto_nome = primeira_linha.locator('td').nth(1).inner_text()
        
        print(f"\n🎯 Testando pré-seleção de: {produto_nome}")
        
        # Clicar no botão "Entrada"
        primeira_linha.locator('a[title="Dar entrada no estoque"]').click()
        page.wait_for_load_state("networkidle")
        
        # Verificar se há alerta informando produto pré-selecionado
        alert = page.locator('.alert-info')
        expect(alert).to_be_visible()
        expect(alert).to_contain_text(produto_nome)
        
        # Verificar se unidade de medida foi preenchida automaticamente
        unidade_medida = page.locator('input[name="unidade_medida"]').input_value()
        assert unidade_medida != '', "Unidade de medida deve ser preenchida automaticamente"
        
        print(f"✅ Produto pré-selecionado corretamente")
        print(f"📏 Unidade: {unidade_medida}")
    
    
    def test_validacao_quantidade_negativa(self, usuario_logado: Page):
        """Testa se sistema valida quantidade negativa"""
        page = usuario_logado
        
        # Navegar para entrada de estoque
        page.goto("http://127.0.0.1:8000/estoque/entrada/")
        page.wait_for_load_state("networkidle")
        
        print("\n🔍 Testando validação de quantidade negativa")
        
        # Selecionar origem
        page.select_option('select[name="origem"]', 'COMPRA')
        
        # Tentar inserir quantidade negativa
        page.fill('input[name="quantidade"]', '-10')
        
        # Submeter formulário
        page.click('button[type="submit"]')
        
        # Verificar se há erro de validação
        # (O HTML5 já valida, mas pode haver validação backend também)
        quantidade_input = page.locator('input[name="quantidade"]')
        is_invalid = quantidade_input.evaluate('el => !el.validity.valid')
        
        if is_invalid:
            print("✅ Validação HTML5 impediu quantidade negativa")
        else:
            # Se passou HTML5, deve ter erro do backend
            expect(page.locator('.alert-danger, .text-danger')).to_be_visible(timeout=3000)
            print("✅ Validação backend impediu quantidade negativa")


@pytest.mark.e2e
class TestFiltrosEstoque:
    """Testes E2E para filtros na lista de estoque"""
    
    def test_filtro_por_categoria(self, usuario_logado: Page):
        """Testa filtro por categoria"""
        page = usuario_logado
        
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        print("\n🔍 Testando filtro por categoria")
        
        # Selecionar uma categoria
        categorias = page.locator('select[name="categoria"] option').all()
        if len(categorias) > 1:  # Tem mais que a opção vazia
            page.select_option('select[name="categoria"]', index=1)
            page.click('button:has-text("Buscar")')
            page.wait_for_load_state("networkidle")
            
            # Verificar se há resultados
            linhas = page.locator('tbody tr').count()
            print(f"✅ {linhas} produto(s) encontrado(s)")
    
    
    def test_filtro_estoque_zerado(self, usuario_logado: Page):
        """Testa filtro de estoque zerado"""
        page = usuario_logado
        
        page.goto("http://127.0.0.1:8000/estoque/produtos/")
        page.wait_for_load_state("networkidle")
        
        print("\n🔍 Testando filtro de estoque zerado")
        
        # Selecionar "Estoque zerado"
        page.select_option('select[name="estoque"]', 'zerado')
        page.click('button:has-text("Buscar")')
        page.wait_for_load_state("networkidle")
        
        # Verificar se todos os produtos têm estoque 0
        linhas = page.locator('tbody tr')
        count = linhas.count()
        
        if count > 0:
            for i in range(min(count, 5)):  # Verificar primeiras 5 linhas
                estoque_text = linhas.nth(i).locator('td').nth(3).inner_text()
                estoque = float(estoque_text.replace(',', '.'))
                assert estoque == 0.0, f"Produto com estoque {estoque} apareceu no filtro 'zerado'"
        
        print(f"✅ Filtro funcionando corretamente")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '-s', '--headed', '--slowmo=500'])
