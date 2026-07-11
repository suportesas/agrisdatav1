# Correções na Solicitação de Compra

## 📋 Resumo das Correções

Foram identificados e corrigidos **2 problemas principais** na formulário de Solicitação de Compra:

---

## 🐛 Problema 1: Duplicação de Campos de Produto

### ❌ O que estava acontecendo:
- Ao adicionar um novo item pelo botão "Adicionar Item", aparecia **dois campos de produto** na mesma linha
- Um campo vinha do template vazio (select HTML simples)
- Outro campo vinha do Django renderizado
- Isso causava confusão visual e potencial conflito de dados

### ✅ Solução Implementada:

1. **Separação do Template Vazio** (solicitacao_form.html)
   - Movemos o template vazio para um container separado: `#empty-form-container`
   - Removemos a classe `d-none` do template e usamos um container pai com `display: none`
   - Isso evita conflitos de CSS e seleção jQuery

2. **Melhorias no JavaScript**
   - Função `cloneNode()` mais robusta com substituição correta de índices
   - Inicializa Select2 apenas após clonar corretamente
   - Reseta valores dos campos antes de adicionar à tabela
   - Classes CSS melhoradas para identificar campos específicos

### Estrutura Antes:
```html
<tbody id="item-forms">
    {% for form in formset %}...{% endfor %}
    <tr class="empty-form d-none">...</tr>  <!-- ❌ Problema aqui -->
</tbody>
```

### Estrutura Depois:
```html
<tbody id="item-forms">
    {% for form in formset %}...{% endfor %}
</tbody>

<tbody id="empty-form-container" class="d-none">  <!-- ✅ Separado -->
    <tr class="empty-form">...</tr>
</tbody>
```

---

## 🔴 Problema 2: Validação de Campos Obrigatórios Incompleta

### ❌ O que estava acontecendo:
- A validação JavaScript era básica e não cobria todos os casos
- Mensagens de erro do servidor apareciam como warnings (pouco visível)
- Não havia tratamento claro para campos vazios
- O contador de itens não era atualizado corretamente

### ✅ Solução Implementada:

1. **Validação Completa e Clara** (em solicitacao_form.html)
   - Validação de **Data de Necessidade** (obrigatório)
   - Validação de **Justificativa** (obrigatório, não vazio)
   - Validação de **Justificativa da Emergência** (obrigatório quando marcado como emergencial)
   - Validação de **Itens da Solicitação** (mínimo 1 item)
   - Para cada item: Produto, Quantidade e Unidade de Medida (todos obrigatórios)

```javascript
// Lista clara de validações
const erros = [];

// Validação 1: Data de necessidade
if (dataNecessidade && !dataNecessidade.value) {
    erros.push('❌ Dados da Solicitação: Data de necessidade é obrigatória');
}

// Validação 2: Justificativa
if (justificativa && !justificativa.value.trim()) {
    erros.push('❌ Dados da Solicitação: Justificativa é obrigatória');
}

// Validação 3: Emergência
if (emergencial && emergencial.checked && !justificativaEmergencial.value.trim()) {
    erros.push('❌ Dados da Solicitação: Justificativa da emergência é obrigatória');
}

// Validação 4: Itens obrigatórios
itemRows.forEach((row, idx) => {
    const itemNum = idx + 1;
    const produto = row.querySelector('[name$="produto"]');
    const quantidade = row.querySelector('[name$="quantidade"]');
    const unidade = row.querySelector('[name$="unidade_medida"]');

    if (!produto || !produto.value) {
        erros.push(`❌ Item ${itemNum}: Selecione um produto`);
    }
    if (!quantidade || !quantidade.value || Number(quantidade.value) <= 0) {
        erros.push(`❌ Item ${itemNum}: Informe uma quantidade válida`);
    }
    if (!unidade || !unidade.value) {
        erros.push(`❌ Item ${itemNum}: Selecione a unidade de medida`);
    }
});
```

2. **Mensagens de Erro Claras**
   - Mensagens com ícones visuais (❌)
   - Agrupadas por seção (Dados da Solicitação, Itens)
   - Exibidas em um único diálogo com lista formatada
   - Imperativas (ação clara do que fazer)

3. **Carregamento Automático de Unidades**
   - Nova API endpoint: `/compras/api/produto/{id}/unidades/`
   - Quando um produto é selecionado, as unidades de medida são carregadas automaticamente
   - Elimina necessidade de seleção manual da unidade

---

## 🔧 Mudanças Técnicas

### Arquivo: `compras/templates/compras/solicitacao_form.html`

**Alterações:**
1. Moveu o template vazio para container separado
2. Adicionou classes especiais aos campos (`.produto-select`, `.quantidade-input`, etc)
3. Melhorou validação JavaScript com erros explícitos
4. Adicionou integração com API de unidades

### Arquivo: `compras/views.py`

**Nova Função:**
```python
@login_required
def get_produto_unidades(request, produto_id):
    """API: Retorna as unidades de medida disponíveis para um produto"""
    # Busca produto
    # Retorna lista de unidades em JSON
    # Inclui unidade padrão do produto
```

### Arquivo: `compras/urls.py`

**Nova Rota:**
```python
path('api/produto/<int:produto_id>/unidades/', 
     views.get_produto_unidades, 
     name='get_produto_unidades'),
```

---

## 📊 Lista de Validação de Campos Obrigatórios

### Seção 1: Dados da Solicitação
- ✅ **Data de Necessidade** - Campo de data (obrigatório)
- ✅ **Justificativa** - Texto (obrigatório, não vazio)
- ⚪ **Departamento** - Texto (opcional)
- ⚪ **Observações** - Texto (opcional)

### Seção 2: Compra Emergencial (Condicional)
- ✅ **Justificativa da Emergência** - Texto (obrigatório **se** "Compra Emergencial" estiver marcado)

### Seção 3: Itens da Solicitação
- ✅ **Mínimo de 1 item** - Deve haver pelo menos um item
- ✅ **Produto** - Seleção (obrigatório por item)
- ✅ **Quantidade** - Número > 0 (obrigatório por item)
- ✅ **Unidade de Medida** - Seleção (obrigatório por item)
- ⚪ **Especificação** - Texto (opcional por item)

---

## 🚀 Melhorias Implementadas

### 1. **Carregamento Automático de Unidades**
- Quando produto é selecionado → carrega unidades automáticamente
- Evita necessidade de seleção manual
- Melhora UX (User Experience)

### 2. **Busca de Estoque**
- Exibe estoque atual do produto na tabela
- Atualiza quando produto muda
- Indicador visual "-" quando não há produto selecionado

### 3. **Validação em Tempo Real**
- Verifica seleção de produto
- Valida quantidade (deve ser > 0)
- Valida unidade de medida
- Evita submissão com erros

### 4. **Melhor Estrutura HTML/CSS**
- Campos melhor separados
- Sem duplicação de elementos
- Hierarquia visual clara
- Responsivo em mobile

---

## ✅ Testes Recomendados

1. **Teste 1: Validação Básica**
   - Tentar salvar com campos vazios
   - Verificar mensagens de validação

2. **Teste 2: Adição de Itens**
   - Adicionar vários itens
   - Verificar numeração e estrutura
   - Remover alguns itens

3. **Teste 3: Preenchimento Completo**
   - Preencher todos os campos obrigatórios
   - Selecionar produtos
   - Verificar carregamento automático de unidades
   - Submeter formulário com sucesso

4. **Teste 4: Compra Emergencial**
   - Selecionar "Compra Emergencial"
   - Verificar se aparece campo de justificativa
   - Tentar submeter sem justificativa (deve falhar)
   - Preencer justificativa e submeter

---

## 📝 Notas de Implementação

- Todos os endpoints de API requerem `@login_required`
- Validação no servidor (Django) é mantida intacta
- Validação no cliente (JavaScript) é apenas para UX melhorada
- Compatível com Select2 para searchable selects
- Suporta múltiplas empresas (isolamento de dados)

