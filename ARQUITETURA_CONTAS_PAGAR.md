# 🏦 Arquitetura - Módulo Contas a Pagar

## 📊 Estrutura de Models

### 1. **ContaPagar** (Principal)
```
ContaPagar
├── recebimento (FK) → RecebimentoCompra (opcional)
├── fornecedor (FK) → Fornecedor
├── empresa (FK) → Empresa
├── numero (unique)
├── data_emissao
├── valor_total
├── valor_ajustado (após divergências)
├── desconto_negociado
├── juros_acumulados
├── multa_acumulada
├── status: ABERTA | APROVADA | PAGA | CANCELADA | RENEGOCIADA
├── requer_aprovacao (boolean, default=False)
├── aprovado_por (FK Usuario, nullable)
├── data_aprovacao
├── observacoes
├── criado_por (FK Usuario)
├── data_criacao
└── data_atualizacao
```

### 2. **ParcelaContaPagar** (Múltiplas parcelas)
```
ParcelaContaPagar
├── conta_pagar (FK)
├── numero_parcela (1, 2, 3...)
├── valor_parcela
├── data_vencimento
├── data_pagamento (nullable)
├── dias_atraso (calculado)
├── juros_parcela (acumulado)
├── multa_parcela (acumulado)
├── valor_total_parcela (valor + juros + multa)
├── status: ABERTA | PAGA | VENCIDA | RENEGOCIADA
└── observacao
```

### 3. **PagamentoContaPagar**
```
PagamentoContaPagar
├── parcela (FK)
├── conta_pagar (FK)
├── valor_pago
├── forma_pagamento: DINHEIRO | BOLETO | TED | CARTAO | CHEQUE | OUTRO
├── numero_documento (cheque, boleto, etc)
├── banco (nullable)
├── data_pagamento
├── data_compensacao (nullable)
├── status: PENDENTE | PROCESSANDO | COMPENSADO | FALHA | CANCELADO
├── comprovante (file, nullable)
├── observacao
├── pago_por (FK Usuario)
└── data_criacao
```

### 4. **AjusteContaPagar** (Divergências/Renegociação)
```
AjusteContaPagar
├── conta_pagar (FK)
├── tipo: DESCONTO_DIVERGENCIA | ACRESCIMO_JUROS | ACRESCIMO_MULTA | RENEGOCIACAO | OUTRO
├── valor_ajuste (positivo=acréscimo, negativo=desconto)
├── motivo
├── divergencia (FK DivergenciaRecebimento, nullable)
├── aprovado (boolean)
├── aprovado_por (FK Usuario, nullable)
├── data_criacao
└── observacao
```

### 5. **ConfiguracaoJurosMulta** (Empresa)
```
ConfiguracaoJurosMulta
├── empresa (OneToOneField)
├── taxa_juros_mensal (%)
├── multa_atraso (%) ou (valor fixo)
├── tipo_multa: PERCENTUAL | FIXO
├── dias_tolerancia (sem juros)
├── ativo (boolean)
└── data_atualizacao
```

---

## 🔄 Fluxos

### Fluxo 1: Criação Automática (Recebimento)
```
RecebimentoCompra FINALIZADO
    ↓
Trigger automático
    ↓
ContaPagar.objects.create(recebimento=...)
    ↓
Gera ParcelaContaPagar (conforme config)
    ↓
Status: ABERTA (ou APROVADA se requer_aprovacao=False)
```

### Fluxo 2: Criação Manual
```
Usuário acessa /financeiro/contas-pagar/nova/
    ↓
Formulário com:
  - Fornecedor
  - Valor
  - Número de parcelas
  - Datas de vencimento
  - Observações
    ↓
Salva como ABERTA
    ↓
Aguarda aprovação (se configurado)
```

### Fluxo 3: Aprovação (Opcional)
```
Status: ABERTA
    ↓
Se requer_aprovacao=True:
  - Aguarda aprovador
  - Clica "Aprovar" ou "Rejeitar"
    ↓
Status: APROVADA
```

### Fluxo 4: Ajuste por Divergência
```
DivergenciaRecebimento criada
    ↓
Gera desconto automático:
  - ContaPagar.valor_ajustado -= divergencia.quantidade * preco_unitario
  - AjusteContaPagar.create(tipo=DESCONTO_DIVERGENCIA)
    ↓
Recalcula parcelas proporcionalmente
```

### Fluxo 5: Cálculo de Juros e Multa
```
ParcelaContaPagar.data_vencimento < today()
    ↓
Cron job (diário) calcula:
  - dias_atraso = today() - data_vencimento
  - juros_parcela = (valor * taxa_mensal / 30) * dias_atraso
  - multa_parcela = (valor * multa_atraso) se dias_atraso > dias_tolerancia
    ↓
Atualiza valor_total_parcela
```

### Fluxo 6: Renegociação
```
Parcela vencida + com atraso
    ↓
Usuário clica "Renegociar"
    ↓
Novo formulário:
  - Novas datas
  - Perdão de juros (sim/não)
  - Perdão de multa (sim/não)
  - Observação
    ↓
Cria nova ContaPagar renegociada
    ↓
Cancela parcela antiga
```

### Fluxo 7: Pagamento
```
ParcelaContaPagar.status = PAGA
    ↓
Clica "Registrar Pagamento"
    ↓
Formulário:
  - Forma de Pagamento
  - Número de documento (cheque/boleto)
  - Data de compensação (se aplicável)
  - **Comprovante (upload obrigatório)** ← Armazenado em PagamentoContaPagar.comprovante (FileField)
    ↓
Cria PagamentoContaPagar com arquivo anexado
    ↓
Status: COMPENSADO (se data_compensacao preenchida)
    ↓
Comprovante acessível em histórico da parcela
```

---

## 🔐 Regras de Negócio

1. ✅ Criar automático ao receber: `recebimento.status = 'FINALIZADO'`
2. ✅ Bloquear pagamento se fornecedor tem nota < 2.0
3. ✅ Calcular juros compostos diariamente
4. ✅ Permissão de renegociação máximo 2x por parcela
5. ✅ Fluxo de aprovação customizável por empresa
6. ✅ Registrar histórico de ajustes
7. ✅ Vincular a divergências do recebimento

---

## 📱 Views Necessárias

### ContaPagar
- `conta_pagar_list` - Listagem com filtros
- `conta_pagar_create` - Criação manual
- `conta_pagar_detail` - Detalhes completos
- `conta_pagar_aprovar` - Aprovação (optional flow)
- `conta_pagar_cancelar` - Cancelamento

### ParcelaContaPagar
- `parcela_detail` - Detalhes da parcela
- `parcela_pagar` - Pagamento
- `parcela_renegociar` - Renegociação
- `parcela_histórico` - Histórico de ajustes

### Relatórios
- `relatorio_contas_vencidas` - Contas já vencidas
- `relatorio_contas_vencer` - **NOVO** Contas próximas de vencer (próximos 30 dias)
- `relatorio_fluxo_caixa` - Projeção de entradas
- `relatorio_fornecedores_pagamentos` - Análise por fornecedor
- `relatorio_juros_multas` - Juros e multas acumulados
- `exportar_contas_pagar` (PDF/Excel) - Exportação completa

---

## 📅 Tasks Agendadas (Celery/APScheduler)

- ⏰ Cálculo diário de juros/multas
- ⏰ Notificação 3 dias antes de vencer
- ⏰ Notificação de vencimento
- ⏰ Relatório semanal de contas

---

## 📦 App Financeiro

**Será criado um app separado: `financeiro`**

```
erp_agricola/
├── financeiro/
│   ├── models.py (ContaPagar, ParcelaContaPagar, PagamentoContaPagar, AjusteContaPagar, ConfiguracaoJurosMulta)
│   ├── views.py (CRUD, Pagamento, Relatórios)
│   ├── urls.py
│   ├── admin.py
│   ├── forms.py
│   ├── templates/
│   │   ├── conta_pagar_list.html
│   │   ├── conta_pagar_detail.html
│   │   ├── parcela_pagar.html
│   │   └── relatorios/
│   │       ├── contas_vencidas.html
│   │       ├── contas_vencer.html ← NOVO
│   │       ├── fluxo_caixa.html
│   │       └── ...
│   └── tasks.py (Celery tasks para juros/multa/notificações)
```

**Estrutura separada permite:**
- ✅ Encapsular toda lógica de financeiro
- ✅ Gestão independente de comprovantes
- ✅ Relatórios especializados
- ✅ Tasks agendadas próprias
- ✅ Permissões de acesso específicas

---

## 🎯 Próximos Passos

1. [ ] Criar app `financeiro`
2. [ ] Criar os 5 models
3. [ ] Criar migrations
4. [ ] Criar admin definições
5. [ ] Criar forms com validação
6. [ ] Criar views CRUD
7. [ ] Criar templates
8. [ ] Implementar upload de comprovantes (FileField)
9. [ ] Criar fluxo de aprovação
10. [ ] Criar cálculo automático de juros
11. [ ] **Criar relatório: Contas a Vencer (próximos 30 dias)** ← NOVO
12. [ ] Criar relatório: Contas Vencidas
13. [ ] Criar relatório: Fluxo de Caixa
14. [ ] Criar relatório: Fornecedores
15. [ ] Integrar com DivergenciaRecebimento
16. [ ] Adicionar notificações
17. [ ] Exportar para PDF/Excel

