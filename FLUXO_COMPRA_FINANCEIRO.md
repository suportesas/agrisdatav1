# 🛒 FLUXO COMPLETO DE COMPRA E INTEGRAÇÃO COM FINANCEIRO

## 📊 Visão Geral do Processo

```
COMPRA ➜ RECEBIMENTO ➜ FATURAMENTO ➜ CONTAS A PAGAR ➜ PAGAMENTO
  ↓         ↓             ↓              ↓                ↓
PEDIDO   ESTOQUE      NF gerada      Parcelas        Liquidação
```

---

## ⚡ MODO 1: COMPRA RÁPIDA (Simples)

### 1️⃣ Criação da Compra Rápida
```
URL: /compras/compra-rapida/
```

**Dados de Entrada:**
- Fornecedor (obrigatório)
- Produtos + Quantidades + Preços
- Data de entrega prevista

**Ações no Sistema:**
```python
# compras/views_simples.py
pedido = PedidoCompra.objects.create(
    empresa=request.user.empresa,
    fornecedor=fornecedor_selecionado,
    comprador=request.user,
    status='PENDENTE_RECEBIMENTO',
    cotacao=None,  # ← SEM COTAÇÃO (modo simples)
    data_entrega_prevista=timezone.now().date() + timedelta(days=7)
)

# Criar itens do pedido
ItemPedidoCompra.objects.create(
    pedido=pedido,
    produto=produto,
    quantidade_pedida=quantidade,
    preco_unitario=preco,
    proposta_fornecedor=None  # ← SEM PROPOSTA (modo simples)
)
```

**Status do Pedido:** 🟡 PENDENTE_RECEBIMENTO

**Documentos Adicionais:**
- PDF do pedido pode ser gerado e enviado via email

---

### 2️⃣ Recebimento da Mercadoria
```
URL: /compras/pedido/<id>/receber/
```

**Dados de Entrada:**
- Quantidade recebida (pode ser parcial)
- Local de estoque (Armazém)
- Número do lote

**Ações no Sistema:**
```python
# compras/views.py
recebimento = RecebimentoCompra.objects.create(
    empresa=request.user.empresa,
    pedido=pedido,
    data_recebimento=timezone.now(),
    status='PENDENTE_NOTA'  # Aguarda NF
)

# Para cada item pedido
ItemRecebimento.objects.create(
    recebimento=recebimento,
    item_pedido=item_pedido,
    produto=item_pedido.produto,
    quantidade_recebida=quantidade_recebida,
    local_estoquagem=local_escolhido
)

# Automático: Cria lote no estoque
lote = Lote.objects.create(
    empresa=request.user.empresa,
    produto=item_pedido.produto,
    numero_lote=f"AUTO-{timestamp}",
    quantidade_inicial=quantidade_recebida,
    quantidade_atual=quantidade_recebida,
    status='DISPONIVEL'
)
```

**Status do Recebimento:** 🟡 PENDENTE_NOTA

**Estoque Atualizado:**
- Lote criado e disponível para uso
- Quantidade refletida no saldo

---

### 3️⃣ Recebimento da Nota Fiscal
```
URL: /compras/recebimento/<id>/fatura/
```

**Dados de Entrada:**
- Número da NF
- Série
- Data de emissão
- CFOP
- Valor total NF
- Parcelas e datas de vencimento

**Ações no Sistema:**
```python
# compras/models.py - RecebimentoCompra.save()
recebimento = RecebimentoCompra.objects.create(
    numero_nf=numero_nf,
    serie_nf=serie,
    data_emissao_nf=data_nf,
    valor_nf=valor_total,
    status='FINALIZADO'
)
```

**Status do Recebimento:** ✅ FINALIZADO

---

## 💰 INTEGRAÇÃO COM MÓDULO FINANCEIRO

### 4️⃣ Criação Automática de Conta a Pagar

Quando a **Nota Fiscal é registrada**, o sistema cria automaticamente uma **ContaPagar**:

```python
# financeiro/signals.py (ou view de faturamento)
from django.db.models.signals import post_save

@receiver(post_save, sender=RecebimentoCompra)
def criar_conta_pagar(sender, instance, created, **kwargs):
    """
    Quando recebimento é finalizado com NF,
    cria ContaPagar automaticamente
    """
    if instance.status == 'FINALIZADO' and instance.numero_nf:
        
        # 1. Criar ContaPagar
        conta = ContaPagar.objects.create(
            empresa=instance.empresa,
            fornecedor=instance.pedido.fornecedor,
            numero=f"CP-{instance.numero_nf}",  # Referencia a NF
            valor_total=instance.valor_nf,
            desconto_negociado=0,  # Pode ser ajustado depois
            data_emissao=instance.data_emissao_nf,
            requer_aprovacao=True,  # Define fluxo de aprovação
            observacoes=f"Referência NF: {instance.numero_nf}"
        )
        
        # 2. Criar ParcelaContaPagar baseado em condicoes_pagamento
        condicao = instance.pedido.condicao_pagamento
        # Ex: "1x à vista" = 1 parcela
        # Ex: "3x 30 dias" = 3 parcelas com 30d de intervalo
        
        for num_parcela in range(1, condicao.numero_parcelas + 1):
            data_vencimento = instance.data_emissao_nf + timedelta(
                days=condicao.dias_intervalo * num_parcela
            )
            
            valor_parcela = instance.valor_nf / condicao.numero_parcelas
            
            ParcelaContaPagar.objects.create(
                conta_pagar=conta,
                numero_parcela=num_parcela,
                valor_parcela=valor_parcela,
                data_vencimento=data_vencimento,
                status='ABERTA'  # Pronta para aprovação
            )
        
        print(f"✅ ContaPagar criada: {conta.numero}")
        print(f"   Fornecedor: {conta.fornecedor.nome}")
        print(f"   Valor: R$ {conta.valor_total:,.2f}")
        print(f"   Parcelas: {condicao.numero_parcelas}")
```

**Dados Copiados Automaticamente:**
| Origem | Destino | Campo |
|--------|---------|-------|
| RecebimentoCompra | ContaPagar | empresa, fornecedor, valor_total, data_emissão |
| ItemRecebimento | - | Itens da NF (rastreabilidade) |
| PedidoCompra | ContaPagar | Condições de pagamento |

---

### 5️⃣ Fluxo de Aprovação da Conta a Pagar

#### Status: 🟡 ABERTA → 🟦 APROVADA

```
Conte a Pagar (ABERTA)
    ↓
Validação de Dados:
  ✓ Conferência: NF confere com Pedido?
  ✓ Preço confere com Proposta?
  ✓ Descrição de itens bate?
    ↓
[Se ok] ➜ Aprovar Conta
    ↓
Conta Status = APROVADA
Parcelas Status = ABERTA (prontas para pagar)
```

**URL de Aprovação:**
```
/financeiro/contas/<id>/aprovar/
```

**Ação:**
```python
# financeiro/views.py
@login_required
def conta_pagar_aprovar(request, pk):
    conta = get_object_or_404(ContaPagar, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm')
        if confirm == 'on':
            conta.status = 'APROVADA'
            conta.data_aprovacao = timezone.now()
            conta.aprovador = request.user
            conta.save()
            
            messages.success(request, f'Conta {conta.numero} aprovada!')
            
            # Atualiza status das parcelas
            conta.parcelas.filter(status='ABERTA').update(status='ABERTA')
            
            return redirect('financeiro:conta_pagar_detail', pk=conta.id)
    
    # Renderiza template com confirmação
    return render(request, 'financeiro/conta_pagar_confirm.html', {'conta': conta})
```

---

### 6️⃣ Cálculo de Juros e Multa (Se Passar do Vencimento)

A **cada acesso ao sistema**, as parcelas vencidas recalculam:

```python
# financeiro/models.py - ParcelaContaPagar

def save(self, *args, **kwargs):
    """Recalcula dias de atraso e juros/multa ao salvar"""
    
    if self.data_pagamento is None:
        # Parcela ainda não foi paga
        self.dias_atraso = (timezone.now().date() - self.data_vencimento).days
        
        if self.dias_atraso > 0:
            # Passou do vencimento - aplica juros e multa
            self.status = 'VENCIDA'
            
            config = self.conta_pagar.empresa.configuracaojurosmulta
            
            # Cálculo de juros (juros compostos)
            taxa_mensal = config.taxa_juros_mensal / 100
            dias_decorridos = self.dias_atraso
            
            self.juros_parcela = (
                self.valor_parcela * 
                ((1 + taxa_mensal) ** (dias_decorridos / 30) - 1)
            )
            
            # Cálculo de multa (percentual fixo ou por dia)
            if config.tipo_multa == 'PERCENTUAL':
                self.multa_parcela = self.valor_parcela * (config.multa_atraso / 100)
            else:  # POR_DIA
                self.multa_parcela = self.valor_parcela * (config.multa_atraso / 100) * dias_decorridos
        
        # Recalcula total
        self.valor_total_parcela = (
            self.valor_parcela + 
            self.juros_parcela + 
            self.multa_parcela
        )
    
    super().save(*args, **kwargs)
```

**Exemplo no Dashboard:**
```
Parcela #1 - Vencida há 5 dias
├─ Valor Original: R$ 1.000,00
├─ Juros (5 dias @ 2% mês): R$ 3,33
├─ Multa (2% fixa): R$ 20,00
└─ Total: R$ 1.023,33  ← Valor a pagar AGORA
```

---

### 7️⃣ Pagamento da Parcela

#### Status: 🟡 ABERTA → ✅ PAGA

```
URL: /financeiro/parcelas/<id>/pagar/
```

**Dados de Entrada:**
- Valor a pagar (sugerido: valor com juros/multa)
- Forma de pagamento (Dinheiro, Boleto, TED, Cartão, Cheque, PIX)
- Número do documento (cheque, boleto, TED)
- Banco
- Comprovante (PDF/Imagem)

**Ações no Sistema:**
```python
# financeiro/views.py
@login_required
def parcela_pagar(request, pk):
    parcela = get_object_or_404(ParcelaContaPagar, pk=pk)
    
    if request.method == 'POST':
        # 1. Criar registro de pagamento
        pagamento = PagamentoContaPagar.objects.create(
            parcela=parcela,
            valor_pago=Decimal(request.POST['valor_pago']),
            forma_pagamento=request.POST['forma_pagamento'],
            data_pagamento=request.POST['data_pagamento'],
            numero_documento=request.POST.get('numero_documento'),
            banco=request.POST.get('banco'),
            comprovante=request.FILES.get('comprovante'),
            status='PENDENTE'  # Aguarda compensação
        )
        
        # 2. Atualizar parcela
        parcela.data_pagamento = timezone.now()
        parcela.status = 'PAGA'
        parcela.save()
        
        # 3. Atualizar ContaPagar (pode estar totalmente paga)
        conta = parcela.conta_pagar
        if conta.parcelas.filter(status__in=['ABERTA', 'VENCIDA']).count() == 0:
            conta.status = 'PAGA'
            conta.save()
        
        return redirect('financeiro:conta_pagar_detail', pk=conta.id)
```

**Fluxo de Compensação:**
```
Pagamento Status = PENDENTE (enviado para banco)
    ↓ (após 1-2 dias úteis)
Pagamento Status = COMPENSADO (confirmado no banco)
    ↓
Parcela Status = PAGA
ContaPagar Status = PAGA (quando todas as parcelas pagas)
```

---

## 📊 RELATÓRIOS DO FINANCEIRO

### Dashboard Financeiro
```
URL: /financeiro/
```

**Mostra:**
- 📈 KPIs: Total a pagar, Pagas, Juros acumulados, Multas
- ⚠️ Alertas: Parcelas vencidas, próximas 7 dias
- 📋 Tabelas: Próximas parcelas, vencidas, fornecedores com maiores débitos

### Contas a Vencer
```
URL: /financeiro/relatorios/vencer/
```

**Mostra:**
- Próximas 30 dias de vencimentos
- Agrupado por data
- Permite exportar para CSV/PDF
- Botão para pagar direto

### Contas Vencidas
```
URL: /financeiro/relatorios/vencidas/
```

**Mostra:**
- Todas as parcelas vencidas
- Dias de atraso
- Juros e multas acumuladas
- Gráfico de distribuição de atraso (1-7d, 8-30d, 30-90d, 90+d)

### Fluxo de Caixa
```
URL: /financeiro/relatorios/fluxo-caixa/
```

**Mostra:**
- Saída de caixa por mês
- Valor previsto vs. já pago
- Gráfico de tendência
- Distribuição por fornecedor
- Exportação para Excel

---

## 🔄 FLUXO COMPLETO - TIMELINE VISUAL

```
DIA 1: Segunda-feira
  09:00 - Cria Pedido de Compra (00001)
            Fornecedor: DISTRIBUIDORA SILVA
            4x produtos
            Total: R$ 10.000,00
           
  15:00 - Pedido enviado para fornecedor ✉️

DIA 3: Quarta-feira
  10:00 - Mercadoria chega no armazém 📦
          Cria Recebimento
          Quantidade confere
          Lote criado: LOTE-202603-001
          Status: PENDENTE_NOTA

DIA 5: Sexta-feira
  14:00 - Nota Fiscal recebida 📄
          NF: 123456 / Série A
          Registra no Recebimento
          Status: FINALIZADO
          
  14:05 - ⚙️ AUTOMÁTICO - Cria ContaPagar
          CP-123456
          Fornecedor: DISTRIBUIDORA SILVA
          Valor: R$ 10.000,00
          Condição: 3x 30 dias
          Parcelas criadas:
            #1 - R$ 3.333,33 - Vence 04/04 (10d)
            #2 - R$ 3.333,33 - Vence 04/05 (40d)
            #3 - R$ 3.333,34 - Vence 04/06 (70d)

DIA 6: Sábado
  10:00 - Gerente acessa financeiro.
          Vê CP-123456 em ABERTA
          Confere tudo correto
          Clica "Aprovar Conta"
          Status: APROVADA ✅

DIA 20: Quarta-feira (9 dias depois)
  09:00 - Dashboard mostra: Parcela #1 vencendo HOJE
          Clica "Pagar"
          
  09:15 - Registra pagamento:
          Forma: TED
          Valor: R$ 3.333,33
          Comprovante: PDF anexado
          Status: PENDENTE_COMPENSACAO

DIA 22: Sexta-feira (banco compensou)
  Pagamento Status: COMPENSADO ✅
  Parcela Status: PAGA
  
DIA 30: Quarta-feira (4ª próximo mês)
  Parcela #2 vence - repete processo
  
DIA 60: Sexta-feira (6ª próximo mês)
  Parcela #3 vence - repete processo

DIA 70: Segunda-feira (1ª mês seguinte)
  Última parcela paga
  ContaPagar Status: PAGA ✅
  Transação finalizada!
```

---

## ⚙️ CONFIGURAÇÕES POR EMPRESA

Cada empresa tem suas próprias **taxas de juros e multa**:

```
URL: /configuracao/juros-multa/

Configuração de Juros e Multa
├─ Taxa de Juros Mensal: 2.0%
├─ Multa por Atraso: 2.0%
├─ Tipo de Multa: PERCENTUAL ou POR_DIA
└─ Dias de Tolerância: 5 dias
```

---

## 🔐 PERMISSÕES & FLUXO DE APROVAÇÃO

```
USUÁRIOS:
├─ COMPRADOR
│  └─ Criar pedidos, receber mercadoria, registrar NF
│
├─ GERENTE FINANCEIRO
│  └─ Aprovar contas, pagar, gerar relatórios
│
└─ DIRETOR
   └─ Ver tudo, aprovações maiores, ajustes
```

---

## 📌 RESUMO: O QUE ACONTECE EM CADA ETAPA

| Etapa | Quem | Ação | Resultado |
|-------|------|------|-----------|
| **Compra** | Comprador | Cria pedido | PedidoCompra (PENDENTE_RECEBIMENTO) |
| **Recebimento** | Comprador | Registra chegada | RecebimentoCompra (PENDENTE_NOTA), Lote criado |
| **NF** | Admin/Financeiro | Registra NF | RecebimentoCompra (FINALIZADO) |
| **Auto: Conta** | Sistema | ⚙️ Automático | ContaPagar (ABERTA) + ParcelaContaPagar |
| **Aprovação** | Gerente | Aprova conta | ContaPagar (APROVADA) |
| **Pagamento** | Financeiro | Registra pgt | PagamentoContaPagar (PENDENTE) |
| **Compensação** | Sistema | ⚙️ Automático | PagamentoContaPagar (COMPENSADO), Parcela (PAGA) |

---

## 🎯 PRÓXIMAS IMPLEMENTAÇÕES

- [ ] Integração com API de bancos (compensação automática)
- [ ] Boleto integrado (gera boleto automaticamente)
- [ ] NFS-e integração
- [ ] Renegociação de parcelas (com novo contrato)
- [ ] Desconto para pagamento antecipado
- [ ] Notificações automáticas por email/WhatsApp (3d antes do vencimento)
- [ ] Portal do fornecedor (ver pedidos, confirmar entrega)
