# 🛒 GUIA RÁPIDO: COMPRA ATÉ CONTA A PAGAR

## 📱 Fluxo em 3 Passos Simples

```
PASSO 1          PASSO 2           PASSO 3              RESULTADO
┌─────────┐     ┌──────────┐      ┌─────────┐         ┌────────────┐
│ Compra  │ ──→ │Recebimen-│  ──→ │ Faturar │    ──→  │  Conta a   │
│ Rápida  │     │   to     │      │   (NF)  │         │   Pagar    │
└─────────┘     └──────────┘      └─────────┘         └────────────┘
 (Pedido)        (Mercadoria)      (Nota Fiscal)     (Parcelas)
```

---

## 🟢 PASSO 1: CRIAR COMPRA RÁPIDA

**URL:** `/compras/compra-rapida/`

### O que fazer:
1. Clique em **"Nova Compra Rápida"**
2. Preencha:
   - **Fornecedor** (obrigatório)
   - **Produtos** a adicionar (clique em "Adicionar Linha")
   - **Quantidade** de cada produto
   - **Preço unitário** de cada produto
3. Clique em **"Criar Pedido"**

### O que acontece:
✅ Pedido criado com número automático (ex: #00001)
✅ Data de entrega prevista = 7 dias a partir de hoje
✅ Status: 🟡 PENDENTE_RECEBIMENTO

### Resultado:
- Você vê a página com detalhes do pedido
- Próximo passo: Registrar o recebimento quando a mercadoria chegar

---

## 📦 PASSO 2: REGISTRAR RECEBIMENTO

**URL:** `/compras/recebimentos/<id>/`

### Quando fazer:
Assim que a mercadoria chegar no armazém.

### O que fazer:
1. Acesse o detalhe do pedido
2. Clique em **"Dar entrada no estoque"**
   - Selecione o **Armazém**
   - Clique em **"Conferir Recebimento"** primeiro se ainda não conferiu

### O que acontece:
✅ Recebimento criado com número automático
✅ Lote é criado automaticamente no estoque
✅ Mercadoria fica disponível para uso
✅ Status: 🟡 CONFERIDO → 🟢 FINALIZADO

### Resultado:
- Você tem um "Recebimento #00001"
- Agora vê dois botões:
  - **"Registrar Nota Fiscal"** (para criar conta a pagar)
  - **"Avaliar Fornecedor"** (opcional)

---

## 📄 PASSO 3: REGISTRAR NOTA FISCAL → CRIA CONTA A PAGAR

**URL:** `/compras/recebimentos/<id>/faturar/`

### Quando fazer:
Quando receber a Nota Fiscal do fornecedor.

### O que fazer:
1. Clique em **"Registrar Nota Fiscal"** (botão amarelo)
2. Preencha os dados da NF:
   - **Número da NF** (obrigatório) - ex: 123456
   - **Série** (padrão: 1)
   - **Data de Emissão** (obrigatório)
   - **Valor Total da NF** (obrigatório)

3. Escolha a **Condição de Pagamento**:
   - 🔘 **1x à vista** → Paga hoje
   - 🔘 **2x 30 dias** → 2 parcelas, cada 30 dias
   - 🔘 **3x 30 dias** → 3 parcelas, cada 30 dias
   - 🔘 **4x 30 dias** → 4 parcelas, cada 30 dias
   - 🔘 **Customizado** → Você define número de parcelas e dias

4. {VISUALIZE} A tabela mostra automaticamente:
   - Data de vencimento de cada parcela
   - Valor de cada parcela

5. Clique em **"Criar Conta a Pagar"**

### O que acontece - AUTOMÁTICO! ✨
```
Sistema CRIA:
  ✅ ContaPagar (#CP-123456)
  ✅ ParcelaContaPagar #1 (vence em X dias)
  ✅ ParcelaContaPagar #2 (vence em Y dias)
  ✅ ParcelaContaPagar #3 (vence em Z dias)
  
Tudo já vinculado ao fornecedor!
```

### Resultado:
- Você é redirecionado para a **tela de Conta a Pagar**
- Status da conta: 🟡 ABERTA
- Status das parcelas: 🟡 ABERTA

---

## 💰 PRÓXIMO PASSO: APROVAR E PAGAR

Agora você está no módulo financeiro!

### Aprovar a Conta
1. Na tela de detalhe da conta a pagar
2. Clique em **"Aprovar Conta"**
3. Confirme (checkbox)
4. Status muda: 🟡 ABERTA → 🟢 APROVADA

### Pagar a Parcela
1. Clique em **"Pagar"** na parcela
2. Preencha:
   - Valor a pagar (vem preenchido)
   - Forma de pagamento (Dinheiro, Boleto, TED, Cartão, Cheque, PIX)
   - Comprovante (PDF/Imagem)
3. Clique em **"Registrar Pagamento"**

Status muda: 🟡 PENDENTE → ✅ COMPENSADO → 🟢 PAGA

---

## 📊 EXEMPLO PRÁTICO COMPLETO

```
SEGUNDA-FEIRA - 09:00
├─ Acessa: /compras/compra-rapida/
├─ Cria: Pedido #00001
├─ Fornecedor: DISTRIBUIDORA SILVA
├─ 4x produtos
└─ Total: R$ 10.000,00

QUARTA-FEIRA - 14:00
├─ Mercadoria chega
├─ Clica: "Dar entrada no estoque"
├─ Cria: Recebimento #REC-00001
├─ Lote criado automaticamente
└─ Status: FINALIZADO ✅

SEXTA-FEIRA - 16:00
├─ Recebe NF: 123456
├─ Clica: "Registrar Nota Fiscal"
├─ Preenche:
│  ├─ NF: 123456
│  ├─ Data: 05/03/2026
│  ├─ Valor: R$ 10.000,00
│  └─ Parcelamento: 3x 30 dias
│
└─ Sistema CRIA automaticamente:
   ├─ ContaPagar #CP-123456
   ├─ Parcela 1: R$ 3.333,33 - Vence 04/04 🟡
   ├─ Parcela 2: R$ 3.333,33 - Vence 04/05 🟡
   └─ Parcela 3: R$ 3.333,34 - Vence 04/06 🟡

Gerente aprova a conta: 🟢 APROVADA

04/04 - Paga Parcela 1: TED → 🟢 PAGA
04/05 - Paga Parcela 2: TED → 🟢 PAGA  
04/06 - Paga Parcela 3: TED → 🟢 PAGA

FINALIZADO ✅✅✅
```

---

## 🎯 CHECKLIST RÁPIDO

### Compra Rápida ✓
- [ ] Fornecedor selecionado
- [ ] Produtos adicionados
- [ ] Preços informados
- [ ] Clique em "Criar Pedido"

### Recebimento ✓
- [ ] Mercadoria conferida
- [ ] Clique em "Dar entrada no estoque"
- [ ] Armazém selecionado

### Nota Fiscal → Conta Pagar ✓
- [ ] Número da NF preenchido
- [ ] Valor da NF correto
- [ ] Parcelamento escolhido
- [ ] Visualizou datas de vencimento
- [ ] Clique em "Criar Conta a Pagar"

### Aprovação & Pagamento ✓
- [ ] Conta foi para APROVADA
- [ ] Parcelas mostram vencimento correto
- [ ] Clique em "Pagar" quando vencer
- [ ] Registrou comprovante

---

## 🔗 LINKS RÁPIDOS

| Ação | URL |
|------|-----|
| Nova Compra | `/compras/compra-rapida/` |
| Meus Pedidos | `/compras/pedidos/` |
| Recebimentos | `/compras/recebimentos/` |
| Financeiro | `/financeiro/` |
| Contas a Pagar | `/financeiro/contas/` |
| Relatório de Vencidas | `/financeiro/relatorios/vencidas/` |

---

## ⚡ DICAS IMPORTANTES

### ✅ Boas Práticas
1. **Sempre confira** a mercadoria antes de dar entrada
2. **Registre a NF** o mais rápido possível (gera a conta automaticamente)
3. **Aprove a conta** antes da primeira parcela vencer
4. **Guarde comprovantes** de pagamento

### ⚠️ Atenção
- Se a parcela passar do vencimento, **juros e multa são aplicados automaticamente**
- Juros compostos + multa fixa = valor aumenta
- Contas aprovadas deixam as parcelas prontas para pagar

### 💡 Lembre-se
- Tudo é **automático** quando você confirma
- Não precisa criar manualmente a conta a pagar
- O sistema gera as parcelas baseado na sua escolha
- Cada empresa tem sua própria taxa de juros/multa

---

## 📞 SUPORTE

Alguma dúvida?
- Dashboard: `/` → Ver status das compras
- Relatórios: `/financeiro/relatorios/` → Ver contas vencidas/próximas
- Números não batem? Veja o histórico completo no detalhe da conta
