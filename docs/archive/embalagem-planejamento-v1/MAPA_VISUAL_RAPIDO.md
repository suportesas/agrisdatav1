# 🗺️ MAPA VISUAL - NAVEGAÇÃO RÁPIDA
## Guia Interativo de Fluxos e Documentação

---

## 📡 FLUXO PRINCIPAL DO SISTEMA

```
[Usuário Acessa]
       ↓
    [Login] ← Leia: 7_FLUXOS_SISTEMA.md (Autenticação)
       ↓     Código: 4_CODIGO_PRONTO.md (CustomLoginView)
       ↓     Setup: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 2)
       ↓
  [Dashboard] ← Leia: 7_FLUXOS_SISTEMA.md (Dashboard + Cache)
       ↓      Código: 4_CODIGO_PRONTO.md (DashboardView)
       ↓      Check: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 4)
       ↓
    [Menu]
       ├─→ [Registrar Produção] ← Fluxo: 7_FLUXOS_SISTEMA.md
       │         ↓
       │     [Auto-calcula Turno] ← 4_CODIGO_PRONTO.md (calcular_turno)
       │         ↓
       │     [Snapshots Config]
       │         ↓
       │     [INSERT BD]
       │         ↓
       │     [Invalida Cache]
       │         ↓
       │     [Dashboard Atualiza]
       │
       ├─→ [Relatórios] ← Fluxo: 7_FLUXOS_SISTEMA.md
       │         ↓
       │     [Query BD]
       │         ↓
       │     [Processa Dados]
       │         ↓
       │     [Renderiza HTML + Gráficos]
       │
       ├─→ [CRUD Culturas] ← Fluxo: 7_FLUXOS_SISTEMA.md
       │         ↓
       │     [Validações]
       │         ↓
       │     [INSERT/UPDATE/DELETE]
       │
       └─→ [Admin]
               ↓
           [Configurações] ← Fluxo: 7_FLUXOS_SISTEMA.md
               ↓
           [Altera Valores]
               ↓
           [Log Auditoria]
               ↓
           [Invalida Cache]
```

---

## 🔍 MATRIZ: FUNCIONALIDADE × FLUXO × CÓDIGO

| Funcionalidade | Fluxo em | Código em | Checklist em | Tempo |
|---|---|---|---|---|
| **Autenticação** | 7 (seção 2) | 4 (LoginForm, View) | 6 (Fase 2) | 2h |
| **Dashboard** | 7 (seção 3) | 4 (DashboardView) | 6 (Fase 4) | 4h |
| **Registrar Produção** | 7 (seção 5) | 4 (ProducaoForm, View) | 6 (Fase 5) | 3h |
| **CRUD Culturas** | 7 (seção 6) | 4 (CulturaForm, CRUD) | 6 (Fase 6) | 2h |
| **CRUD Embaladores** | 7 (seção 7) | 4 (EmbaladorForm, CRUD) | 6 (Fase 7) | 2h |
| **Relatórios** | 7 (seção 8) | 4 (Views relatorio) | 6 (Fase 9) | 3h |
| **Configurações** | 7 (seção 8) | 4 (ConfiguracaoForm) | 6 (Fase 13) | 1h |
| **Exportar Excel** | 7 (seção 9) | 4 (export views) | 6 (Fase 10) | 2h |
| **Cache** | 7 (seção 10) | 4 (signals.py) | 6 (Fase 14) | 1h |

---

## 🎯 COMO USAR ESTE MAPA

### **Cenário 1: "Qual é o fluxo de [FEATURE]?"**

1. Procure a funcionalidade acima
2. Abra o arquivo de **Fluxo** (coluna 2)
3. Veja o diagrama visual e sequência

### **Cenário 2: "Como implemento [FEATURE]?"**

1. Procure a funcionalidade acima
2. Abra **Checklist** (coluna 4) para a fase específica
3. Abra **Código** (coluna 3) para copiar snippets
4. Volte ao **Fluxo** (coluna 2) se tiver dúvida

### **Cenário 3: "Qual é a próxima tarefa?"**

1. Abra `6_CHECKLIST_IMPLEMENTACAO.md`
2. Veja próxima checkbox não marcada
3. Procure funcionalidade nesta matriz
4. Siga as colunas para **Fluxo** → **Código** → **Checklist**

---

## 📚 LIGAÇÃO ENTRE ARQUIVOS

```
Se você está lendo:        Relacionado com:
─────────────────────────────────────────────────────
0_COMECE_AQUI.md      →    README.md, 1_RESUMO_EXECUTIVO.md
1_RESUMO_EXECUTIVO.md →    0_COMECE_AQUI.md, README.md
2_INDICE_MASTER.md    →    0_COMECE_AQUI.md, 7_FLUXOS_SISTEMA.md
3_PROMPT_COMPLETO.md  →    7_FLUXOS_SISTEMA.md, 4_CODIGO_PRONTO.md
4_CODIGO_PRONTO.md    →    3_PROMPT_COMPLETO.md, 5_QUICK_REFERENCE.md
7_FLUXOS_SISTEMA.md   →    3_PROMPT_COMPLETO.md, 4_CODIGO_PRONTO.md
5_QUICK_REFERENCE.md  →    4_CODIGO_PRONTO.md, troubleshooting
6_CHECKLIST_IMPLEMENTACAO  → Todos (tracking diário)
```

---

## 🔐 SEGURANÇA: ONDE ENCONTRAR

| Aspecto | Fluxo | Código | Documentação |
|---|---|---|---|
| **Autenticação** | 7 (seção 2) | 4 (LoginForm) | 3 (RF03) |
| **Authorization** | 7 (fluxo inteiro) | 4 (decorators.py) | 3 (RF04) |
| **Validação** | Cada seção | 4 (forms.py) | 3 (RNF02) |
| **Criptografia** | 7 (seção 2) | 4 (User model) | 3 (RNF05) |
| **Cache Seguro** | 7 (seção 10) | 4 (signals.py) | 3 (RNF07) |
| **SQL Injection** | 7 (inteiro) | 4 (ORM) | 3 (RNF03) |
| **CSRF** | 7 (POST forms) | 4 (templates) | 3 (RNF06) |
| **Auditoria** | 7 (seção 8) | 4 (ConfiguracaoLog) | 3 (RF10) |

👉 **Para detalhes completos:** Ver `DOCUMENTACAO_DJANGO.md` na raiz

---

## 🚀 JORNADA RÁPIDA: PRIMEIRA IMPLEMENTAÇÃO

### **Dia 1-2: Entender**
```
1. Abra 0_COMECE_AQUI.md (10 min)
2. Abra 7_FLUXOS_SISTEMA.md (30 min) ← VEJA OS DIAGRAMAS!
3. Abra 3_PROMPT_COMPLETO.md (40 min)
4. Abra 6_CHECKLIST_IMPLEMENTACAO.md (10 min)
5. Setup ambiente (conforme 3_PROMPT_COMPLETO.md)
```

### **Dia 3: Implementar Fase 1-2**
```
1. Abra 6_CHECKLIST_IMPLEMENTACAO.md → Fase 1
2. Leia 7_FLUXOS_SISTEMA.md (se tiver dúvida)
3. Copie de 4_CODIGO_PRONTO.md (models.py)
4. Teste com manage.py shell
5. Marque checklist como done
```

### **Dia 4: Implementar Fase 3**
```
1. Abra 6_CHECKLIST_IMPLEMENTACAO.md → Fase 3
2. Consulte 7_FLUXOS_SISTEMA.md (Fluxo de Autenticação)
3. Copie de 4_CODIGO_PRONTO.md (LoginForm, View)
4. Teste em browser
5. Se erro → 5_QUICK_REFERENCE.md
```

### **Dias 5+: Pattern**
```
Repetir para cada fase:
├─ 6_CHECKLIST_IMPLEMENTACAO.md (qual fazer)
├─ 7_FLUXOS_SISTEMA.md (entender fluxo)
├─ 4_CODIGO_PRONTO.md (copiar código)
├─ 5_QUICK_REFERENCE.md (se erro)
└─ Marque checklist como done
```

---

## 🎓 MAPA MENTAL: ARQUITETURA

```
┌─ AUTENTICAÇÃO ──────────────────────────────────────┐
│ User (AbstractUser)                                  │
│   ↓                                                  │
│ LoginForm (validação de credencial)                 │
│   ↓                                                  │
│ CustomLoginView (PBKDF2, Session, Redis)            │
│   ↓                                                  │
│ Dashboard (LoginRequiredMixin)                       │
│ Leia: 7_FLUXOS_SISTEMA.md (seção 2)                 │
│ Código: 4_CODIGO_PRONTO.md (LoginForm, View)        │
│ Check: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 2)        │
└──────────────────────────────────────────────────────┘

┌─ DASHBOARD ──────────────────────────────────────────┐
│ GET /dashboard                                       │
│   ↓                                                  │
│ Cache? (Redis, 15 min TTL)                         │
│   ↓ Sim → Retorna                                   │
│   ↓ Não → Calcula KPIs                             │
│   ↓                                                  │
│ SELECT agregações (COUNT, SUM, AVG)                │
│   ↓                                                  │
│ Formata para Chart.js                              │
│   ↓                                                  │
│ Cache + Retorna                                     │
│ Leia: 7_FLUXOS_SISTEMA.md (seção 3)                │
│ Código: 4_CODIGO_PRONTO.md (DashboardView)         │
│ Check: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 4)       │
└──────────────────────────────────────────────────────┘

┌─ REGISTRAR PRODUÇÃO (NÚCLEO DO SISTEMA) ────────────┐
│ Form: código_barra, cultura, quantidade, reemb.    │
│   ↓                                                  │
│ Scan & Carrega Embalador                           │
│   ↓                                                  │
│ Auto-calcula turno (calcular_turno)                │
│   ↓                                                  │
│ Busca Configuracao (singleton)                     │
│   ↓                                                  │
│ Calcula bonificação & penalidade                   │
│   ↓                                                  │
│ Snapshot valores de config                         │
│   ↓                                                  │
│ INSERT Producao                                     │
│   ↓                                                  │
│ Signal: Invalida cache                             │
│   ↓                                                  │
│ Dashboard atualiza automaticamente                  │
│ Leia: 7_FLUXOS_SISTEMA.md (seção 5)                │
│ Código: 4_CODIGO_PRONTO.md (ProducaoForm, View)    │
│ Check: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 5)       │
└──────────────────────────────────────────────────────┘

┌─ CACHE & PERFORMANCE ────────────────────────────────┐
│ Redis Database                                       │
│ ├─ dashboard_data (TTL 15 min)                      │
│ ├─ configuracao (TTL 1 hora)                        │
│ ├─ embalador_stats_<id> (TTL 15 min)               │
│ └─ session_<id> (TTL 7 dias)                        │
│                                                     │
│ Invalidação via Django Signals                      │
│ ├─ post_save Producao → Invalida cache             │
│ └─ post_save Configuracao → Invalida cache         │
│ Leia: 7_FLUXOS_SISTEMA.md (seção 10)               │
│ Código: 4_CODIGO_PRONTO.md (signals.py)            │
│ Check: 6_CHECKLIST_IMPLEMENTACAO.md (Fase 14)      │
└──────────────────────────────────────────────────────┘
```

---

## 🆘 TROUBLESHOOTING RÁPIDO

### **"Preciso entender [FEATURE]"**
→ 7_FLUXOS_SISTEMA.md (seção correspondente)

### **"Como implemento [FEATURE]?"**
→ 4_CODIGO_PRONTO.md (copiar) + 6_CHECKLIST_IMPLEMENTACAO.md (tasks)

### **"Dá erro em [ERRO]"**
→ 5_QUICK_REFERENCE.md (troubleshooting)

### **"Qual é a próxima tarefa?"**
→ 6_CHECKLIST_IMPLEMENTACAO.md (próxima checkbox)

### **"Tenho dúvida sobre cache/segurança/performance"**
→ 3_PROMPT_COMPLETO.md (buscar tópico)

### **"Preciso de ajuda com Django/PostgreSQL/etc"**
→ 5_QUICK_REFERENCE.md (referência rápida)

---

## 📖 LEITURA RECOMENDADA POR TÓPICO

### **Entender o Todo (1 hora)**
1. 0_COMECE_AQUI.md (10 min)
2. 7_FLUXOS_SISTEMA.md (30 min) ← **FLUXOS VISUAIS**
3. 1_RESUMO_EXECUTIVO.md (10 min)
4. 3_PROMPT_COMPLETO.md (10 min primeiros%)

### **Implementar (contínuo)**
1. 6_CHECKLIST_IMPLEMENTACAO.md (qual fazer)
2. 7_FLUXOS_SISTEMA.md (se tiver dúvida do fluxo)
3. 4_CODIGO_PRONTO.md (copiar código)
4. 5_QUICK_REFERENCE.md (se erro)

### **Pesquisa Específica**
1. 2_INDICE_MASTER.md (busque por tópico)
2. Abra arquivo específico

---

## 🎯 CHECKLIST: ANTES DE COMEÇAR

- [ ] Entendi qual é meu papel (dev, manager, tech)
- [ ] Abri 0_COMECE_AQUI.md
- [ ] Abri 7_FLUXOS_SISTEMA.md (visuais!)
- [ ] Entendi fluxo de autenticação
- [ ] Entendi fluxo de produção
- [ ] Entendi como cache funciona
- [ ] Pronto para implementar

**Todos OK?** → Vá para 6_CHECKLIST_IMPLEMENTACAO.md (Fase 1)

---

**Status:** ✅ Mapa Visual Completo  
**Data:** 01/07/2026  
**Próximo:** Abra 7_FLUXOS_SISTEMA.md para ver diagramas! 🔄
