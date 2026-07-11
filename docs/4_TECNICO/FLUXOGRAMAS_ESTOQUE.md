Owner: Estoque
Status: Approved
Last Updated: 2026-07-10
Scope: Movimentação e cálculo de estoque

# Fluxogramas do Sistema de Estoque

## 1. Fluxo Atual de Entrada (Entrada Rápida SEM Lote)

```
┌─────────────────────────────────┐
│  Usuário acessa /estoque/entrada│
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  EntradaEstoqueForm renderiza   │
│  - Tipo: ENTRADA (pré-preenchido)
│  - Origem: Compra (filtrada)
│  - Produto: SELECT (auto-popula)
│  - Unidade: AUTO-PREENCHE
│  - Quantidade: INPUT
│  - Lote: VAZIO (opcional)
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Usuário preenche:              │
│  - Produto: Fertilizante Ureia
│  - Quantidade: 100
│  - Lote: deixa em branco
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  form.is_valid() ✅
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  form.save()                    │
│  ├─ MovimentacaoEstoque.save()
│  ├─ Define empresa, usuario
│  └─ commit=True
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  _atualizar_estoque_produto_direto
│  ├─ Busca TODAS MovimentacaoEstoque
│  │  com produto=Ureia
│  ├─ Calcula entrada = SUM(ENTRADA)
│  ├─ Calcula saida = SUM(SAIDA)
│  └─ estoque_atual = entrada - saida
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Produto.estoque_atual atualizado
│  ✅ SUCESSO - Redireciona
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│  Usuário vê: "Entrada criada"
│  Estoque visível no dashboard
└─────────────────────────────────┘
```

---

## 2. Fluxo Existente de Entrada (COM Lote - via Pedido Compra)

```
┌──────────────────────────┐
│ ItemRecebimento criado   │
│ (via Recebimento de PC)
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ registrar_movimento_     │
│ estoque()                │
│                          │
│ ├─ Cria Lote:          │
│ │  - produto_id=9
│ │  - quantidade_atual=100
│ │  - status=DISPONIVEL
│ │                       │
│ └─ Cria MovimentacaoEstoque:
│    - lote_id=N
│    - tipo=ENTRADA
│    - quantidade=100
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Produto.estoque_atual   │
│ = SUM(lotes.DISPONIVEL) │
│ = 100                    │
│ ✅ ATUALIZADO
└──────────────────────────┘
```

---

## 3. Fluxo de Saída (SEM Lote) 

```
┌─────────────────────────┐
│  Formulário SAIDA       │
│  - Tipo: SAIDA
│  - Origem: VENDA
│  - Produto: Ureia
│  - Quantidade: 50
│  - Lote: vazio
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│  form.save()            │
│  ├─ MovimentacaoEstoque
│  │  (tipo=SAIDA)
│  └─ _atualizar_estoque_
│     produto_direto()
└──────────────┬──────────┘
               │
               ▼
┌─────────────────────────┐
│  Calcula:               │
│  entrada  = 250 KG
│  saida    = 50 KG
│  estoque  = 200 KG ✅
└─────────────────────────┘
```

---

## 4. Fluxo Completo (Entrada + Saída + Transferência)

```
INICIO: estoque_atual = 0
│
├─ ENTRADA 100 KG (produto direto)
│  └─ estoque_atual = 100 ✅
│
├─ ENTRADA 150 KG (produto direto)
│  └─ estoque_atual = 250 ✅
│
├─ SAIDA 50 KG (produto direto)
│  └─ estoque_atual = 200 ✅
│
├─ TRANSFERENCIA COM LOTE
│  ├─ Requer executar()
│  ├─ Cria Lote destino
│  └─ estoque_atual recalculado ✅
│
└─ AJUSTE -25 KG (produto direto)
   └─ estoque_atual = 175 ✅

RESUMO:
  Entradas: 250 KG
  Saidas:   75 KG
  Estoque:  175 KG ✅
```

---

## 5. Matriz de Atualização de Estoque

```
┌─────────────────┬──────────────┬──────────────┬──────────────┐
│ Tipo            │ Com Lote     │ Sem Lote     │ Atualização  │
├─────────────────┼──────────────┼──────────────┼──────────────┤
│ ENTRADA         │ executar()   │ form.save()  │ Automática   │
│ SAIDA           │ executar()   │ form.save()  │ Automática   │
│ TRANSFERENCIA   │ executar()   │ N/A          │ Atomica      │
│ AJUSTE          │ executar()   │ form.save()  │ Automática   │
│ DEVOLUCAO       │ executar()   │ form.save()  │ Automática   │
└─────────────────┴──────────────┴──────────────┴──────────────┘

Legenda:
- executar()     = Valida quantidade, atualiza lote+produto atomicamente
- form.save()    = Recalcula estoque direto (entrada-saida)
- Automática     = Sem necessidade de .executar()
- Atomica        = Tudo-ou-nada via @transaction.atomic
```

---

## 6. Hierarquia de Responsabilidade

```
┌─────────────────────────────────────────────┐
│  Produto.estoque_atual                      │
│  (Campo principal do sistema)               │
│                                             │
│  Actualizado por DUAS estratégias:          │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
   ┌────────────┐  ┌─────────────────┐
   │ COM LOTE   │  │ SEM LOTE        │
   │            │  │                 │
   │ 1. Cria    │  │ 1. Cria Mov...
   │    Lote    │  │                 │
   │ 2. Mov...  │  │ 2. form.save()  │
   │    .exe    │  │    atualiza     │
   │    cutar() │  │    direto       │
   │ 3. Soma    │  │ 3. SUM(ENT)-
   │    lotes   │  │    SUM(SAI)
   └────────────┘  └─────────────────┘
```

---

## 7. Sequência de Chamadas - Entrada Direta

```
USER
  │
  └─ POST /estoque/entrada/
     │
     └─ entradaform_form.save()
        │
        ├─ super().save(commit=False)
        │  └─ MovimentacaoEstoque instanciado
        │
        ├─ Set empresa, usuario
        │
        ├─ if commit:
        │  │
        │  ├─ movimentacao.save()
        │  │  └─ Models.MovimentacaoEstoque.save()
        │  │     ├─ Gera numero
        │  │     └─ super().save() → DB
        │  │
        │  └─ if tipo=='ENTRADA' and not lote and produto:
        │     │
        │     └─ _atualizar_estoque_produto_direto(mov)
        │        │
        │        ├─ Busca todas MovimentacaoEstoque
        │        │
        │        ├─ SUM(ENTRADA) = entrada
        │        ├─ SUM(SAIDA) = saida
        │        │
        │        └─ Produto.estoque_atual = entrada - saida
        │           └─ produto.save()
        │
        └─ return movimentacao ✅
           │
           └─ USER: "Sucesso! Estoque atualizado"
```

---

## 8. Sequência de Chamadas - Movimento com Lote

```
USER
  │
  └─ POST /estoque/movimentacao/executar/ID
     │
     └─ movimentacao.executar(usuario)
        │
        ├─ @transaction.atomic (inicio)
        │
        ├─ Valida status in ['PENDENTE','APROVADO']
        │
        ├─ self._atualizar_estoque()
        │  │
        │  ├─ if tipo == 'ENTRADA':
        │  │  └─ lote.quantidade_atual += qtd
        │  │     └─ lote.save()
        │  │        └─ Produto recalcula via Lote.save()
        │  │
        │  ├─ if tipo in ['SAIDA','DEVOLUCAO']:
        │  │  ├─ Valida quantidade disponível
        │  │  └─ lote.quantidade_atual -= qtd
        │  │     └─ lote.save()
        │  │
        │  └─ if tipo == 'TRANSFERENCIA':
        │     ├─ lote_origem.quantidade_atual -= qtd
        │     ├─ Busca/Cria lote_destino
        │     └─ Ambos salvam (recalculam produto)
        │
        ├─ self.status = 'EXECUTADO'
        ├─ self.executado_por = usuario
        ├─ self.save()
        │
        └─ @transaction.atomic (final) ✅
           │
           └─ USER: "Executado!"
```

---

## Resumo

| Cenário | Trigger | Validação | Atualização |
|---------|---------|-----------|-------------|
| Entrada rápida | form.save() | Básica (formulário) | Imediata (direto) |
| Entrada lote | .executar() | PEPS/FIFO | Via Lote.save() |
| Saída | form.save() | Básica | Imediata (direto) |
| Saída lote | .executar() | Qty check | Via Lote.save() |
| Transferência | .executar() | Qty + armazém | Atomic (2 lotes) |
| Ajuste | form/exec | Conforme origem | Conforme movimento |
