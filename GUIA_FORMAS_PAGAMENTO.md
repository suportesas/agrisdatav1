# 💳 Sistema Profissional de Formas de Pagamento

## Visão Geral

O sistema foi atualizado para incluir um **módulo profissional de formas de pagamento** que permite:

✅ **Gerar automaticamente parcelas** ao informar o número desejado
✅ **Selecionar forma de pagamento** (PIX, Boleto, Transferência, etc) para cada parcela
✅ **Calcular automaticamente** datas (30 dias por padrão) e valores de cada parcela
✅ **Gerenciar 7 formas profissionais**: PIX, Transferência, Boleto, Cheque, Dinheiro, Cartão, Crediário

---

## 🎯 Como Funciona

### 1. **Fluxo de Uso**

```
Recebimento Conferido → Registrar NF → Informar Parcelas → Selecionar Formas → Conta a Pagar Criada
                                                              ↓
                                                    PIX/Boleto/Transferência etc
```

### 2. **Passo a Passo**

#### **Passo 1: Acessar o Formulário**
- Vá para o recebimento conferido
- Clique em "Registrar Nota Fiscal"
- URL: `/compras/recebimentos/<id>/faturar/`

#### **Passo 2: Informar Dados da NF**
```
Campos Obrigatórios:
├─ Número da NF        (Ex: 123456)
├─ Data de Emissão     (Ex: 01/03/2026)
└─ Valor da NF         (Ex: 10.000,00)

Campos Opcionais:
├─ Série NF            (Padrão: 1)
└─ Observações
```

#### **Passo 3: Gerar Parcelas Automaticamente**
```
1. Informe o número de parcelas (1-12)
   └─ Sistema calcula automaticamente:
      • Datas de vencimento (30 dias cada)
      • Valores por parcela (distribuição uniforme)
      • Última parcela ajusta centavos

2. Exemplos:
   ├─ 1 parcela  → R$ 10.000,00 à vista
   ├─ 2 parcelas → R$ 5.000,00 cada (30 dias)
   ├─ 3 parcelas → R$ 3.333,33 cada (30 dias)
   └─ 4 parcelas → R$ 2.500,00 cada (30 dias)
```

#### **Passo 4: Selecionar Forma de Pagamento**
```
Opções Disponíveis (7 Formas Profissionais):

1️⃣  PIX
    └─ Transferência instantânea
    └─ Processamento: Imediato (0 dias)
    └─ Taxa: 0%

2️⃣  Transferência Bancária
    └─ TED ou DOC
    └─ Processamento: 1-2 dias úteis
    └─ Taxa: 0%

3️⃣  Boleto
    └─ Boleto bancário
    └─ Processamento: 3 dias úteis
    └─ Taxa: 1.5%

4️⃣  Cheque
    └─ Cheque pré-datado ou à vista
    └─ Processamento: 1 dia útil
    └─ Taxa: 0.5%

5️⃣  Dinheiro
    └─ Pagamento em espécie
    └─ Processamento: Imediato
    └─ Taxa: 0%

6️⃣  Cartão de Crédito
    └─ Cartão de crédito
    └─ Processamento: 1-2 dias úteis
    └─ Taxa: 2.5%

7️⃣  Crediário
    └─ Crediário próprio da empresa
    └─ Processamento: Imediato
    └─ Taxa: 5%

Como Selecionar:
├─ Forma Padrão: Selecionar 1 forma que será aplicada a TODAS as parcelas
└─ Forma Individual: Cada parcela pode ter sua própria forma (tabela abaixo)
```

#### **Passo 5: Preview e Confirmação**
Sistema mostra tabela com:
- ✓ Número da parcela
- ✓ Data de vencimento
- ✓ Valor (R$)
- ✓ Forma de pagamento selecionada
- ✓ Total consolidado

```
EXEMPLO DE PREVIEW:

Parc. | Vencimento | Valor (R$)  | Forma de Pagamento
------|------------|-------------|-------------------
  #1  | 01/04/2026 | 3.333,33   | PIX
  #2  | 01/05/2026 | 3.333,33   | Boleto
  #3  | 02/06/2026 | 3.333,34   | Transferência Bancária
      |            | TOTAL: 10.000,00
```

---

## 🛠️ Características Técnicas

### **Modelos de Dados**

#### **FormaPagemento** (Novo)
```python
class FormaPagemento(models.Model):
    nome                 # PIX, Boleto, Transferência, etc
    descricao           # Instruções / notas
    ativo               # Ativa/inativa forma
    dias_processamento  # Dias úteis para processar
    taxa_administrativa # % de taxa sobre pagamento
    ordem_exibicao      # Ordem na lista
```

#### **ParcelaContaPagar** (Atualizado)
```python
class ParcelaContaPagar(models.Model):
    # ... campos existentes ...
    forma_pagamento     # ✨ NOVO: FK para FormaPagemento
```

### **View Atualizada**

**`faturar_recebimento(request, recebimento_pk)`**

Funcionalidades:
- GET: Renderiza formulário com formas de pagamento disponíveis
- POST: 
  - Valida dados (NF, data, valor)
  - Cria ContaPagar automaticamente
  - Gera ParcelaContaPagar com forma de pagamento
  - Calcula datas (30 dias cada)
  - Distribui valor uniformemente
  - Ajusta última parcela para não haver centavos

```python
# Pseudocódigo
for i in range(1, num_parcelas + 1):
    if i == num_parcelas:
        valor = valor_total - acumulado  # Ajusta centavos
    else:
        valor = valor_total / num_parcelas
    
    data_vencimento = data_receb + (30 * (i-1)) dias
    
    ParcelaContaPagar.create(
        numero_parcela=i,
        valor_parcela=valor,
        data_vencimento=data_vencimento,
        forma_pagamento=forma_selecionada
    )
```

### **Template Melhorado**

JavaScript dinâmico que:
- ✓ Recalcula parcelas em tempo real (onchange/oninput)
- ✓ Gera tabela preview automaticamente
- ✓ Sincroniza forma de pagamento para todas (ou individual)
- ✓ Valida número de parcelas (1-12)
- ✓ Formata valores em Real (BR)
- ✓ Calcula datas corretamente

---

## 📦 Dados Padrão Criados

Ao instalar, 7 formas são criadas automaticamente:

```
✅ PIX              (Taxa: 0%)     - Processamento: 0 dias
✅ Transferência    (Taxa: 0%)     - Processamento: 1 dia
✅ Boleto           (Taxa: 1.5%)   - Processamento: 2 dias
✅ Cheque           (Taxa: 0.5%)   - Processamento: 1 dia
✅ Dinheiro         (Taxa: 0%)     - Processamento: 0 dias
✅ Cartão Crédito   (Taxa: 2.5%)   - Processamento: 1 dia
✅ Crediário        (Taxa: 5%)     - Processamento: 0 dias
```

Execute para criar:
```bash
py criar_formas_pagamento.py
```

---

## 🎮 Testando o Sistema

### **1. Via Admin Django**

- Acesse: `/admin/financeiro/formapagemento/`
- Visualize / edite as 7 formas
- Adicione novas formas conforme necessário

### **2. Via Aplicação**

```bash
# Testando
1. Crie um pedido rápido
2. Receba o pedido e confira
3. Clique "Registrar Nota Fiscal"
4. Informe:
   - Número NF: 123456
   - Data: Hoje
   - Valor: 1.000,00
   - Parcelas: 3
   - Forma Padrão: PIX
5. Confira preview
6. Clique "Criar Conta a Pagar"
7. Verifique em Financeiro
```

### **3. Via Código**

```python
from financeiro.models import FormaPagemento, ParcelaContaPagar

# Listar formas
formas = FormaPagemento.objects.filter(ativo=True)
# Resultado: 7 formas

# Buscar por nome
pix = FormaPagemento.objects.get(nome='PIX')
# Resultado: FormaPagemento(PIX, taxa=0%, dias=0)

# Parcela com forma
parcela = ParcelaContaPagar.objects.create(
    conta_pagar=conta,
    numero_parcela=1,
    valor_parcela=500.00,
    data_vencimento='2026-04-01',
    forma_pagamento=pix
)
```

---

## 📊 Casos de Uso

### **Caso 1: Compra à Vista (PIX)**
```
NF: 100.000,00
├─ 1 parcela
├─ Forma: PIX
├─ Vencimento: Hoje (à vista)
└─ Status: Criada e pronta para pagar
```

### **Caso 2: Compra Parcelada (Boleto)**
```
NF: 30.000,00
├─ 3 parcelas
├─ Valores: 10.000,00 cada
├─ Datas: 30, 60, 90 dias
├─ Forma: Boleto (todas)
└─ Total de Boletos: 3
```

### **Caso 3: Compra com Múltiplas Formas**
```
NF: 50.000,00
├─ 2 parcelas
├─ Parcela 1 (25.000,00): Vencimento 30d | Forma: Transferência
├─ Parcela 2 (25.000,00): Vencimento 60d | Forma: Boleto
└─ Sistema registra forma diferente para cada
```

---

## 🔒 Validações Implementadas

```python
# Validações automáticas
✓ Número de parcelas entre 1-12
✓ Valor da NF > 0
✓ Data de emissão obrigatória
✓ NF não pode duplicar
✓ Última parcela ajusta centavos
✓ Datas calculadas corretamente (30 dias)
✓ Isolamento por empresa (multi-tenant)
✓ Forma de pagamento obrigatória por parcela
```

---

## 🚀 Melhorias Futuras

```
Fase 2:
├─ Relatório de contas por forma de pagamento
├─ Alertas de formas específicas (boleto, feriado)
├─ Integração com gateway de pagamento (PIX automático)
├─ Whatsapp com link de pagamento (Boleto)
├─ Renegociação com mudança de forma
├─ Histórico de formas usadas por fornecedor
└─ Dashboard de formas mais usadas
```

---

## 📝 Resumo das Mudanças

### **Arquivos Criados**
- ✅ Modelo `FormaPagemento` em `financeiro/models.py`
- ✅ Admin para `FormaPagemento` em `financeiro/admin.py`
- ✅ Script `criar_formas_pagamento.py` (dados iniciais)
- ✅ Documentação `GUIA_FORMAS_PAGAMENTO.md`

### **Arquivos Atualizados**
- ✅ `compras/views_simples.py` - View com suporte a formas
- ✅ `compras/templates/faturar_recebimento.html` - Template aprimorado
- ✅ `financeiro/models.py` - Novo campo em ParcelaContaPagar
- ✅ Migration `0002_formapagemento_parcelacontapagar_forma_pagamento.py`

### **Funcionalidades Novas**
- ✅ 7 formas de pagamento profissionais
- ✅ Geração automática de parcelas
- ✅ Seleção de forma por parcela
- ✅ Preview em tempo real
- ✅ Cálculo automático de datas e valores
- ✅ Admin para gerenciar formas

---

## 🎯 Próximos Passos

1. **Testar o sistema completo**
   ```bash
   py test_parcelamento_profissional.py
   ```

2. **Adicionar novas formas (se necessário)**
   - Via Admin Django: `/admin/financeiro/formapagemento/`
   - Via código: `FormaPagemento.objects.create(...)`

3. **Integrar com módulo de pagamentos**
   - Criar view para agendar pagamentos por forma
   - Separar fluxo por forma (CNAB para boleto, API para PIX, etc)

4. **Criar relatórios**
   - Contas por forma de pagamento
   - Taxa média por forma
   - Prazos de processamento

---

**Versão:** 2.0 | **Data:** 03/03/2026 | **Status:** ✅ Produção
