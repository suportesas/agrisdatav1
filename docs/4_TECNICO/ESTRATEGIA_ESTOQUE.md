Owner: Estoque
Status: Approved
Last Updated: 2026-07-10
Scope: Movimentação e cálculo de estoque

# Estratégia de Atualização de Estoque

## Visão Geral

O sistema de estoque do Agrisdata suporta **dois fluxos principais** de atualização:

### 1️⃣ Fluxo de Lotes (Histórico - com detalhamento PEPS/FIFO)
- **Quando usar**: Produtos que exigem rastreabilidade por lote
- **Processo**:
  1. Cria-se um **Lote** com `quantidade_atual`
  2. Cria-se uma **MovimentacaoEstoque** referenciando o lote
  3. Chama-se `movimentacao.executar()` que:
     - Atualiza `Lote.quantidade_atual`
     - Recalcula `Produto.estoque_atual` (soma dos lotes)

### 2️⃣ Fluxo Direto (Novo - entrada rápida sem lote)
- **Quando usar**: Produtos sem rastreabilidade detalhada, entrada manual rápida
- **Processo**:
  1. Cria-se uma **MovimentacaoEstoque** com `produto` (sem lote)
  2. Salva-se o registro (simplesmente `movimentacao.save()`)
  3. Sistema calcula automaticamente `Produto.estoque_atual`:
     - `entrada_total` = soma de todas as ENTRADA
     - `saida_total` = soma de todas as SAIDA
     - `estoque_atual` = entrada - saída

---

## Fluxos Detalhados

### Fluxo A: Solicitação de Compra → Recebimento → Estoque (com Lotes)

```
SolicitacaoCompra
    ↓
PedidoCompra
    ↓
ItemRecebimento.registrar_movimento_estoque()
    ├─ Cria Lote (com quantidade_atual)
    └─ Atualiza Produto.estoque_atual (soma dos lotes DISPONIVEL)
```

**Código**: `compras/models.py` - `ItemRecebimento.registrar_movimento_estoque()`

---

### Fluxo B: Entrada Manual via Formulário (sem Lote)

```
Form: EntradaEstoqueForm
    ↓
MovimentacaoEstoque.save()
    ├─ Gera número automático
    └─ Retorna (NÃO atualiza estoque ainda)

POST → Salva
    ↓
Imediatamente visível em: Produto.estoque_atual
    ├─ Calcula: SUM(ENTRADA) - SUM(SAIDA)
    └─ Não precisa de .executar()
```

**Forma de visualização**: Em tempo real, pois `estoque_atual` é calculado diretamente

---

### Fluxo C: Movimentação com Lote (SAIDA, TRANSFERENCIA, AJUSTE)

```
Form: MovimentacaoEstoqueForm
    ↓
MovimentacaoEstoque.save()
    └─ Gera número automático apenas
    ↓
Precisa chamar movimentacao.executar(usuario)
    ├─ Valida quantidade disponível no lote
    ├─ Atualiza Lote.quantidade_atual
    ├─ Recalcula Produto.estoque_atual (soma lotes)
    └─ Marca como EXECUTADO
```

**Código**: `estoque/views.py` - `movimentacao_executar()`

---

## Tabela de Responsabilidades

| Operação | Triggers | Atualiza | Resultado |
|----------|----------|----------|-----------|
| **Entrada (sem lote)** | `MovimentacaoEstoque.save()` | Produto.estoque_atual | Imediato ✅ |
| **Entrada (com lote)** | `executar()` | Lote + Produto | Validado ✅ |
| **Saida** | `executar()` | Lote + Produto | Validado ✅ |
| **Transferência** | `executar()` | Lote origem + Lote destino + Produto | Validado ✅ |
| **Ajuste** | `executar()` | Lote + Produto | Validado ✅ |
| **Lote.save()** | Quantidade muda | Produto.estoque_atual | Via Lote.save() |

---

## Código-Chave

### MovimentacaoEstoque.save() - Entrada Rápida
```python
def save(self, *args, **kwargs):
    """Gera número automático mas NÃO atualiza estoque aqui"""
    if not self.numero:
        self.numero = self.gerar_numero()
    
    if not self.armazem_origem and self.tipo in ['SAIDA', 'TRANSFERENCIA']:
        if self.lote:
            self.armazem_origem = self.lote.armazem
            self.local_origem = self.lote.local_estocagem
    
    super().save(*args, **kwargs)
    # Sem atualização aqui - apenas salva
```

### MovimentacaoEstoque.executar() - Validação de Lote
```python
@transaction.atomic
def executar(self, usuario):
    """Executa e atualiza estoque atomicamente"""
    if self.status not in ['PENDENTE', 'APROVADO']:
        raise ValidationError('...')
    self._atualizar_estoque()  # Atualiza lote e produto
    self.status = 'EXECUTADO'
    self.executado_por = usuario
    self.data_execucao = timezone.now()
    self.save()
```

### Lote.save() - Recalcula Produto
```python
def save(self, *args, **kwargs):
    """Atualiza status e recalcula estoque_atual do produto"""
    # ... validações ...
    super().save(*args, **kwargs)
    # Recalcula produto com base em todos os lotes
    if hasattr(self.produto, 'recalcular_estoque'):
        self.produto.recalcular_estoque()
```

---

## Exemplo Prático: Entrada de Fertilizante Ureia (100 KG)

### Cenário 1: Entrada Rápida (SEM Lote)
```python
# 1. Usuário preenche formulário
form = EntradaEstoqueForm(data={
    'tipo': 'ENTRADA',
    'origem': 'COMPRA',
    'produto': Produto.objects.get(nome='Fertilizante Ureia'),
    'unidade_medida': UnidadeMedida.objects.get(sigla='KG'),
    'quantidade': 100,
    'lote': None  # ← Vazio
})

# 2. Form salva
movimentacao = form.save()

# 3. Automaticamente:
# - Cria MovimentacaoEstoque(id=12, tipo='ENTRADA', quantidade=100, produto=Ureia)
# - Produto.estoque_atual = SUM(ENTRADA) - SUM(SAIDA) = 100 - 0 = 100 ✅

# 4. Visualizar em tempo real:
ureia = Produto.objects.get(nome='Fertilizante Ureia')
print(ureia.estoque_atual)  # → 100.000
```

### Cenário 2: Entrada com Lote (via Pedido de Compra)
```python
# 1. ItemRecebimento.registrar_movimento_estoque()
#    └─ Cria Lote('Fertilizante Ureia', armazem, quantidade=100)
#    └─ Cria MovimentacaoEstoque(tipo='ENTRADA', lote=...)
#    └─ Chama movimentacao.executar()

# 2. executar() atualiza:
# - Lote.quantidade_atual = 0 + 100 = 100
# - Produto.estoque_atual = SUM(lotes DISPONIVEL) = 100 ✅

ureia = Produto.objects.get(nome='Fertilizante Ureia')
print(ureia.estoque_atual)  # → 100.000
```

---

## Fluxo de Compra Completo (Verificado ✅)

```
SolicitacaoCompra (criada)
    ↓
PedidoCompra (gerado)
    ├─ status='PENDENTE'
    └─ itens ligados
    ↓
Recebimento (parcial/total)
    ├─ ItemRecebimento.quantidade_recebida = 100
    ├─ ItemRecebimento.registrar_movimento_estoque()
    │   ├─ Cria Lote (quantidade_inicial=100, quantidade_atual=100)
    │   └─ Produto.estoque_atual += 100
    └─ PedidoCompra.status = 'RECEBIDO'
    ↓
Resultado final:
    └─ Produto.estoque_atual = 100 ✅
    └─ Lote.quantidade_atual = 100 ✅
    └─ Movimentações registradas ✅
```

---

## Status de Implementação

| Fluxo | Status | Notas |
|-------|--------|-------|
| Entrada Manual (sem Lote) | ✅ **TESTADO** | Funciona em tempo real |
| Entrada com Lote | ✅ **OK** | Via `ItemRecebimento` |
| Saída com Lote | ✅ **Pronto** | Requer `.executar()` |
| Transferência | ✅ **Pronto** | Cria/Atualiza lote destino |
| Ajuste | ✅ **Pronto** | Validação de quantidade |
| Recálculo em lote | ✅ **Pronto** | Comando `recalcular_estoque` |

---

## Debugging

Se estoque não atualizar:

1. **Verifica se é Entrada sem Lote**:
   ```python
   mov = MovimentacaoEstoque.objects.get(id=12)
   print(f"Tipo: {mov.tipo}")  # ENTRADA?
   print(f"Lote: {mov.lote}")  # None?
   print(f"Produto: {mov.produto}")  # Preenchido?
   ```

2. **Verifica se Lote foi atualizado**:
   ```python
   lote = Lote.objects.get(id=1)
   print(f"Qtd Atual: {lote.quantidade_atual}")
   ```

3. **Recalcula manualmente**:
   ```python
   from estoque.management.commands.recalcular_estoque import Command
   Command().handle()
   ```

---

## Conclusão

O sistema agora suporta **dois caminhos de entrada**:
- ✅ **Rápido**: Entrada sem lote (cálculo direto)
- ✅ **Rastreável**: Entrada com lote (PEPS/FIFO com validação)

Ambos atualizam corretamente o `Produto.estoque_atual`!
