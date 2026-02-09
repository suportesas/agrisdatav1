# 🏗️ RF-055: Arquitetura do Sistema de Alertas

## 📊 Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│                      USUÁRIO ACESSA PÁGINA                      │
│                  /estoque/estoque-produtos/                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               1. VIEW: estoque_produtos_list()                   │
│                   (estoque/views.py:550)                         │
│                                                                  │
│  for produto in produtos:                                       │
│    └─ Calcula saldo = Lotes + (Entradas - Saídas)              │
│    └─ Define alerta_tipo:                                       │
│       ├─ 'critico' se saldo ≤ 0                                 │
│       ├─ 'baixo' se saldo < estoque_minimo                      │
│       ├─ 'excesso' se saldo > estoque_maximo                    │
│       └─ None se normal                                         │
│    └─ Incrementa contador (alertas_criticos/baixos/excesso)    │
│                                                                  │
│  context = {                                                     │
│    'produtos': produtos,                 ◀─ Com alerta_tipo     │
│    'alertas_criticos': N,                                       │
│    'alertas_baixos': N,                                         │
│    'alertas_excesso': N,                                        │
│    'total_alertas': N,                                          │
│  }                                                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴───────────┐
                │                        │
                ▼                        ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │  TEMPLATE RENDERIZA  │    │  CONTEXT PROCESSOR   │
    │                      │    │  alertas_estoque()   │
    │ estoque_produtos_    │    │  (core/context_     │
    │ list.html            │    │   processors.py)     │
    │                      │    │                      │
    │ - Badges no topo     │    │ ✓ Calcula alertas    │
    │ - Cores nas linhas   │    │ ✓ Filtra por empresa │
    │ - Coluna Situação    │    │ ✓ Trata erros        │
    │ - Mín/Máx visíveis   │    │ ✓ Retorna dict       │
    └──────────────────────┘    └──────────────────────┘
                │                        │
                │    ┌──────────────────┘
                │    │
                ▼    ▼
    ┌──────────────────────────────────────┐
    │      SIDEBAR.HTML (Template)         │
    │                                      │
    │  📦 Estoque 🔴 {{ total_alertas }}   │
    │  └─ Estoque de Produtos 🔴 {{ ... }} │
    │  └─ Armazéns                         │
    │  └─ ...                              │
    └──────────────────────────────────────┘
                │
                ▼
    ┌──────────────────────────────────────┐
    │      HTML RENDERIZADO (Navegador)    │
    │                                      │
    │  Página com:                         │
    │  ✓ Cores                             │
    │  ✓ Badges                            │
    │  ✓ Ícones                            │
    │  ✓ Menu com contador                 │
    │                                      │
    │  👥 Usuário Vê Alertas! 🎉          │
    └──────────────────────────────────────┘
```

---

## 🔄 Ciclo de Vida de um Alerta

```
PRODUTO CRIADO
│
├─ estoque_minimo = 100
├─ estoque_maximo = 500
├─ estoque_atual = 0
│
▼
ENTRADA/SAÍDA REALIZADA
│
▼
VIEW CALCULA SALDO
│
├─ Lotes: 50
├─ Entradas: 30
├─ Saídas: 20
├─ Saldo: 60
│
▼
VERIFICA TIPO DE ALERTA
│
├─ É 60 ≤ 0? NÃO
├─ É 60 < 100? SIM → 'baixo'
├─ É 60 > 500? NÃO
│
▼
TEMPLATE RENDERIZA
│
├─ Linha com cor: table-warning
├─ Badge: 🟠 Baixo
├─ Mensagem: "Abaixo do mínimo"
│
▼
CONTEXT PROCESSOR ATUALIZA
│
├─ alertas_baixos += 1
├─ total_alertas = X
│
▼
MENU MOSTRA BADGE
│
├─ 📦 Estoque 🔴 X
│
▼
USUÁRIO VÊ ALERTA ✅
```

---

## 🏢 Arquitetura Multi-Tenant

```
┌──────────────────────────────────────────────────────────────┐
│                    SISTEMA MULTI-EMPRESA                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ USUÁRIO 1 - Empresa A                                │   │
│  │ └─ Context Processor                                 │   │
│  │    └─ Filtra: categoria__empresa=Empresa_A           │   │
│  │       ├─ Vê alertas da Empresa A                      │   │
│  │       ├─ Estoque de Produtos: 5 alertas              │   │
│  │       └─ Total: 5                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ USUÁRIO 2 - Empresa B                                │   │
│  │ └─ Context Processor                                 │   │
│  │    └─ Filtra: categoria__empresa=Empresa_B           │   │
│  │       ├─ Vê alertas da Empresa B                      │   │
│  │       ├─ Estoque de Produtos: 3 alertas              │   │
│  │       └─ Total: 3                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ ADMIN SUPERUSER - Todas as Empresas                 │   │
│  │ └─ Context Processor (sem filtro empresa)            │   │
│  │    ├─ Vê alertas de TODAS as empresas                │   │
│  │    ├─ Total: 8 alertas                               │   │
│  │    └─ Precisa de cuidado extra!                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 📱 Interface Responsiva

```
DESKTOP (1920x1080)
┌──────────────────────────────────────────────┐
│  ◄ 📦 SIDEBAR │ 📦 Estoque de Produtos    │
│    Estoque🔴8 │ 🔴 Críticos: 2            │
│    └─ Produtos🔴8  🟠 Baixos: 3  🔵 Excesso: 1
│    ├─ Armazéns│                          │
│    ├─ Locais  │ ┌───┬──────┬──────┬──────┐
│    ├─ Lotes   │ │Cod│Prod  │Atual │Mín   │
│    └─ ...     │ ├───┼──────┼──────┼──────┤
└──────────────────┤P01│Adubo │0     │100   │
                   └───┴──────┴──────┴──────┘

TABLET (768x1024)
┌──────────────────────────────────────────────┐
│ ☰  📦 MENU   │ 📦 Estoque de Produtos      │
│              │ 🔴 Críticos: 2              │
│              │ 🟠 Baixos: 3                │
│              │                            │
│              │ ┌────────┬──────┬──────┐    │
│              │ │Cod │Prod│Atual│Mín   │    │
│              │ ├────┼───┼──────┤       │    │
│              │ │P01 │Adu│0 │100│       │    │
│              │ └────┴───┴──────┴───────┘    │
└──────────────────────────────────────────────┘

MOBILE (375x667)
┌──────────────────┐
│ ☰                │
│ 📦 Estoque 🔴 2  │
│                  │
│ Críticos: 2      │
│ Baixos: 3        │
│                  │
│ Adubo      🔴   │
│ 0 < 100          │
│                  │
│ Sementes   🟠   │
│ 50 < 100         │
│                  │
│ [Ver Mais]       │
└──────────────────┘
```

---

## 🔗 Relacionamentos de Modelos

```
┌──────────────┐
│   Produto    │
├──────────────┤
│ id           │
│ nome         │
│ estoque_atual│ ◀─ Atualizado por view
│ estoque_min  │ ◀─ Define limite baixo
│ estoque_max  │ ◀─ Define limite alto
│ categoria    │──┐
│ ...          │  │
└──────────────┘  │
                  │
                  │ belongs_to
                  │
                  ▼
          ┌──────────────┐
          │  Categoria   │
          ├──────────────┤
          │ id           │
          │ nome         │
          │ empresa      │──┐
          └──────────────┘  │
                            │ belongs_to
                            │
         ┌──────────────────┘
         │
         ▼
    ┌──────────────┐
    │  Empresa     │
    ├──────────────┤
    │ id           │
    │ nome         │
    │ bloqueada    │
    └──────────────┘

┌──────────────┐      ┌──────────────┐
│    Lote      │      │MovimentacaoE │
├──────────────┤      │   stoque     │
│ id           │      ├──────────────┤
│ produto      │──┐   │ id           │
│ quantidade   │  └──►│ produto      │
│ status       │      │ tipo (E/S)   │
│ ...          │      │ quantidade   │
└──────────────┘      │ status       │
                      │ ...          │
                      └──────────────┘
        ▲
        │
        └─ Calcula saldo: Lotes + (Entradas - Saídas)
```

---

## ⚙️ Configuração do Django

```
settings.py
├─ INSTALLED_APPS
│  └─ 'estoque',    ✓
├─ MIDDLEWARE
│  └─ (nenhuma nova)
└─ TEMPLATES
   └─ OPTIONS
      └─ context_processors
         ├─ django.contrib.auth.context_processors.auth
         ├─ django.contrib.messages.context_processors.messages
         └─ 'core.context_processors.alertas_estoque'  ◀─ NOVO!
```

---

## 🔍 Fluxo de Cache (Futuro)

```
REQUISIÇÃO 1
│
├─ View calcula alertas (200ms)
├─ Salva em cache (key: 'alertas:empresa:1')
├─ TTL = 5 minutos
│
▼
REQUISIÇÃO 2 (1 minuto depois)
│
├─ Busca em cache ✓ (10ms)
├─ Retorna dados em cache
│
▼
REQUISIÇÃO 3 (10 minutos depois)
│
├─ Cache expirou
├─ Recalcula (200ms)
└─ Salva novamente em cache
```

---

## 🚨 Tratamento de Erros

```
Context Processor alertas_estoque()
│
├─ Usuario autenticado?
│  └─ NÃO → return {'alertas_estoque': zeros}
│
├─ Usuario tem empresa?
│  └─ NÃO → return {'alertas_estoque': zeros}
│
├─ Try:
│  ├─ Busca produtos
│  ├─ Calcula saldo
│  └─ Categoriza alertas
│
└─ Except:
   └─ Log erro + return {'alertas_estoque': zeros}

Resultado: NUNCA quebra a página!
```

---

## 📊 Tipos de Alerta vs Ação

```
Tipo: CRÍTICO (saldo ≤ 0)
├─ Cor: Vermelho (danger)
├─ Ícone: ⊘ (exclamation-circle)
├─ Prioridade: 🔴🔴🔴 MÁXIMA
├─ Ação: COMPRAR JÁ
└─ Email: Diário + Urgente

Tipo: BAIXO (saldo < mínimo)
├─ Cor: Laranja (warning)
├─ Ícone: ⚠️ (exclamation-triangle)
├─ Prioridade: 🟠🟠 ALTA
├─ Ação: Comprar em breve
└─ Email: Diário

Tipo: EXCESSO (saldo > máximo)
├─ Cor: Azul (info)
├─ Ícone: ℹ️ (info-circle)
├─ Prioridade: 🔵 MÉDIA
├─ Ação: Reduzir próximas compras
└─ Email: Semanal

Tipo: NORMAL (entre mín e máx)
├─ Cor: Verde (success)
├─ Ícone: ✓ (check-circle)
├─ Prioridade: ✅ NENHUMA
├─ Ação: Monitorar
└─ Email: Nenhum
```

---

## 🎯 Matriz de Decisão

```
        Estoque = 0     Estoque < Min   Estoque > Max
        ┌─────────────┬────────────────┬────────────┐
Alertar │     SIM     │      SIM       │    SIM     │
        ├─────────────┼────────────────┼────────────┤
Tipo    │   CRÍTICO   │     BAIXO      │  EXCESSO   │
        ├─────────────┼────────────────┼────────────┤
Cor     │  Vermelho   │    Laranja     │    Azul    │
        ├─────────────┼────────────────┼────────────┤
Urgência│    🔴🔴🔴  │     🟠🟠      │    🔵     │
        ├─────────────┼────────────────┼────────────┤
Ação    │ COMPRA JÁ   │ Compra breve   │  Reduzir   │
        ├─────────────┼────────────────┼────────────┤
Email   │  Urgente    │    Diário      │  Semanal   │
        └─────────────┴────────────────┴────────────┘

        Estoque Normal
        ┌──────────────┐
Alertar │     NÃO      │
        ├──────────────┤
Tipo    │     NONE     │
        ├──────────────┤
Cor     │     Verde    │
        ├──────────────┤
Urgência│      ✅      │
        ├──────────────┤
Ação    │   Monitorar  │
        ├──────────────┤
Email   │    Nenhum    │
        └──────────────┘
```

---

## 🔐 Segurança Multi-Tenant

```
Usuário A (Empresa 1)
│
└─ estoque_produtos_list()
   └─ Filtra: Produto.objects.filter(
        ativo=True,
        categoria__empresa=request.user.empresa  ◀─ Empresa 1
      )
   └─ Vê apenas produtos da Empresa 1

Usuário B (Empresa 2)
│
└─ estoque_produtos_list()
   └─ Filtra: Produto.objects.filter(
        ativo=True,
        categoria__empresa=request.user.empresa  ◀─ Empresa 2
      )
   └─ Vê apenas produtos da Empresa 2

NUNCA há vazamento de dados entre empresas!
```

---

## 📈 Escalabilidade

```
Estoque com:

100 produtos    = ~200ms
500 produtos    = ~800ms
1000 produtos   = ~2s
5000 produtos   = ~8s (com otimizações)
10000 produtos  = ~15s (precisa cache)

Solução para escalabilidade:
├─ Cache Redis (TTL 5min)
├─ Background task (Celery)
├─ Índices do banco (estoque_minimo, estoque_maximo)
├─ Paginação (50 produtos por página)
└─ Select_related para queries otimizadas
```

---

**Versão**: v1.0  
**Data**: 2025-02-03  
**Arquitetura**: Django + Bootstrap + Context Processors
