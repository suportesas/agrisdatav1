# Correção: Entrada Falsa no Estoque em Recebimentos

## Problema Identificado

Quando um **ItemRecebimento** era criado, a movimentação de estoque (ENTRADA) era registrada **imediatamente**, distorcendo o inventário:

- REC-000024 criado (PENDENTE) → Estoque já aumentava em 1.500 KG
- REC-000024 conferido (CONFERIDO) → Nenhuma mudança adicional
- REC-000024 finalizado (FINALIZADO) → Nenhuma mudança adicional

**Resultado:** Entrada falsa registrada enquanto o recebimento ainda estava em análise.

---

## Solução Implementada

### 1. **Desabilitar registro automático em ItemRecebimento.save()**
   - **Arquivo:** `compras/models.py` (linha ~1574)
   - **Antes:** Chamava `self.registrar_movimento_estoque()` automaticamente
   - **Depois:** Comentado e documentado que será chamado apenas na finalização

```python
# NÃO registra movimento aqui - será registrado apenas quando o recebimento for FINALIZADO
# Evita entrada falsa no estoque quando item está em PENDENTE/CONFERIDO
```

### 2. **Melhorar função registrar_movimento_estoque() para ser idempotente**
   - **Arquivo:** `compras/models.py` (linha ~1579)
   - **Mudanças:**
     - Verifica se já existe movimentação para este ItemRecebimento específico
     - Usa campo `observacao` com identificador único: `Item Recebimento #{self.id}`
     - Evita duplicatas mesmo que chamada várias vezes
     - Melhor logging e documentação

### 3. **View recebimento_entrada_estoque já estava correta**
   - **Arquivo:** `compras/views.py` (linha ~1966)
   - ✓ Valida que recebimento está em CONFERIDO
   - ✓ Chama `item.registrar_movimento_estoque()` apenas na finalização
   - ✓ Marca recebimento como FINALIZADO após processamento

---

## Fluxo Correto Agora

```
Recebimento PENDENTE
  ├─ ItemRecebimento adicionado
  ├─ Lote criado automaticamente
  └─ ✗ NENHUMA movimentação registrada

        ↓ (usuário clica "Conferir")

Recebimento CONFERIDO
  └─ ✗ Ainda nenhuma movimentação

        ↓ (usuário clica "Dar Entrada no Estoque")

Recebimento FINALIZADO
  └─ ✓ Movimentação ENTRADA registrada
  └─ ✓ Estoque atualizado
  └─ ✓ Quantidade do Lote ajustada
```

---

## Como Testar

1. **Criar novo recebimento com 1.500 KG**
   ```
   Acesse REC-000025 (ou próximo número)
   ```

2. **Verificar estoque ANTES e DEPOIS de cada etapa**
   ```
   ANTES: 3.000 KG (FERT-000002)
   
   Após criar item: 3.000 KG ✓ (nenhuma mudança - correto!)
   Após conferir: 3.000 KG ✓ (nenhuma mudança - correto!)
   Após finalizar: 4.500 KG ✓ (aumentou 1.500 KG - correto!)
   ```

3. **Verificar MovimentacaoEstoque**
   ```
   Apenas UMA movimentação com tipo=ENTRADA
   Data: quando FINALIZADO (não quando criado)
   ```

4. **Teste de idempotência (opcional)**
   ```python
   # Chamar a função novamente não duplica movimentação
   item.registrar_movimento_estoque()  # chamada 1
   item.registrar_movimento_estoque()  # chamada 2 - sem duplicata
   ```

---

## Validação de Auditoria

Agora é seguro fazer conferência de inventário:
- Movimentações registradas apenas quando entrada é efetivamente processada
- Estoque reflete realidade: lotes disponíveis + quantidades
- Auditoria limpa: data_movimentacao = data_recebimento (quando finalizado)

---

## Impacto em Outros Fluxos

- **Partial Receipts:** ✓ Funciona (cada item registra sua entrada ao finalizar)
- **Divergências:** ✓ Não afetado (usa mesma função)
- **Entrada Direta:** ✓ Não afetado (usa mesmo mecanismo)
- **Múltiplas Entradas:** ✓ Idempotente (evita duplicatas)

