# 🔧 DOCUMENTAÇÃO TÉCNICA: INTEGRAÇÃO COMPRA ↔ FINANCEIRO

## 🎯 Objetivo
Quando um recebimento de compra (RecebimentoCompra) é faturado com uma Nota Fiscal, o sistema cria **automaticamente** uma Conta a Pagar no módulo financeiro.

---

## 📊 ARQUITETURA DO FLUXO

```
┌─────────────────────────────────────────────────────────────┐
│                     MÓDULO DE COMPRAS                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Passo 1: Compra Rápida                                     │
│  ├─ POST /compras/compra-rapida/                           │
│  ├─ Cria: PedidoCompra                                     │
│  ├─ Status: PENDENTE_RECEBIMENTO                           │
│  └─ Template: compra_rapida.html                           │
│                           ↓                                  │
│  Passo 2: Receber Mercadoria                               │
│  ├─ GET/POST /compras/recebimentos/<id>/conferir           │
│  ├─ Cria: RecebimentoCompra                                │
│  ├─ Cria: Lotes (estoque)                                  │
│  ├─ Status: CONFERIDO → FINALIZADO                         │
│  └─ Template: recebimento_detail.html                      │
│                           ↓                                  │
│  Passo 3: Registrar Nota Fiscal                            │
│  ├─ GET/POST /compras/recebimentos/<id>/faturar/           │
│  ├─ View: views_simples.faturar_recebimento()              │
│  ├─ Template: faturar_recebimento.html                     │
│  └─ Ações:                                                  │
│     ├─ Atualiza RecebimentoCompra.nota_fiscal              │
│     ├─ Atualiza RecebimentoCompra.valor_nf                 │
│     └─ CRIA ContaPagar no financeiro                       │
│                           ↓                                  │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│                   MÓDULO FINANCEIRO                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Conta a Pagar Criada                                       │
│  ├─ ContaPagar():                                          │
│  │  ├─ empresa = request.user.empresa                      │
│  │  ├─ fornecedor = recebimento.fornecedor                │
│  │  ├─ numero = "NF-{numero_nf}"                          │
│  │  ├─ valor_total = valor_nf                             │
│  │  ├─ status = "ABERTA"                                  │
│  │  └─ observacoes = "Gerada automaticamente..."          │
│  │                                                          │
│  └─ ParcelaContaPagar[] (múltiplas):                       │
│     ├─ numero_parcela = 1, 2, 3...                        │
│     ├─ valor_parcela = total / num_parcelas               │
│     ├─ data_vencimento = calculada conforme intervalo     │
│     └─ status = "ABERTA"                                  │
│                           ↓                                  │
│  Fluxo de Aprovação & Pagamento                            │
│  ├─ GET /financeiro/contas/<id>/                          │
│  ├─ POST /financeiro/contas/<id>/aprovar/                │
│  ├─ Muda status: ABERTA → APROVADA                        │
│  └─ Parcelas ficam prontas para pagar                     │
│                           ↓                                  │
│  Pagamento de Parcelas                                      │
│  ├─ GET/POST /financeiro/parcelas/<id>/pagar/             │
│  ├─ Cria: PagamentoContaPagar                             │
│  ├─ Status: PENDENTE → COMPENSADO → PAGA                 │
│  └─ Atualiza: Parcela.status = PAGA                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 CONEXÃO ENTRE MODELOS

### Fluxo de Dados

```
PedidoCompra
    ├─ numero = "00001"
    ├─ fornecedor_id = 5
    ├─ empresa_id = 1
    └─ status = "PENDENTE_RECEBIMENTO"
         ↓
RecebimentoCompra
    ├─ numero = "REC-00001"
    ├─ pedido_id = 1
    ├─ fornecedor_id = 5 (do pedido)
    ├─ empresa_id = 1 (do pedido)
    ├─ nota_fiscal = "123456"
    ├─ valor_nf = 10000.00
    └─ status = "CONFERIDO"
         ↓
         ↓ [VIEW: faturar_recebimento()] ↓
         ↓
ContaPagar
    ├─ numero = "NF-123456"
    ├─ fornecedor_id = 5 ← DO RECEBIMENTO
    ├─ empresa_id = 1 ← DO RECEBIMENTO
    ├─ valor_total = 10000.00 ← DO RECEBIMENTO
    ├─ data_emissao = <data_nf>
    ├─ status = "ABERTA"
    └─ parcelas = [...] ← CRIADAS DINAMICAMENTE
         ↓
ParcelaContaPagar[]
    ├─ #1: vence 04/04, valor 3.333,33
    ├─ #2: vence 04/05, valor 3.333,33
    └─ #3: vence 04/06, valor 3.333,34
```

---

## 💻 IMPLEMENTAÇÃO NO CÓDIGO

### 1. View de Faturamento (views_simples.py)

```python
@login_required
@transaction.atomic
def faturar_recebimento(request, recebimento_pk):
    """
    Registra NF do recebimento e cria ContaPagar automaticamente
    """
    from financeiro.models import ContaPagar, ParcelaContaPagar
    from datetime import timedelta
    
    recebimento = get_object_or_404(
        RecebimentoCompra,
        pk=recebimento_pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'GET':
        # Mostra formulário
        return render(request, 'compras/faturar_recebimento.html', context)
    
    # POST - Processar
    numero_nf = request.POST.get('numero_nf')
    valor_nf = Decimal(request.POST.get('valor_nf'))
    num_parcelas = int(request.POST.get('num_parcelas'))
    dias_intervalo = int(request.POST.get('dias_intervalo'))
    
    # Atualizar recebimento
    recebimento.nota_fiscal = numero_nf
    recebimento.valor_total_nf = valor_nf
    recebimento.status = 'FINALIZADO'
    recebimento.save()
    
    # Criar ContaPagar
    conta = ContaPagar.objects.create(
        empresa=request.user.empresa,
        fornecedor=recebimento.fornecedor,  # ← Do recebimento!
        numero=f"NF-{numero_nf}",
        valor_total=valor_nf,
        # ... outros campos
    )
    
    # Criar parcelas
    for parcela_num in range(1, num_parcelas + 1):
        data_vencimento = recebimento.data_recebimento + timedelta(
            days=dias_intervalo * parcela_num
        )
        valor_parcela = valor_nf / num_parcelas
        
        ParcelaContaPagar.objects.create(
            conta_pagar=conta,
            numero_parcela=parcela_num,
            valor_parcela=valor_parcela,
            data_vencimento=data_vencimento,
            status='ABERTA'
        )
    
    return redirect('financeiro:conta_pagar_detail', pk=conta.id)
```

### 2. URLs (urls.py)

```python
# Compras
path('recebimentos/<int:recebimento_pk>/faturar/', 
     views_simples.faturar_recebimento, 
     name='faturar_recebimento'),

# Financeiro (já existe)
path('contas/<int:pk>/', 
     conta_pagar_detail, 
     name='conta_pagar_detail'),
```

### 3. Template (faturar_recebimento.html)

```html
<form method="POST">
    {% csrf_token %}
    
    <!-- Seção 1: Dados da NF -->
    <input type="text" name="numero_nf" required />
    <input type="date" name="data_emissao" required />
    <input type="number" name="valor_nf" required />
    
    <!-- Seção 2: Parcelamento -->
    <div id="parcelamento">
        <label>
            <input type="radio" name="parcelamento" value="0" />
            1x à vista
        </label>
        ...
    </div>
    
    <!-- JavaScript para preview -->
    <div id="preview_table">
        Parcela #1: 04/04 - R$ 3.333,33
        Parcela #2: 04/05 - R$ 3.333,33
        ...
    </div>
    
    <button type="submit">Criar Conta a Pagar</button>
</form>
```

---

## 📋 CAMPOS OBRIGATÓRIOS POR ETAPA

### Compra Rápida
```
POST /compras/compra-rapida/
Required:
  - fornecedor_id ✓
  - produto_id[] ✓
  - quantidade[] ✓
  - preco[] ✓
```

### Recebimento
```
POST /compras/recebimento-rapido/
Required:
  - fornecedor_id ✓
  - armazem_id ✓
  - produto_id[] ✓
  - quantidade[] ✓
  - preco[] ✓
```

### Faturamento → Conta a Pagar
```
POST /compras/recebimentos/<id>/faturar/
Required:
  - numero_nf ✓
  - data_emissao ✓
  - valor_nf ✓
  - num_parcelas (de 1-12)
  - dias_intervalo (intervalo entre parcelas)
```

---

## 🔄 PARCELAMENTO AUTOMÁTICO

### Opções Configuradas

| Opção | Fórmula | Exemplo |
|-------|---------|---------|
| 1x à vista | 1 parcela, 0 dias | Hoje |
| 2x 30 dias | 2 parcelas, 30d intervalo | 04/04, 05/04 |
| 3x 30 dias | 3 parcelas, 30d intervalo | 04/04, 05/04, 06/04 |
| 4x 30 dias | 4 parcelas, 30d intervalo | 04/04, 05/04, 06/04, 07/04 |
| Customizado | User define | Ex: 6 parcelas, 15 dias |

### Cálculo das Datas

```python
# Cada parcela tem data diferente
data_vencimento = data_recebimento + (dias_intervalo * numero_parcela)

# Exemplo: Recebimento 05/03, 3x 30 dias
# Parcela 1: 05/03 + (30*1) = 04/04
# Parcela 2: 05/03 + (30*2) = 05/05
# Parcela 3: 05/03 + (30*3) = 05/06
```

### Cálculo dos Valores

```python
# Cada parcela tem valor igual
valor_parcela = valor_total_nf / numero_parcelas

# Exemplo: R$ 10.000 em 3 parcelas
# Parcela 1: 10.000 / 3 = 3.333,33
# Parcela 2: 10.000 / 3 = 3.333,33
# Parcela 3: 10.000 / 3 = 3.333,34 (ajuste de arredondamento)
```

---

## 🎯 MULTI-TENANT (ISOLAMENTO POR EMPRESA)

Cada etapa respeita o isolamento:

```python
# Compra
PedidoCompra.objects.filter(empresa=request.user.empresa)

# Recebimento
RecebimentoCompra.objects.filter(empresa=request.user.empresa)

# Conta a Pagar
ContaPagar.objects.create(
    empresa=request.user.empresa,  # ← SEMPRE!
    ...
)
```

---

## 🔐 PERMISSÕES

```
COMPRADOR
├─ Criar pedidos (view: compra_rapida)
├─ Receber mercadoria (view: recebimento_rapido)
└─ Registrar NF (view: faturar_recebimento)

GERENTE FINANCEIRO
├─ Aprovar contas (view: conta_pagar_aprovar)
├─ Registrar pagamento (view: parcela_pagar)
└─ Gerar relatórios (views: relatorio_vencidas, etc)

DIRETOR
└─ Acesso para tudo (sem restrições)
```

---

## ✅ VALIDAÇÕES IMPLEMENTADAS

### View de Faturamento

```python
# 1. Verificar status do recebimento
if recebimento.status not in ['CONFERIDO', 'PENDENTE']:
    raise ValidationError("Recebimento não está pronto")

# 2. Verificar se fornecedor existe
if not fornecedor:
    raise ValidationError("Fornecedor é obrigatório")

# 3. Verificar valor
if valor_nf <= 0:
    raise ValidationError("Valor deve ser maior que zero")

# 4. Verificar número de parcelas
if not (1 <= num_parcelas <= 12):
    raise ValidationError("Deve ter entre 1 e 12 parcelas")
```

---

## 📊 HISTÓRICO E RASTREABILIDADE

Cada conta a pagar guarda:
- `observacoes`: "Gerada automaticamente do recebimento REC-00001"
- `data_emissao`: Data exata da NF
- Vinculação com fornecedor
- Vinculação com empresa

**Rastreamento completo:**
```
PedidoCompra #00001 
  ↓ (referência em)
RecebimentoCompra #REC-00001
  ↓ (gera)
ContaPagar #CP-123456
  ├─ ParcelaContaPagar #1
  ├─ PagamentoContaPagar #1 (quando paga)
  ├─ ParcelaContaPagar #2
  └─ PagamentoContaPagar #2 (quando paga)
```

---

## 🧪 TESTE MANUAL

### Cenário: Compra de R$ 10.000 em 3x 30 dias

```bash
# 1. Criar Compra
POST /compras/compra-rapida/
fornecedor=DISTRIBUIDORA SILVA
produto_id=[5, 6, 7]
quantidade=[10, 20, 30]
preco=[100, 200, 300]
# Resultado: PedidoCompra #00001 criado ✓

# 2. Registrar Recebimento
GET /compras/recebimentos/1/conferir/
POST (conferir)
# Resultado: RecebimentoCompra #REC-00001 ✓

# 3. Dar entrada no estoque
POST /compras/recebimentos/1/entrada-estoque/
# Resultado: Lotes criados, status=FINALIZADO ✓

# 4. Faturar
GET /compras/recebimentos/1/faturar/
POST /compras/recebimentos/1/faturar/
numero_nf=123456
data_emissao=2026-03-05
valor_nf=10000.00
parcelamento=30 (opção 3x)
num_parcelas=3
dias_intervalo=30
# Resultado: ContaPagar #CP-123456 criada ✓

# 5. Verificar no Financeiro
GET /financeiro/contas/1/
# Mostra:
# ├─ Conta aberta
# ├─ Parcela 1: 04/04, R$ 3.333,33
# ├─ Parcela 2: 05/05, R$ 3.333,33
# └─ Parcela 3: 06/05, R$ 3.333,34 ✓

# 6. Aprovar Conta
POST /financeiro/contas/1/aprovar/
# Status: ABERTA → APROVADA ✓

# 7. Pagar Parcela 1
POST /financeiro/parcelas/1/pagar/
valor_pago=3333.33
forma_pagamento=TED
data_pagamento=2026-04-04
# Resultado: PagamentoContaPagar criado, status=PENDENTE ✓
# (Após 2 dias úteis, banco compensa)
# Status: COMPENSADO, Parcela: PAGA ✓
```

---

## 🚀 PRÓXIMAS MELHORIAS

- [ ] Integração com API de bancos (compensação automática)
- [ ] PDF automático da notificação de faturamento
- [ ] Sincronização com sistema de impostos (NF-e)
- [ ] Importação em lote de NFs
- [ ] Dashboard de reconciliação compra vs financeiro

---

## 📞 DEBUGGING

### Se ContaPagar não foi criada
```python
# Verificar:
1. RecebimentoCompra.status é CONFERIDO ou PENDENTE?
2. RecebimentoCompra.fornecedor é None?
3. Valor_nf é > 0?
4. Não houve erro de permissão (empresa diferente)?

# Debug:
from compras.models import RecebimentoCompra
r = RecebimentoCompra.objects.get(pk=1)
print(f"Status: {r.status}")
print(f"Fornecedor: {r.fornecedor}")
print(f"Valor: {r.valor_total_nf}")
print(f"Empresa: {r.empresa}")
```

### Parcelas não aparecem
```python
from financeiro.models import ParcelaContaPagar
parcelas = ParcelaContaPagar.objects.filter(conta_pagar_id=1)
for p in parcelas:
    print(f"Parcela {p.numero_parcela}: {p.data_vencimento} - R$ {p.valor_parcela}")
```

---

## 📚 REFERÊNCIAS

- [Modelo PedidoCompra](compras/models.py)
- [Modelo RecebimentoCompra](compras/models.py)
- [Modelo ContaPagar](financeiro/models.py)
- [Modelo ParcelaContaPagar](financeiro/models.py)
- [View faturar_recebimento](compras/views_simples.py)
- [Template faturamento](compras/templates/compras/faturar_recebimento.html)
