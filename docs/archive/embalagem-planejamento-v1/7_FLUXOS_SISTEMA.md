# 🔄 FLUXOS DO SISTEMA COMPLETO
## Diagramas e Fluxos de Dados

---

## 📋 CONTEÚDO

1. **Fluxo Principal do Sistema**
2. **Fluxo de Autenticação**
3. **Fluxo de Dashboard**
4. **Fluxo de Registro de Produção**
5. **Fluxo de CRUD de Culturas**
6. **Fluxo de CRUD de Embaladores**
7. **Fluxo de Relatórios**
8. **Fluxo de Configurações**
9. **Fluxo de Exportação Excel**
10. **Fluxo Técnico de Cache**

---

## 🎯 FLUXO PRINCIPAL DO SISTEMA

```mermaid
graph TD
    A[Usuário Acessa Sistema] --> B{Autenticado?}
    B -->|Não| C[Login]
    C --> D{Credenciais OK?}
    D -->|Não| E[Erro]
    E --> C
    D -->|Sim| F[Dashboard]
    B -->|Sim| F
    
    F --> G{Escolha Ação}
    G -->|Registrar Produção| H[Produção]
    G -->|Relatórios| I[Relatórios]
    G -->|CRUD| J[Manutenção]
    G -->|Configurações| K[Admin]
    G -->|Sair| L[Logout]
    
    H --> M[Sistema Processa]
    I --> M
    J --> M
    K --> M
    M --> F
    L --> C
```

---

## 🔐 FLUXO DE AUTENTICAÇÃO

### **Fluxo Visual**

```mermaid
sequenceDiagram
    participant Usuario
    participant Django
    participant DB as PostgreSQL
    participant Cache as Redis
    
    Usuario ->> Django: POST /login
    Note over Django: Validar Email
    Django ->> DB: SELECT User WHERE email=?
    DB -->> Django: User Data
    Note over Django: Comparar Senha (PBKDF2)
    alt Senha Incorreta
        Django -->> Usuario: Erro - Credenciais Inválidas
    else Senha Correta
        Note over Django: Criar Session
        Django ->> Cache: SET session_key
        Django -->> Usuario: Redireciona Dashboard
    end
```

### **Fluxo Textual**

```
1. Usuário Acessa /login
   └─ Recebe formulário HTML

2. Usuário Submete Email + Senha
   └─ POST para /login

3. Django Valida Entrada
   ├─ Email existe?
   └─ Formato correto?

4. Busca Usuário no Banco
   └─ SELECT * FROM core_user WHERE email = ?

5. Compara Senha (PBKDF2)
   ├─ Hash enviado vs. Hash BD
   └─ Match?

6. Se OK:
   ├─ Cria Session (Django)
   ├─ Salva no Redis (cache)
   ├─ Define Cookie Session
   └─ Redireciona /dashboard

7. Se Erro:
   ├─ Incrementa tentativas
   ├─ Exibe mensagem
   └─ Volta para /login

8. Logout:
   ├─ Deleta Session
   ├─ Remove do Redis
   └─ Redireciona /login
```

---

## 📊 FLUXO DE DASHBOARD

### **Fluxo Visual**

```mermaid
graph LR
    A[GET /dashboard] --> B{Cache Exists?}
    B -->|Sim| C[Retorna do Cache]
    B -->|Não| D[Calcula Dados]
    
    D --> E["SELECT COUNT(*)
    FROM producao"]
    E --> F["SELECT SUM(quantidade)
    FROM producao"]
    F --> G["SELECT AVG(percentual)
    FROM embalador"]
    
    G --> H["Calcula KPIs:
    - Total Produção
    - Média Embalador
    - Reembalagem %"]
    
    H --> I["Prepara Dados
    para Chart.js"]
    
    I --> J["Salva no Redis
    (15 min cache)"]
    
    J --> K["Retorna JSON"]
    C --> L["Renderiza HTML
    + Gráficos"]
    K --> L
    
    L --> M[Usuario Vê Dashboard]
```

### **Dados Retornados**

```json
{
  "periodo": "07/2026",
  "kpis": {
    "total_producao": 15420,
    "total_reembalagem": 340,
    "media_por_embalador": 128,
    "percentual_reembalagem": 2.2
  },
  "ranking_embaladores": [
    {"nome": "João Silva", "quantidade": 450, "reembalagem": 5},
    {"nome": "Maria Santos", "quantidade": 380, "reembalagem": 2}
  ],
  "evolucao_diaria": [
    {"data": "2026-07-01", "quantidade": 450},
    {"data": "2026-07-02", "quantidade": 520}
  ],
  "graficos": {
    "evolucao_producao": [...],
    "distribuicao_cultura": [...],
    "ranking": [...]
  }
}
```

---

## ✍️ FLUXO DE REGISTRO DE PRODUÇÃO

### **Fluxo Visual Completo**

```mermaid
sequenceDiagram
    participant Usuario
    participant Frontend
    participant Django
    participant Model
    participant DB as PostgreSQL
    participant Signal as Django Signal
    participant Cache as Redis
    
    Usuario ->> Frontend: Escaneia Código (barcode)
    Frontend ->> Django: Busca Embalador
    Django ->> DB: SELECT Embalador
    DB -->> Django: Dados Embalador
    Django -->> Frontend: Embalador Carregado
    
    Usuario ->> Frontend: Seleciona Cultura
    Frontend ->> Frontend: Carrega Config
    
    Usuario ->> Frontend: Verifica Reembalagem
    Usuario ->> Frontend: Entra Quantidade
    Usuario ->> Frontend: Submete Form
    
    Frontend ->> Django: POST /registrar
    Note over Django: Validar Dados
    Django ->> Model: Criar Producao()
    
    Note over Model: Auto-calcula:
    Note over Model: - turno (calcular_turno)
    Note over Model: - bonificacao
    Note over Model: - penalidade
    
    Model ->> DB: INSERT Producao
    DB -->> Model: Sucesso
    
    Model ->> Signal: post_save Signal
    Signal ->> Cache: Invalida cache
    Signal ->> Cache: DELETE dashboard_data
    Signal ->> Cache: DELETE embalador_stats
    
    Django -->> Frontend: Sucesso + Novo Registro
    Frontend -->> Usuario: Mensagem OK
    Frontend ->> Frontend: Limpa Form
```

### **Fluxo de Cálculo do Turno**

```python
Entrada: hora = 14:30 (14h30)

calcular_turno(hora):
    h = 14
    if 5 <= h < 12:
        return 'Manhã'      # 5h-12h
    elif 12 <= h < 18:
        return 'Tarde'      # 12h-18h (AQUI!)
    else:
        return 'Noite'      # 18h-5h

Resultado: Turno = 'Tarde'
```

### **Fluxo de Cálculo de Bonificação**

```
1. Busca Configuracao do Sistema
   └─ valor_bonificacao = R$ 1.50

2. Calcula Bonificação
   ├─ quantidade = 100 unidades
   ├─ valor_bonificacao = R$ 1.50
   └─ bonificacao_total = 100 × 1.50 = R$ 150.00

3. Verifica Reembalagem
   ├─ reembalagem = True?
   ├─ Se Sim: penalidade = R$ 1.00
   └─ Se Não: penalidade = R$ 0.00

4. Calcula Final Líquido
   └─ final_liquido = 150.00 - 1.00 = R$ 149.00

5. Salva Registro
   └─ INSERT Producao com todos os valores

6. Snapshot de Configuração
   ├─ Salva valor_bonificacao_snapshot
   ├─ Salva valor_penalidade_snapshot
   └─ Auditoria: ConfiguracaoLog registra alteração
```

---

## 🌾 FLUXO DE CRUD - CULTURAS

### **Visualizar Lista**

```mermaid
graph LR
    A[GET /culturas/] --> B{Cache OK?}
    B -->|Sim| C[Retorna Cache]
    B -->|Não| D["SELECT * 
    FROM cultura
    ORDER BY nome"]
    D --> E["Formata 
    em Tabela"]
    E --> F["Cache 
    15 min"]
    C --> G["Renderiza 
    Template"]
    F --> G
```

### **Criar Cultura**

```mermaid
graph TD
    A[GET /culturas/criar/] --> B[Renderiza Form]
    C[Usuario Submete] --> D[POST /culturas/criar/]
    D --> E["Valida 
    nome unique?"]
    E -->|Nome Existe| F["Erro: 
    Cultura Duplicada"]
    F --> B
    E -->|OK| G["INSERT Cultura"]
    G --> H["Log: 
    Criado por User"]
    H --> I["Invalida Cache"]
    I --> J["Redireciona 
    Lista"]
```

### **Editar Cultura**

```
1. GET /culturas/editar/1/
   └─ Carrega Cultura ID 1

2. Renderiza Form com Dados
   ├─ Nome: "Tomate"
   └─ Criado em: 01/07/2026

3. Usuario Altera: "Tomate" → "Tomate Premium"

4. POST /culturas/editar/1/
   ├─ Valida unique (ignora ID 1)
   ├─ UPDATE cultura SET nome = ?
   └─ Log: modificado_por = User

5. Invalida Cache
   └─ DELETE cache_culturas

6. Redireciona Lista com Mensagem OK
```

### **Deletar Cultura**

```
1. GET /culturas/deletar/1/
   └─ Renderiza Confirmação

2. Verifica Integridade
   ├─ Busca Producao com cultura_id = 1
   ├─ Se Existir:
   │  ├─ Bloqueia Delete
   │  └─ Mensagem: "Não pode deletar, tem registros"
   └─ Se Não Existir:
      └─ Permite Delete

3. POST /culturas/deletar/1/
   ├─ DELETE cultura WHERE id = 1
   ├─ Log: deletado_por = User
   └─ Invalida Cache

4. Redireciona Lista
```

---

## 👤 FLUXO DE CRUD - EMBALADORES

Similar a Culturas, mas com validações adicionais:

```mermaid
graph TD
    A["Criar Embalador"] --> B["Valida:
    - Nome (obrigatório)
    - Código Barras (unique, min 3 chars)"]
    
    C["Editar Embalador"] --> D["Mesmas validações
    + ignora ID próprio"]
    
    E["Deletar Embalador"] --> F["Verifica Producao
    com embalador_id"]
    
    B --> G["INSERT Embalador"]
    D --> H["UPDATE Embalador"]
    F -->|Sem Producao| I["DELETE Embalador"]
    F -->|Com Producao| J["Bloqueia Delete"]
    
    G --> K["Invalida Cache"]
    H --> K
    I --> K
    J --> K
```

---

## 📈 FLUXO DE RELATÓRIOS

### **Relatório de Bonificação**

```mermaid
sequenceDiagram
    participant Usuario
    participant Django
    participant DB
    participant Calc as Cálculo
    participant Template
    
    Usuario ->> Django: GET /relatorio/bonificacao?data=2026-07
    Note over Django: Extrai Período
    
    Django ->> DB: SELECT Embalador
    Django ->> DB: SELECT Producao WHERE data IN período
    
    DB -->> Django: Dados Retornados
    
    Note over Calc: Para cada Embalador:
    
    loop Embalador
        Calc ->> DB: SUM(bonificacao) WHERE embalador_id
        Calc ->> DB: SUM(penalidade) WHERE embalador_id
        Calc ->> Calc: final_liquido = bonificacao - penalidade
    end
    
    Calc -->> Django: Relatório Pronto
    
    Django ->> Template: Context com Dados
    Template -->> Usuario: HTML com Tabela + Gráficos
```

### **Estrutura do Relatório**

```
Relatório de Bonificação - Julho 2026

Embalador          | Producao | Bonificação | Penalidade | Final Líquido
João Silva         |   450    | R$ 675.00   | R$ 5.00    | R$ 670.00
Maria Santos       |   380    | R$ 570.00   | R$ 2.00    | R$ 568.00
Pedro Oliveira     |   520    | R$ 780.00   | R$ 8.00    | R$ 772.00
─────────────────────────────────────────────────────────────
TOTAL              | 1.350    | R$ 2.025.00 | R$ 15.00   | R$ 2.010.00

Gráficos:
- Ranking de Bonificação (Bar Chart)
- Evolução Diária (Line Chart)
- Reembalagem por Embalador (Pie Chart)
```

---

## ⚙️ FLUXO DE CONFIGURAÇÕES

### **Visualizar Configuração**

```
1. GET /configuracoes/
   └─ Apenas Admin

2. SELECT * FROM configuracao
   └─ Singleton (sempre ID 1)

3. Renderiza Form com Valores Atuais
   ├─ valor_bonificacao: R$ 1.50
   ├─ valor_penalidade: R$ 1.00
   └─ Última alteração: por User X em 01/07/2026

4. Usuario Vê:
   - Campo para editar bonificação
   - Campo para editar penalidade
   - Histórico de alterações (últimas 10)
```

### **Alterar Configuração**

```mermaid
sequenceDiagram
    participant Admin
    participant Django
    participant Cache as Redis
    participant DB
    participant Log as ConfiguracaoLog
    
    Admin ->> Django: POST /configuracoes/salvar
    Note over Django: Valida Valores > 0
    
    alt Valores Inválidos
        Django -->> Admin: Erro de Validação
    else OK
        Note over Django: Snapshot Valores Atuais
        Django ->> DB: SELECT Configuracao
        DB -->> Django: Valores Antigos
        
        Note over Django: Prepara Log
        Django ->> Log: INSERT ConfiguracaoLog
        Log -->> Django: Log Criado
        
        Django ->> DB: UPDATE Configuracao
        Note over Django: Novos Valores
        
        Note over Django: Invalida Cache
        Django ->> Cache: DELETE cache_configuracao
        Django ->> Cache: DELETE dashboard_data
        
        Django -->> Admin: Sucesso
        Admin ->> Admin: Tabela Atualiza
    end
```

### **Auditoria de Configurações**

```
ConfiguracaoLog:
├─ ID: 1
├─ valor_bonificacao_anterior: R$ 1.00
├─ valor_bonificacao_novo: R$ 1.50
├─ valor_penalidade_anterior: R$ 0.50
├─ valor_penalidade_novo: R$ 1.00
├─ alterado_por: admin_user
├─ data_alteracao: 01/07/2026 14:30:45
└─ motivo: "Ajuste conforme reunião com gerente"
```

---

## 📊 FLUXO DE EXPORTAÇÃO EXCEL

### **Fluxo de Exportação**

```mermaid
graph TD
    A["Usuario Clica
    Exportar Excel"] --> B["GET /exportar?tipo=producao
    &data_inicio=01/07
    &data_fim=31/07"]
    
    B --> C["Valida Período
    - Data início < fim?
    - Período <= 90 dias?"]
    
    C -->|Erro| D["Erro: Período Inválido"]
    
    C -->|OK| E["Query Banco de Dados
    SELECT Producao
    WHERE data BETWEEN"]
    
    E --> F["Busca relacionados
    - Embalador
    - Cultura
    - Usuario"]
    
    F --> G["Cria Workbook
    openpyxl"]
    
    G --> H["Formatação:
    - Headers em Negrito
    - Cores alternadas
    - Totalizadores
    - Gráficos"]
    
    H --> I["Salva em Memory
    (BytesIO)"]
    
    I --> J["Retorna
    Content-Type:
    application/vnd.ms-excel"]
    
    J --> K["Usuario Recebe
    arquivo.xlsx"]
```

### **Estrutura do Excel**

```
SHEET 1: Produção
┌─────────────────────────────────────────────────────────────┐
│ RELATÓRIO DE PRODUÇÃO - Julho 2026                           │
├─────────────────────────────────────────────────────────────┤
│ Data    │ Embalador    │ Cultura  │ Quantidade │ Reembalagem │
│ 01/07   │ João Silva   │ Tomate   │ 450        │ Não         │
│ 02/07   │ Maria Santos │ Cebola   │ 380        │ Sim         │
├─────────────────────────────────────────────────────────────┤
│ TOTAL                                    1.350    │ 15        │
└─────────────────────────────────────────────────────────────┘

SHEET 2: Bonificação
┌─────────────────────────────────────────────────────────────┐
│ Embalador      │ Producao │ Bonificação │ Penalidade │ Total │
│ João Silva     │ 450      │ R$ 675.00   │ R$ 5.00    │ R$... │
├─────────────────────────────────────────────────────────────┤
│ TOTAL          │ 1.350    │ R$ 2.025.00 │ R$ 15.00   │ R$... │
└─────────────────────────────────────────────────────────────┘

SHEET 3: Gráficos
- Gráfico de Evolução (Line)
- Gráfico de Ranking (Bar)
```

---

## 🔄 FLUXO TÉCNICO DE CACHE

### **Estrutura de Cache**

```
Redis Database:
├─ dashboard_data (TTL: 15 min)
│  └─ {kpis, ranking, evolucao}
│
├─ configuracao (TTL: 1 hora)
│  └─ {valor_bonificacao, valor_penalidade}
│
├─ embalador_stats_<id> (TTL: 15 min)
│  └─ {producao_total, reembalagem%, percentual}
│
└─ session_<id> (TTL: 7 dias)
   └─ {user_id, permissions}
```

### **Invalidação de Cache**

```mermaid
graph TD
    A["Evento: 
    Nova Producao"] --> B["post_save Signal"]
    
    B --> C["Delete Cache:
    - dashboard_data
    - embalador_stats
    - configuracao"]
    
    D["Evento:
    Alterar Configuracao"] --> E["post_save Signal"]
    E --> C
    
    F["Evento:
    User Logout"] --> G["Delete Session"]
    
    H["Cache Expira
    Automaticamente"] --> I["TTL Acionado"]
    
    C --> J["Próximo GET
    Recalcula"]
    G --> K["Session Removida"]
    I --> J
```

### **Fluxo de Leitura com Cache**

```python
# Pseudocódigo

def obter_dashboard_data():
    # 1. Tenta Cache
    data = cache.get('dashboard_data')
    if data:
        return data  # HIT!
    
    # 2. Cache Vazio - Calcula
    data = {
        'kpis': calcular_kpis(),
        'ranking': calcular_ranking(),
        'evolucao': calcular_evolucao(),
    }
    
    # 3. Salva no Cache (15 min)
    cache.set('dashboard_data', data, 15*60)
    
    return data
```

---

## 🔀 FLUXO DE INTEGRAÇÕES ENTRE MÓDULOS

```mermaid
graph TB
    A["Login"] --> B["Session Django"]
    B --> C["Cache Redis"]
    
    D["Dashboard"] --> E["Calcula KPIs"]
    E --> F["Cache"]
    
    G["Registrar Producao"] --> H["Auto-calcula Turno"]
    H --> I["Busca Configuracao"]
    I --> J["Calcula Bonif/Penal"]
    J --> K["INSERT BD"]
    K --> L["Invalida Cache"]
    L --> M["Dashboard Atualiza"]
    
    N["CRUD Cultura"] --> O["Valida Integridade"]
    O --> P["INSERT/UPDATE/DELETE"]
    P --> L
    
    Q["Relatório"] --> R["SELECT BD"]
    R --> S["Processa Dados"]
    S --> T["Renderiza HTML"]
    T --> U["Usuario Vê Relatório"]
    
    V["Exportar Excel"] --> W["Busca Dados"]
    W --> X["Formata openpyxl"]
    X --> Y["Download .xlsx"]
    
    Z["Configuração"] --> AA["Atualiza Valores"]
    AA --> AB["Log ConfiguracaoLog"]
    AB --> L
```

---

## 📱 FLUXO DO USUÁRIO - CASO DE USO COMPLETO

### **Dia Normal de Trabalho**

```
08:00 - INÍCIO DO TURNO
├─ Usuario Acessa http://packing.local
├─ Sistema Detecta Não Autenticado
└─ Redireciona para /login

08:05 - LOGIN
├─ Usuario Insere Email + Senha
├─ Sistema Valida no BD
├─ Cria Session + Redis
└─ Redireciona Dashboard

08:10 - DASHBOARD
├─ Sistema Calcula KPIs (ou retorna cache)
├─ Usuario Vê Gráficos de Produção
└─ Usuario Clica "Registrar Produção"

08:15 - REGISTRO DE PRODUÇÃO (x50)
├─ Usuario Escaneia Código Barrera
├─ Sistema Carrega Embalador
├─ Usuario Seleciona Cultura
├─ Usuario Entra Quantidade
├─ Sistema Auto-calcula:
│  ├─ Turno: Manhã (8:15)
│  ├─ Bonificação: 50 × R$ 1.50 = R$ 75.00
│  └─ Penalidade: R$ 0.00 (sem reembalagem)
├─ Sistema Invalida Cache
└─ Repete 50x até 12:00

12:00 - ALMOÇO + VERIFICAÇÃO
├─ Usuario Acessa Dashboard
├─ Sistema Mostra 50 registros do dia
├─ Gráficos Atualizados
└─ Usuario Vê Seu Ranking

14:00 - TARDE
├─ Continua Registrando Produção
├─ Sistema Muda Turno para "Tarde" (14:00)
└─ Registra com Bonificação Tarde

17:30 - FINAL DO TURNO
├─ Usuario Clica "Meus Relatórios"
├─ Sistema Mostra Bonificação do Dia
├─ Total: R$ 112.50 (75 registros)
└─ Usuario Clica Logout

17:35 - ADMIN VERIFICA
├─ Admin Acessa Dashboard
├─ Admin Clica "Exportar Excel"
├─ Sistema Gera arquivo.xlsx
├─ Admin Faz Download
└─ Admin Abre em Excel (com gráficos)

17:45 - ADMIN ALTERA CONFIG
├─ Admin Clica "Configurações"
├─ Altera valor_bonificacao: 1.50 → 1.75
├─ Sistema Valida
├─ Sistema Registra Log
├─ Cache Invalidado
└─ Mensagem: "Configuração Alterada com Sucesso"

PRÓXIMO DIA - NOVOS VALORES
├─ Sistema Usa novo valor_bonificacao: 1.75
└─ Cálculos com novo valor automaticamente
```

---

## 🎯 RESUMO DOS FLUXOS

| Fluxo | Início | Fim | Cache | BD Ops |
|-------|--------|-----|-------|--------|
| Login | GET /login | Session | Redis | 1 SELECT |
| Dashboard | GET / | HTML | Redis 15min | 3 SELECT |
| Registrar | Form | Cadastrado | Invalida | 1 INSERT |
| CRUD Lista | GET /list | HTML | Redis 15min | 1 SELECT |
| CRUD Criar | GET /new | Criado | Invalida | 1 INSERT |
| CRUD Editar | GET /edit | Atualizado | Invalida | 1 UPDATE |
| CRUD Deletar | GET /del | Deletado | Invalida | 1 DELETE |
| Relatório | GET /report | PDF/HTML | Nenhum | N SELECT |
| Exportar | GET /export | .xlsx | Nenhum | N SELECT |
| Config | GET /settings | Atualizado | Invalida | 1 UPDATE |

---

## 🔐 SEGURANÇA NOS FLUXOS

Cada fluxo implementa:

```
✅ CSRF Protection
   └─ Token em cada POST form

✅ Authentication Check
   └─ LoginRequiredMixin em toda view

✅ Authorization Check
   └─ AdminRequiredMixin onde necessário

✅ Input Validation
   └─ Form.clean() + Model validators

✅ SQL Injection Prevention
   └─ ORM Django (sem raw SQL)

✅ XSS Prevention
   └─ Template escaping automático

✅ Password Security
   └─ PBKDF2 hashing

✅ Session Security
   └─ HttpOnly + Secure cookies
```

---

## 📚 CONSULTE TAMBÉM

- **3_PROMPT_COMPLETO.md** - Detalhes de cada fase
- **4_CODIGO_PRONTO.md** - Implementação dos fluxos
- **5_QUICK_REFERENCE.md** - Comandos rápidos
- **DOCUMENTACAO_DJANGO.md** - Especificação completa

---

**Status:** ✅ Pronto para Usar  
**Versão:** 1.0  
**Última atualização:** 01/07/2026
