# Testes E2E de Estoque

## 📋 Sobre
Testes end-to-end (E2E) que simulam um usuário real navegando e preenchendo formulários no sistema.

## 🎯 Testes Implementados

### ✅ Testes de Movimentação
1. **test_entrada_estoque_aumenta_quantidade** - Simula entrada de estoque via formulário web
2. **test_saida_estoque_diminui_quantidade** - Simula saída de estoque via formulário web  
3. **test_historico_produto_mostra_movimentacoes** - Verifica visualização do histórico
4. **test_gerar_pdf_historico** - Testa geração de PDF do histórico
5. **test_produto_pre_selecionado_entrada** - Verifica pré-seleção de produto
6. **test_validacao_quantidade_negativa** - Valida que não aceita quantidade negativa

### ✅ Testes de Filtros
7. **test_filtro_por_categoria** - Testa filtro por categoria
8. **test_filtro_estoque_zerado** - Testa filtro de produtos com estoque zerado

## 🚀 Como Executar

### Pré-requisitos
```bash
# Instalar playwright browsers (primeira vez)
playwright install chromium
```

### Configuração
1. **Servidor deve estar rodando:**
   ```bash
   python manage.py runserver
   ```

2. **Ajustar credenciais de login** em `test_movimentacao_e2e.py`:
   ```python
   page.fill('input[name="username"]', 'SEU_USUARIO')
   page.fill('input[name="password"]', 'SUA_SENHA')
   ```

3. **Ter ao menos 1 produto cadastrado** com estoque disponível

### Executar Testes

#### Todos os testes E2E (headless - sem abrir navegador)
```bash
pytest estoque/tests/test_movimentacao_e2e.py -v -s -m e2e
```

#### Com navegador visível (útil para debug)
```bash
pytest estoque/tests/test_movimentacao_e2e.py -v -s -m e2e --headed
```

#### Com navegador em câmera lenta
```bash
pytest estoque/tests/test_movimentacao_e2e.py -v -s -m e2e --headed --slowmo=1000
```

#### Teste específico
```bash
pytest estoque/tests/test_movimentacao_e2e.py::TestMovimentacaoEstoqueE2E::test_entrada_estoque_aumenta_quantidade -v -s --headed
```

#### Apenas testes de filtros
```bash
pytest estoque/tests/test_movimentacao_e2e.py::TestFiltrosEstoque -v -s --headed
```

## 🎬 Modo Interativo
```bash
# Abre o navegador e pausa antes de cada ação
pytest estoque/tests/test_movimentacao_e2e.py -v -s --headed --slowmo=2000
```

## 📸 Capturas de Tela
Para tirar screenshot em caso de falha, adicione ao `pytest.ini`:
```ini
[pytest]
markers =
    e2e: End-to-end tests using Playwright
```

## 🐛 Debug
```bash
# Modo debug com PWDEBUG
PWDEBUG=1 pytest estoque/tests/test_movimentacao_e2e.py::TestMovimentacaoEstoqueE2E::test_entrada_estoque_aumenta_quantidade -v -s
```

## 📊 Resultado Esperado

```
Test session starts
platform win32 -- Python 3.13.6, pytest-7.4.2

estoque/tests/test_movimentacao_e2e.py::TestMovimentacaoEstoqueE2E::test_entrada_estoque_aumenta_quantidade
📦 Produto: Amistar TOP
📊 Estoque Inicial: 100.0
📏 Unidade de Medida: KG - Quilograma
📊 Estoque Final: 125.5
✅ Entrada de 25.5 registrada com sucesso!
PASSED

estoque/tests/test_movimentacao_e2e.py::TestMovimentacaoEstoqueE2E::test_saida_estoque_diminui_quantidade
📦 Produto: Amistar TOP
📊 Estoque Inicial: 125.5
📏 Unidade de Medida: KG - Quilograma
📊 Estoque Final: 120.5
✅ Saída de 5.0 registrada com sucesso!
PASSED

... (outros testes)

========== 8 passed in 45.23s ==========
```

## 🎯 O Que os Testes Verificam

### Entrada de Estoque
- ✅ Produto é pré-selecionado ao clicar em "Entrada"
- ✅ Unidade de medida é preenchida automaticamente
- ✅ Formulário é submetido com sucesso
- ✅ Estoque aumenta corretamente
- ✅ Mensagem de sucesso é exibida

### Saída de Estoque
- ✅ Lote disponível é listado
- ✅ Formulário de saída funciona
- ✅ Estoque diminui corretamente
- ✅ Validações funcionam

### Histórico
- ✅ Lista todas as movimentações
- ✅ Estatísticas são exibidas
- ✅ Filtros funcionam
- ✅ PDF é gerado com sucesso

## 🔧 Troubleshooting

### Erro: "Timeout waiting for element"
- Verifique se o servidor está rodando em `http://127.0.0.1:8000/`
- Aumente o timeout: `page.wait_for_load_state("networkidle", timeout=10000)`

### Erro: "Login failed"
- Verifique credenciais na fixture `usuario_logado`
- Confirme que a URL de login está correta

### Erro: "No product found"
- Cadastre ao menos 1 produto com estoque
- Ou ajuste os testes para criar produtos antes

## 📝 Notas
- Testes E2E são **mais lentos** que testes unitários (30-60s)
- Use `--headed` para ver o que está acontecendo
- Use `--slowmo=1000` para debugar visualmente
- Testes criam dados reais no banco (use banco de testes)
