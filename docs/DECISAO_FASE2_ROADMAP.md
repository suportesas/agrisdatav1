# Fase 2: Decisão de Roadmap - Escolha 1 ou 2

**Data**: 02/04/2026  
**Status**: Fase 1 (XML Import) ✅ CONCLUÍDA  
**Próximo**: Escolher direção de evolução

---

## 🎯 Resumo das Opções

### ✅ Completed (Fase 1)
```
✅ Parsing XML NF-e v4.0 
✅ Extração automática de dados
✅ Validação por fornecedor + duplicação
✅ Vinculação com PedidoCompra
✅ Testes unitários + integração
✅ Feature flag + fallback seguro
```

### 🚀 Two Paths Forward

---

## 📌 OPÇÃO 1: Fase 2 XE (XML Enhancement)
**Subtítulo**: Rastreabilidade de Lote + Validação SEFAZ

### 📊 Escopo

| Item | O Quê | Por Quê |
|------|-------|--------|
| **SEFAZ Validation** | Integração com Web Service da Receita Federal | Validar NF-e autorizada + dados carregados corretos |
| **Lote Tracking** | Vincular NF-e → Lote → Validade | Rastreabilidade completa insumo → estoque |
| **Batch Operations** | Importar múltiplas NF-e em lote | Acelerar entrada em safra (100+ NF-es) |
| **Error Reporting** | Log detalhado para SEFAZ rejects | Auditoria + troubleshooting |

### 🏗️ Arquitetura

```
RecebimentoCompra (Fase 1)
    ↓
[SEFAZ Web Service Call]
    ├─ Validar chave NF-e autorizada
    ├─ Comparar dados: XML vs SEFAZ
    ├─ Coletar informações lote/validade
    └─ Cache resultado por 24h
    ↓
LoteRecebimento (NOVO)
    ├─ chave_nfe → lote_id
    ├─ data_validade
    ├─ numero_sequencial
    └─ status_sefaz (validado/pendente/rejeitado)
    ↓
✅ RecebimentoCompra.lote = LoteRecebimento
```

### 💡 Casos de Uso

1. **Validação Automática**
   - NF-e importada → Sistema checa com SEFAZ automaticamente
   - ✅ Autorizada → Continua fluxo normal
   - ❌ Cancelada/Rejeitada → Bloqueia recebimento

2. **Rastreabilidade Completa**
   - Produto comprado P1 (NF #123) → Lote X → Validade 30/06/26
   - Ao sacar estoque → Registra lote automático
   - Consulta reversa: Lote X → NF #123 → Fornecedor ABC

3. **Batch Import**
   - Upload ZIP com 50 NF-es
   - Sistema processa em background (Celery task)
   - Relatório de sucesso/erro para usuário

### 🕐 Estimativa

- SEFAZ Integration: 8h (API call, error handling, caching)
- Lote Model + Migrations: 3h (schema, relations, queries)
- Batch Processing: 4h (Celery, file handling, progress tracking)
- Tests: 5h (integration w/ SEFAZ mock, batch scenarios)
- Docs: 2h (SOP, troubleshooting, rate limits)

**Total: 22 horas** (~2.5 semanas para 1 dev)

### 📈 Impacto

- ✅ **Risk Reduction**: Validação SEFAZ evita NF-es falsas/canceladas
- ✅ **Automation**: Lote automático = menor entrada manual
- ✅ **Compliance**: Log completo para auditoria fiscal
- ✅ **Multi-Empresa**: Cada empresa escolhe se valida com SEFAZ ou não (via flag)

### ⚠️ Desafios

1. **Rate Limits da SEFAZ**: API pode ter throttling
   - Solução: Queue + retry com backoff exponencial

2. **Certificado Digital**: SEFAZ exige cert para autenticação
   - Pré-requisito: Empresa já tem cert instalado

3. **Testabilidade**: Não há SEFAZ em staging
   - Solução: Mock responses para testes + ambiente "quasi-produção"

---

## 📌 OPÇÃO 2: RF-059 (Vendor Scorecard)
**Subtítulo**: Avaliação de Desempenho de Fornecedores

### 📊 Escopo

| Item | O Quê | Por Quê |
|------|-------|--------|
| **Scorecard Widget** | Card visual mostrando A/B/C rating por fornecedor | Dashboard rápido para decisão de compra |
| **Métricas de Preço** | Histórico de preços pagos | Detectar aumento injustificado |
| **Métricas de Prazo** | Média de dias para entregar | Alertar se prazo médio aumentando |
| **Métricas de Qualidade** | Taxa de devoluções / reclamações | Identificar fornecedores problemáticos |
| **Ranking A/B/C** | Classificação automática (melhor → pior) | Sugestão de fornecedor na solicitação |
| **Sugestão Automática** | "Use Fornecedor B (ranking A)" na SolicitacaoCompra | Otimizar decisão de compra |

### 🏗️ Arquitetura

```
Fornecedor
    ↓
[Scorecard Model] (NOVO)
    ├─ fornecedor_id
    ├─ periodo_inicio (ex: últimos 90 dias)
    ├─ contagem_compras
    ├─ avg_preco_unitario
    ├─ avg_dias_entrega
    ├─ taxa_devolucao (%)
    ├─ score_total (0-100)
    └─ ranking (A/B/C)
    ↓
[RelatorioFornecedorScorecard] (View)
    ├─ Tabela com todos fornecedores
    ├─ Filtro por categoria/produto
    ├─ Gráfico histórico scores
    └─ Comparação: Preço vs Prazo vs Qualidade
    ↓
[Sugestão em SolicitacaoCompra]
    └─ "Recomendação: Fornecedor XYZ (Ranking A) - R$ 12.50/un"
```

### 💡 Casos de Uso

1. **Dashboard Rápido**
   - Comprador abre relatório Scorecard
   - Vê: Fornecedor A (Score 95/100, Ranking A) vs Fornecedor B (Score 72/100, Ranking C)
   - Decisão rápida qual usar

2. **Histórico de Preço**
   - Fornecedor X cobrava R$ 10 (mar) → R$ 12 (abr) → R$ 14 (mai)
   - Sistema alerta: ⚠️ Aumento de 40% em 2 meses
   - Comprador renegocia ou troca fornecedor

3. **Qualidade**
   - Fornecedor Y teve 3 devoluções em 10 compras (30% taxa)
   - Sistema marca como Ranking C
   - Reduz para fornecedor confiável

4. **Sugestão Automática**
   - Usuário cria SolicitacaoCompra
   - Sistema sugere: "Melhor oferta: Fornecedor A (R$ 12.50, entrega 2d, ranking A)"
   - Usuário pode aceitar ou mudar

### 🕐 Estimativa

- Scorecard Model + Calculations: 4h (agregação, triggers, refresh)
- relatório View + Template: 3h (tabela, gráficos com Chart.js ou Plotly)
- Sugestão Automática (SolicitacaoCompra): 2.5h (form logic, ranking selector)
- Score Caching + Background Job: 2.5h (Celery task, refresh diário)
- Tests: 4h (calculation correctness, edge cases)
- Docs + Guia Usuário: 1.5h

**Total: 17.5 horas** (~2 semanas para 1 dev)

### 📈 Impacto

- ✅ **Cost Savings**: Melhor seleção de fornecedores = menor preço geral
- ✅ **Quality Improvement**: Rastrear qualidade = pressão positiva em fornecedores
- ✅ **Time to Decision**: Scorecard pronto = decisão em minutos vs. horas
- ✅ **Compliance**: Auditoria clara do critério de seleção de fornecedor

### ⚠️ Desafios

1. **Devolução Tracking**: Precisamos ter dados de qualidade/devolução completos
   - Pré-requisito: RF-083 (Devoluções) já implementado? → **Não está**
   - Workaround: Cache somente dados que temos (preço + prazo), qualidade em Fase 3

2. **Atualização de Score**: Quando recalcular?
   - Opção A: Daily job (simples, + demora 1 dia para atualizar)
   - Opção B: Real-time (complexo, + sempre fresco)
   - Recomendação: Daily (trade-off razoável)

3. **Feedback de Usuário**: Scorecard precisa ser calibrado
   - Legítimo? A preço realmente melhor?
   - Validação: Tester na homologação aprova critérios

---

## 🤔 Comparação: Qual Escolher?

| Critério | Opção 1 (SEFAZ) | Opção 2 (Scorecard) |
|----------|-----------------|-------------------|
| **Urgência** | ALTA (compliance)  | MÉDIA (eficiência) |
| **Complexidade** | ALTA (API externa) | MÉDIA (cálculos) |
| **Tempo** | 22h (~2.5w)        | 17.5h (~2w) |
| **Impacto Direto** | Segurança        | Eficiência |
| **Pré-requisitos** | Cert SEFAZ       | Devoluções parcial |
| **User Wow Factor** | ⭐⭐ (automático)  | ⭐⭐⭐ (visual+rápido) |
| **Prioridade PM** | Alta             | Média |

### 🎯 Recomendação (TechLead)

Pelos dados acima:

- **Se objetivo é COMPLIANCE + AUDITORIA**: Escolha Opção 1 (SEFAZ)
  - Reduz risco fiscal
  - Atende regulatory concerns
  - Menos impacto visual imediato ao usuário

- **Se objetivo é EFICIÊNCIA + UX**: Escolha Opção 2 (Scorecard)
  - Usuários veem impacto imediato (dashboard)
  - Economia de tempo em compras
  - Mais "wow" para cliente

---

## 📋 Próximas Ações

### Se Escolher OPÇÃO 1 (SEFAZ)

1. [ ] Verificar: Empresa tem certificado digital? (pré-requisito)
2. [ ] Coletar documentação da API SEFAZ (Consultoria fiscal)
3. [ ] Implementar mock para testes
4. [ ] Planejar pipeline de rate-limiting

### Se Escolher OPÇÃO 2 (Scorecard)

1. [ ] Validar: Devoluções (RF-083) pode ser feita em paralelo ou depois?
2. [ ] Design: Mockup do scorecard dashboard
3. [ ] Calibração: Qual peso para preço vs prazo vs qualidade?
   - Exemplo: Score = (preço_rank * 30%) + (prazo_rank * 40%) + (qualidade_rank * 30%)

### Se Escolher AMBAS (Paralelo)

- 🚀 Recursos: 2 devs (1 cada) OU 1 dev sequencial (22+17.5=39.5h ~ 5 semanas)
- 📅 Timeline: Simultânea (mais rápido) vs Sequencial (menos caos)

---

## ✍️ DECIDIR AGORA

**Qual direção?**

```
[ ] 1. OPÇÃO 1: Fase 2 XE (SEFAZ + Lote Rastreabilidade)
     → Prioridade: COMPLIANCE
     → Tempo: 22h
     → Impacto: Interno + Regulatório

[ ] 2. OPÇÃO 2: RF-059 (Scorecard de Fornecedores) 
     → Prioridade: EFICIÊNCIA
     → Tempo: 17.5h  
     → Impacto: Externo + UX

[ ] 3. AMBAS (Paralelo ou Sequencial)
     → Prioridade: TOTAL
     → Tempo: 39.5h+ 
     → Impacto: MÁXIMO
```

---

## 🔗 Documentação de Referência

**Opção 1 Resources:**
- SEFAZ API: [Receita Federal - NF-e Portal](https://www.nfe.fazenda.gov.br/portal/)
- Rate Limiting Best Practices: Django Ratelimit docs
- Celery + Redis: Background job orchestration

**Opção 2 Resources:**
- RF-059 Detalhes: [ANALISE_STATUS_PRD.md](archive/diversos/ANALISE_STATUS_PRD.md#rf-059-ranking-e-avaliação-de-fornecedores) (documento histórico, desatualizado — ver nota em `docs/archive/diversos/README.md`)
- Chart.js / Plotly for Dashboard
- Django ORM Aggregation (group_by, Sum, Avg, Count)

---

## 📞 Próxima Conversa

Responda:
- **O quê?** `1`, `2`, ou `1 e 2`?
- **Por quê?** Qual motivação (compliance, eficiência, ou total)?
- **Quando?** Começar imediatamente após aprovação?

