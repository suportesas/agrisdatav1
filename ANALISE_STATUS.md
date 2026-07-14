# Análise de Status — Agrisdata Salutaris
**Data:** 2026-04-27

---

## RESUMO EXECUTIVO

O sistema encontra-se na **transição entre Fase 1 e Fase 2** do roadmap do PRD.
A base técnica (multitenancy, usuários, compras, estoque, financeiro básico) está sólida.
Os módulos de **exportação, packing house, produção completa e financeiro avançado** ainda não foram implementados — exatamente o núcleo do negócio para uma exportadora de frutas.

---

## LEGENDA
- ✅ Implementado e funcional
- ⚠️ Parcialmente implementado
- ❌ Não implementado

---

## MÓDULOS DO PRD vs. STATUS ATUAL

### FASE 1 — BASE (Meses 1–3)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.2 | Cadastros Base | ✅ | Fazenda, Área, Talhão, Cultura, Clientes, Fornecedores, Funcionários, Motoristas, Navios, Armadores, Portos |
| 2.3 | Gestão de Usuários e Segurança | ✅ | 2FA, RBAC, anomalias de login, grupos corporativos |
| 2.4 | Suprimentos e Compras | ✅ | Solicitação → Cotação → Pedido → Recebimento |
| 2.5 | Almoxarifado e Armazéns | ⚠️ | Falta: Requisições internas, devoluções, bloqueio de contaminado, logística reversa |
| 2.15 | Financeiro | ⚠️ | Só ContaPagar. **Falta ContaReceber, DRE, fluxo de caixa projetado, conciliação bancária** |
| 2.20 | Fiscal e Faturamento | ⚠️ | NCM, CFOP, tributação de produtos existem. **Falta emissor NF-e/CT-e/MDF-e** |

### FASE 2 — PRODUÇÃO AGRÍCOLA (Meses 4–6)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.6 | Produção Agrícola | ⚠️ | Safra, OS, MonitoramentoMIP existem. Falta: pluviometria, caderno de campo digital, qualidade de campo |
| 2.7 | Estufas e Transplantio | ❌ | **Não implementado** — nenhum modelo ou view |

### FASE 3 — PACKING HOUSE (Meses 7–9)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.9 | Packing House | ❌ | Só existe tipo 'PACKING' no Armazém. Módulo completo não existe |
| 2.10 | Qualidade e Classificação | ❌ | **Não implementado** |
| 2.33 | Balanço de Massas | ❌ | **Não implementado** (obrigatório GLOBALG.A.P.) |

### FASE 4 — LOGÍSTICA + EXPORTAÇÃO (Meses 10–12)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.8 | Frota, Oficina e Manutenção | ⚠️ | Vehicle/Motorista existem. Falta: manutenção, combustível, pedágios, telemetria, margem por viagem |
| 2.11 | Logística e Expedição | ❌ | Transportadora/Viagem básicos existem. Módulo completo não existe |
| 2.12 | Exportação e Documentação | ❌ | **Não implementado** — o módulo mais crítico do negócio |
| 2.13 | Rolagem de Container | ❌ | **Não implementado** |
| 2.21 | CRM e Vendas | ⚠️ | Vendedor/Cliente existem. Falta funil, pipeline, comissões automatizadas |
| 2.29 | Gestão de Riscos e Cut-offs | ❌ | Risco ambiental (RH) existe. Cut-offs de exportação não existem |

### FASE 5 — BI COMPLETO (Meses 13–15)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.1 | Dashboard Principal | ⚠️ | Dashboard e métricas executivas existem. Falta: KPIs configuráveis, indicadores de exportação, indicadores de carbono |
| 2.28 | Business Intelligence | ⚠️ | Dashboards básicos existem. Falta BI por módulo, relatórios customizados |

### FASE 6 — PORTAIS + MOBILE (Meses 16–18)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.25 | Portais Externos | ⚠️ | Portal Produtor e Fornecedor existem. **Falta Portal do Cliente (com Timeline) e Portal do Despachante** |
| 2.32 | Aplicativo Mobile | ❌ | **Não implementado** |

### FASE 7 — AVANÇADOS (Meses 19–24)

| # | Módulo PRD | Status | Observação |
|---|-----------|--------|------------|
| 2.14 | Conta Corrente de Produtores | ⚠️ | EmprestimoProdutor existe. Falta integração Account Sales, simulador de pagamento |
| 2.16 | Adiantamentos Internacionais | ❌ | **Não implementado** |
| 2.17 | Account Sales e Rateio Comercial | ❌ | **Não implementado** |
| 2.18 | Histórico Financeiro por Invoice | ❌ | **Não implementado** |
| 2.19 | Formação de Preço | ❌ | **Não implementado** |
| 2.22 | Certificações e Compliance | ❌ | Certificados de produto existem. Módulo GLOBALG.A.P., ISO, BRC não existe |
| 2.23 | Sustentabilidade e Carbono | ❌ | **Não implementado** |
| 2.24 | Recursos Humanos | ⚠️ | Estrutura básica existe. Falta: ponto eletrônico, folha de pagamento, ASO completo |
| 2.26 | Cooperativas | ❌ | **Não implementado** |
| 2.27 | AgriCommunity | ❌ | **Não implementado** |

---

## ITENS PENDENTES DO PRD — ROADMAP 2026

### Pendências dentro de módulos já criados

#### Almoxarifado (2.5)
- ⏳ RF-082 Requisições internas entre departamentos
- ⏳ RF-083 Devoluções com reintegração ao estoque
- ⏳ RF-084 Inventário geral e parcial
- ⏳ RF-086 Bloqueio de estoque contaminado / quarentena
- ⏳ RF-087 Logística reversa de embalagens
- ⏳ RF-088 Empréstimos a produtores (integrado conta corrente)

#### Compras (2.4)
- ⚠️ RF-054 Parsing XML de NF-e
- ⏳ RF-056 Inventário cíclico (modelo existe mas incompleto)
- ⏳ RF-058 Controle especial de defensivos e fertilizantes
- ⏳ RF-059 Ranking e avaliação de fornecedores

#### Produção Agrícola (2.6)
- ⏳ RF-107 Registro de pluviometria
- ⏳ RF-108 Controle de qualidade de campo
- ⏳ RF-111 Caderno de campo digital (GLOBALG.A.P.)
- ⏳ RF-113 Aplicações de defensivos e fertilizantes detalhadas
- ⏳ RF-117 Fotos geolocalizadas

#### Financeiro (2.15)
- ⏳ RF-400 Contas a receber completo
- ⏳ RF-402 Fluxo de caixa projetado
- ⏳ RF-403 DRE
- ⏳ RF-404 Conciliação bancária (OFX/CNAB)
- ⏳ RF-408 Controle multimoeda
- ⏳ RF-409 Centro de custo por talhão
- ⏳ RF-410 Rentabilidade por cliente/lote/container

### Módulos novos a criar (por prioridade de negócio)

#### PRIORIDADE CRÍTICA
1. **Exportação e Documentação** (2.12) — Booking, container, invoice, packing list, documentos
2. **Packing House** (2.9) — Recepção, classificação, embalagem, etiquetas, câmara fria
3. **Account Sales e Rateio** (2.17) — Demonstrativo de vendas, rateio por produtor
4. **Estufas e Transplantio** (2.7) — Mudas, lotes, transplantio, rastreabilidade semente→talhão

#### PRIORIDADE ALTA
5. **Qualidade e Classificação** (2.10) — Relatório de qualidade por container
6. **Histórico Financeiro por Invoice** (2.18) — Receitas/despesas por invoice/container
7. **Formação de Preço** (2.19) — Custo real x preço negociado
8. **Logística e Expedição** (2.11) — Programação de cargas, romaneios, gate-in/out
9. **Adiantamentos Internacionais** (2.16) — Controle em moeda estrangeira
10. **Portal do Cliente com Timeline** (2.25)

#### PRIORIDADE MÉDIA
11. **Rolagem de Container** (2.13)
12. **Frota Completa** (2.8) — Manutenção, combustível, custos por viagem
13. **Fiscal NF-e Emissor** (2.20)
14. **Balanço de Massas** (2.33)
15. **Certificações e Compliance** (2.22)
16. **Gestão de Riscos e Cut-offs** (2.29)
17. **Portal do Despachante** (2.25)

#### PRIORIDADE BAIXA
18. **Cooperativas** (2.26)
19. **Sustentabilidade e Carbono** (2.23)
20. **AgriCommunity** (2.27)
21. **Mobile** (2.32)

---

## ESTATÍSTICAS

| Categoria | Qtd |
|-----------|-----|
| Módulos totais no PRD | 33 |
| Módulos totalmente implementados | 7 |
| Módulos parcialmente implementados | 12 |
| Módulos não implementados | 14 |
| % de conclusão estimada | ~35% |

---

*Gerado automaticamente em 2026-04-27*
