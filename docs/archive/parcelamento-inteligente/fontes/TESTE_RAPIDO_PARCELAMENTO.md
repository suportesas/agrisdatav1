# 🚀 GUIA DE TESTE RÁPIDO - SISTEMA DE PARCELAMENTO INTELIGENTE

## ⚡ 5 Minutos para Testar

### Passo 1: Iniciar Servidor (30 segundos)
```bash
cd c:\erp_agricola
py manage.py runserver
```

**Esperado:** "Starting development server at http://127.0.0.1:8000/"

---

### Passo 2: Acessar Sistema (30 segundos)
1. Abrir navegador: `http://localhost:8000/admin/`
2. Fazer login: `admin / admin` (ou seu usuário)
3. Navegar para: `Financeiro → Contas a Pagar`

---

### Passo 3: Encontrar Conta sem Parcelas (30 segundos)

Procurar na lista por uma conta que:
- ✅ Tenha `Número` (ex: "2024-001")
- ✅ Tenha `Fornecedor` 
- ✅ Tenha `Valor Total > 0`
- ✅ **NÃO tenha parcelas ainda** (ou clicar em uma existente e deletar parcelas)

→ Exemplo: Clique em uma conta

---

### Passo 4: Clicar em "Criar Parcelas Automaticamente"

Na página de detalhe da conta, procure pelo botão:
```
🔗 Criar Parcelas Automaticamente
```

**URL esperada:** `http://localhost:8000/financeiro/contas/2/parcelas/criar/`

---

### Passo 5: Testar a Interface (3 minutos)

#### 5.1: Escolher Condição de Pagamento
Marque diferentes opções e observe o **Preview atualizar em tempo real**:

**Teste 1 - À Vista:**
- ✅ Marque: "À Vista"
- ✅ Observe: 1 parcela, hoje, valor total
- ✅ Esperado: Parc. 1 | 03/03/2026 | R$ [valor]

**Teste 2 - 30 Dias:**
- ✅ Marque: "30 Dias"
- ✅ Observe: 1 parcela, +30 dias
- ✅ Esperado: Parc. 1 | 02/04/2026 | R$ [valor]

**Teste 3 - 30/60 Dias (2 parcelas):**
- ✅ Marque: "30/60 Dias"
- ✅ Observe: 2 parcelas, valores divididos
- ✅ Esperado: 
  ```
  Parc. 1 | 02/04/2026 | R$ [valor/2]
  Parc. 2 | 02/05/2026 | R$ [valor/2]
  TOTAL: R$ [valor original]
  ```

**Teste 4 - Customizado:**
- ✅ Marque: "Customizado"
- ✅ Aparecer campo: "Dias de Vencimento"
- ✅ Digite: `15, 30, 45`
- ✅ Observe: 3 parcelas com dias 15, 30, 45
- ✅ Esperado:
  ```
  Parc. 1 | 18/03/2026 | R$ [valor/3]
  Parc. 2 | 02/04/2026 | R$ [valor/3]
  Parc. 3 | 17/04/2026 | R$ [valor/3]
  ```

#### 5.2: Selecionar Forma de Pagamento
- ✅ Dropdown: Observar 7 opções disponíveis
- ✅ Selecione: "PIX"
- ✅ Observe: Todas as parcelas mostram "PIX"
- ✅ Selecione: "Boleto"
- ✅ Observe: Todas mostram "Boleto (1.5% taxa)"

#### 5.3: Verificar Preview
O preview deve conter:
- ✅ Número de parcelas correto
- ✅ Valores somando corretamente
- ✅ Datas espaçadas com dias corretos
- ✅ Forma de pagamento selecionada

---

### Passo 6: Criar as Parcelas (1 minuto)

1. **Confirme as informações:**
   - Condição de pagamento: 30 Dias ✅
   - Forma de pagamento: PIX ✅
   - Preview mostra valores corretos ✅

2. **Clique em:** "✅ Criar Parcelas"

3. **Esperado:** 
   - Página redireciona para detalhe da conta ✅
   - Mensagem verde: "✅ 1 parcelas criadas com sucesso" ✅
   - Seção de "Parcelas" agora mostra a parcela criada ✅

---

### Passo 7: Verificar Parcelas Criadas (1 minuto)

Na página de detalhe da conta:

```
PARCELAS
┌──────────────────────────────────────────┐
│ Nº    Vencimento   Valor      Status     │
│ 1     02/04/2026   R$ 3.000   Aberta     │
└──────────────────────────────────────────┘
```

Validações:
- ✅ `numero_parcela = 1` (ou correspondente)
- ✅ `data_vencimento = data_pedido + dias` 
- ✅ `valor_parcela = valor_total / num_parcelas` (ou ajuste centavos)
- ✅ `status = ABERTA`
- ✅ `forma_pagamento = PIX` (se selecionada)

---

## 📋 Checklist de Testes

### Testes Funcionais
- [ ] Página carrega sem erros
- [ ] Preview atualiza em tempo real ao mudar condição
- [ ] À Vista cria 1 parcela com data de hoje
- [ ] 30 Dias cria 1 parcela com +30 dias
- [ ] 30/60 cria 2 parcelas com +30 e +60 dias
- [ ] Customizado funciona com dias definidos
- [ ] Forma de pagamento é aplicada

### Testes de Dados
- [ ] Valores estão corretos no preview
- [ ] Total do preview = Valor total da conta
- [ ] Datas estão corretas (data_emissao + dias)
- [ ] Centavos ajustados na última parcela
- [ ] Soma das parcelas = Valor total

### Testes de Banco de Dados
- [ ] Parcelas aparecem em `ParcelaContaPagar`
- [ ] Campo `numero_parcela` preenchido
- [ ] Campo `valor_parcela` preenchido
- [ ] Campo `data_vencimento` preenchido
- [ ] Campo `forma_pagamento` preenchido (se selecionado)
- [ ] Campo `status` = "ABERTA"

### Testes de Segurança
- [ ] Acesso requer login
- [ ] Usuário só pode criar parcelas de suas contas
- [ ] CSRF token validado
- [ ] Escrita no banco no contexto de transação

---

## 🐛 Troubleshooting

### ❌ "Erro 404 - Página não encontrada"
**Solução:** Verificar se URL está correta
- Correto: `/financeiro/contas/2/parcelas/criar/`
- Verificar se conta ID existe e você tem permissão

### ❌ "Página redireciona mas não cria parcelas"
**Solução:** Verificar console do navegador (F12)
- Possivelmente erro de JavaScript
- Tentar em navegador diferente

### ❌ "Valores estão errados na preview"
**Solução:** Verificar
- Se `conta.valor_total` está preenchido corretamente
- Se JavaScript está carregando (verificar aba "Console" no F12)

### ❌ "Forma de pagamento não aparece"
**Solução:**
- Verificar em `Administração → Formas de Pagamento`
- Conferir se está marcado como "Ativo"
- Refresh da página (F5)

---

## 📊 Resultado Esperado Final

Depois de criar as parcelas você vê:

### Na Página de Detalhe da Conta:
```
CONTA A PAGAR #2
Fornecedor: Empresa X
Valor Total: R$ 3.000,00
Data Emissão: 03/03/2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PARCELAS
┌─────────────────────────────────────────────────────┐
│ Parc. │ Vencimento │ Valor        │ Forma    │ Status  │
├─────────────────────────────────────────────────────┤
│   1   │ 02/04/2026 │ R$ 3.000,00  │ PIX      │ Aberta  │
└─────────────────────────────────────────────────────┘

RESUMO
Total em Parcelas: R$ 3.000,00 ✅
Pago: R$ 0,00
Faltando: R$ 3.000,00
```

### No Banco de Dados:
```sql
ParcelaContaPagar:
  ID: 15
  conta_pagar_id: 2
  numero_parcela: 1
  valor_parcela: 3000.00
  data_vencimento: 2026-04-02
  forma_pagamento_id: 1 (PIX)
  status: ABERTA
  data_criacao: 2026-03-03 16:45:00
```

---

## ✅ Sucesso!

Se você conseguiu passar por todos os testes, o sistema está **funcionando perfeitamente!**

**Próximas ações sugeridas:**
1. ✅ Testar com diferentes fornecedores
2. ✅ Testar com valores em diferentes faixas
3. ✅ Testar pagamento das parcelas (registrar_pagamento)
4. ✅ Testar relatório de parcelas
5. ✅ Treinar usuários na interface

---

## 🎓 Instruções para Usuários Finais

Forneça este texto resumido para seus usuários:

> **Como Criar Parcelas Automaticamente:**
> 
> 1. Abra a Conta a Pagar
> 2. Clique em "Criar Parcelas Automaticamente"
> 3. Escolha a **Condição de Pagamento** (À Vista, 30 dias, etc.)
> 4. Escolha a **Forma de Pagamento** (PIX, Boleto, etc.)
> 5. Veja a **Preview das Parcelas** (sistema calcula automaticamente)
> 6. Clique em "Criar Parcelas"
> 7. Pronto! As parcelas foram criadas!
>
> **Dica:** O sistema divide o valor automaticamente e define as datas. Não é necessário calcular nada!

---

**Data de Teste Recomendada:** 03/03/2026
**Versão do Sistema:** Django 5.2.7
**Status:** ✅ PRONTO PARA PRODUÇÃO
