# Debug da Unidade de Medida - Instruções

## 🔍 Como Verificar o Problema

### Passo 1: Abra a Página do Formulário
1. Vá para: `http://localhost:8000/compras/solicitacoes/nova/`
2. Pressione **F12** para abrir o Developer Tools
3. Clique na aba **"Console"**

### Passo 2: Verificar os Logs

Quando a página carrega, você deve ver logs como:

```
=== Carregando unidades para produtos existentes ===
Selects de produto encontrados: 1
Select 0: itens-0-produto Value: 
Validação OK - enviando formulário
```

### Passo 3: Selecionar um Produto

1. Clique no dropdown "Produto" do primeiro item
2. Selecione um produto (ex: "Arame Galvanizado 18 - 1,24Mm")
3. **Observe o console** - você deve ver logs como:

```
CHANGE EVENT: Produto foi alterado
Select element: <select name="itens-0-produto" ...>
Classe do elemento: form-select form-select-sm
Value: 4
=== Atualizando produto ===
Produto ID: 4
Linha encontrada: true
Select unidade encontrado: true
Estoque cell encontrado: true
Buscando unidades de: /compras/api/produto/4/unidades/
Response status: 200
Dados da API: {success: true, unidades: Array(7), unidade_padrao_id: 1, ...}
Unidades carregadas: 7 itens
Preenchendo select with 7 unidades
Opção adicionada: Caixa
Opção adicionada: Envelope
Opção adicionada: Litro
Opção adicionada: Pacote
Opção adicionada: Quilograma
Opção adicionada: Rolo
Opção adicionada: Unidade
Total de options no select: 8
Estoque atualizado: 0.00 Unidade
```

### Passo 4: Interpretação dos Logs

| Log | Significado | Ação se não aparecer |
|-----|-------------|-------------------|
| `CHANGE EVENT: Produto foi alterado` | Evento de mudança foi disparado | Verificar se o Select2 está funcionando corretamente |
| `Select unidade encontrado: true` | O select de unidade foi localizado | Verificar seletor CSS |
| `Buscando unidades de: /compras/api/...` | API está sendo chamada | Verificar se URL está correta |
| `Response status: 200` | API respondeu com sucesso | Verificar status HTTP (404, 500, etc) |
| `Unidades carregadas: 7 itens` | Dados foram retornados | Verificar se API tem dados |
| `Opção adicionada: ...` | Opções estão sendo adicionadas ao select | Pode haver problema com o DOM |
| `Total de options no select: 8` | Select tem as opções completas | Verificar se está visível |

---

## 🧪 Teste Prático

### Teste 1: Verificar se a API funciona

1. Abra uma nova aba do navegador
2. Vá para: `http://localhost:8000/compras/api/produto/4/unidades/`
3. Você deve ver um JSON como:

```json
{
  "success": true,
  "unidades": [
    {"id": 5, "nome": "Caixa", "sigla": "CX"},
    {"id": 6, "nome": "Envelope", "sigla": "ENV"},
    {"id": 3, "nome": "Litro", "sigla": "L"},
    {"id": 4, "nome": "Pacote", "sigla": "PC"},
    {"id": 2, "nome": "Quilograma", "sigla": "KG"},
    {"id": 7, "nome": "Rolo", "sigla": "RL"},
    {"id": 1, "nome": "Unidade", "sigla": "UN"}
  ],
  "unidade_padrao_id": 1,
  "unidade_padrao_nome": "Unidade"
}
```

Se não aparecer, pode haver problema com a API.

### Teste 2: Verificar o Select no Inspector

1. No Developer Tools, clique na aba **"Elements"**
2. Localize o `<tbody id="item-forms">`
3. Procure pelo `<select name="itens-0-unidade_medida">`
4. Veja as `<option>` dentro dele
5. Deve ter múltiplas opções (não vazio)

### Teste 3: Adicionar Item Novo

1. Volte para o formulário
2. Clique em **"Adicionar Item"**
3. Um novo item aparecerá
4. Abra o console (F12) e observe os logs
5. Selecione um produto no novo item
6. Observe se o select de unidade é preenchido

---

## 🐛 Problemas Comuns e Soluções

### Problema: "Select unidade encontrado: false"

**Causa:** O selector CSS não está encontrando o elemento

**Solução:**
1. No Inspector, clique no select de unidade
2. Veja qual é o atributo `name` exato
3. Confirme se termina com `unidade_medida`

### Problema: "Response status: 404"

**Causa:** A API não existe ou a URL está errada

**Solução:**
1. Verifique se o arquivo `compras/urls.py` tem a rota
2. Verifique se o arquivo `compras/views.py` tem a função `get_produto_unidades`
3. Execute `python manage.py check` para verificar erros

### Problema: "Unidades carregadas: 0 itens"

**Causa:** A API retornada vazia ou nenhuma unidade cadastrada

**Solução:**
1. Executeé o script de teste:
   ```bash
   python test_api_unidades.py
   ```
2. Verifique se a empresa tem unidades de medida cadastradas

### Problema: "Total de options no select: 1"

**Causa:** As opções são adicionadas, mas depois apagadas ou o select é recriado

**Solução:**
1. Verifique se há outro script JavaScript que está limpando o select
2. Procure por `.html('')` ou `.innerHTML = ''` no jQuery
3. Pode ser que o Select2 está interferindo

---

## 📋 Checklist de Fixação

- [ ] API `/compras/api/produto/{id}/unidades/` retorna JSON correto
- [ ] Console mostra log "CHANGE EVENT"
- [ ] Console mostra log "Unidades carregadas: X itens"
- [ ] Select de unidade está sendo preenchido visualmente
- [ ] Select2 está funcionando (ao selecionar produto, mostra em Select2)
- [ ] Ao adicionar novo item, o select de unidade é preenchido após selecionar produto

---

## 🚀 Próximas Etapas

Se tudo estiver funcionando no console mas não vendo as opções no select:

1. Abra Developer Tools → **Elements**
2. Procure pela linha: `<select name="itens-0-unidade_medida"...>`
3. Expanda e veja se contém `<option>`
4. Se sim, pode ser problema de CSS (visibility, display, etc)

Se os logs não aparecem:

1. Verifique se há erro de Syntax no JavaScript
2. Verifique se o jQuery/Select2 está sendo carregado
3. Verifique o status HTTP da página (F12 → Network → XHR)
