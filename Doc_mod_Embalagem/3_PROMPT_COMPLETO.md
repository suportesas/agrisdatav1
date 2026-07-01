# 🎯 PROMPT COMPLETO - IMPLEMENTAÇÃO DO SISTEMA PACKING EM DJANGO
## Guia Detalhado para Desenvolvimento Completo

---

## 📋 CONTEXTO DO PROJETO

### O que você está desenvolvendo?
Um **sistema web de gerenciamento de produção para casa de embalagem de frutas/hortaliças**.

### Stack Tecnológico
- **Backend:** Python 3.10+ com Django 4.2
- **Database:** PostgreSQL 13+ (Local OU Supabase Cloud)
  - ✅ **Local:** PostgreSQL instalado localmente
  - ✅ **Supabase:** PostgreSQL gerenciado na nuvem (RECOMENDADO para produção)
- **Frontend:** Bootstrap 5 + Chart.js + DataTables
- **Cache:** Redis
- **Testing:** pytest + pytest-django
- **API:** Django REST Framework (opcional para mobile)

### Objetivo Principal
Migrar um sistema de **PHP + MySQL** para **Python + Django + PostgreSQL**, implementando:
- ✅ Melhorias de segurança (SQL Injection, CSRF, Validação)
- ✅ Auditoria completa
- ✅ Performance otimizada
- ✅ Código profissional e testável
- ✅ Documentação técnica

### ⚠️ IMPORTANTE: INTEGRAÇÃO COM ERP EXISTENTE

**Se você tem um ERP já em funcionamento:**

Este sistema pode ser:
1. **Módulo Standalone** - Sistema independente
2. **Integrado ao ERP** - Expandir módulo de embalagem existente

**Se usar o ERP agrisdatav1:**
- ✅ Expandir módulo `/embalagem/` existente
- ✅ Reutilizar autenticação/usuários do ERP
- ✅ Mapear: Culturas → Produtos, Embaladores → Funcionários
- ✅ Multi-tenant: Isolamento por empresa

👉 **Consulte:** `INTEGRACAO_ERP_AGRISDATAV1.md` para guia completo

## 🏗️ ARQUITETURA DO SISTEMA

### Funcionalidades Principais

#### 1. **Autenticação**
- Login com email/senha
- Dois perfis: Admin e Usuário
- Session-based authentication
- Password reset via email
- Proteção CSRF

#### 2. **Dashboard**
- KPIs: Total caixas, reembalagens, %, média diária
- Gráficos: Por dia, cultura, turno
- Filtros dinâmicos
- Exportação para Excel

#### 3. **Registro de Produção**
- Entrada via código de barras do embalador
- Seleção de cultura (salva em sessão)
- Turno calculado automaticamente (5-12/12-18/18-5)
- Checkbox para reembalagem
- Captura automática de data/hora

#### 4. **CRUD - Culturas, Embaladores, Usuários**
- Criar, listar, editar, deletar
- Proteção contra delete vinculado
- Validações
- Paginação e filtros
- DataTables para listagem

#### 5. **Relatórios**
- Bonificação por embalador
- Filtros por período
- Cálculos: SUM(quantidade × valor_bonificacao) - SUM(reembalagem × valor_penalidade)
- Totalizadores
- Exportação Excel

#### 6. **Configurações (Admin Only)**
- Valores de bonificação/penalidade
- Histórico de alterações
- Auditoria com quem alterou

---

## 📊 MODELOS DE DADOS

### User (Autenticação)
```
id (UUID)
email (unique)
first_name, last_name
perfil (admin | usuario)
ativo
criado_em, modificado_em
```

### Cultura
```
id (PK)
nome (unique, max=100)
criado_em, modificado_em, modificado_por (FK User)
```

### Embalador
```
id (PK)
nome (max=100)
codigo_barra (unique, max=20, min=3)
ativo
criado_em, modificado_em, modificado_por (FK User)
```

### Producao
```
id (BigAutoField)
embalador_id (FK)
cultura_id (FK)
turno (Enum: Manhã, Tarde, Noite) - AUTO
quantidade (PositiveInteger, default=1)
reembalagem (Boolean, default=False)
data, hora
valor_bonificacao, valor_penalidade (snapshot)
criado_em, criado_por (FK User)

Properties:
- bonificacao_total = quantidade × valor_bonificacao
- penalidade_total = reembalagem ? valor_penalidade : 0
- final_liquido = bonificacao_total - penalidade_total
```

### Configuracao
```
id = 1 (singleton)
valor_bonificacao (decimal, default=1.00, min=0.01)
valor_penalidade (decimal, default=1.00, min=0.01)
criado_em, modificado_em, modificado_por (FK User)

Método: get_configuracao() - obtém ou cria padrão
```

### ConfiguracaoLog
```
id (BigAutoField)
valor_bonificacao_anterior, valor_bonificacao_novo
valor_penalidade_anterior, valor_penalidade_novo
alterado_por (FK User)
data_alteracao (auto_now_add)
motivo (TextField, opcional)
```

---

## 🔐 SEGURANÇA IMPLEMENTADA

### Proteção contra SQL Injection
```python
# ❌ NUNCA fazer isto:
queryset = Usuario.objects.raw(f"SELECT * FROM usuarios WHERE email = '{email}'")

# ✅ FAZER ISTO:
usuario = Usuario.objects.filter(email=email).first()
```

### CSRF Token
```html
<!-- SEMPRE incluir em formulários POST -->
<form method="POST">
    {% csrf_token %}
    <!-- campos -->
</form>
```

### Validação em Múltiplas Camadas
- **Camada 1:** Model validators
- **Camada 2:** Form clean methods
- **Camada 3:** View lógica adicional

### Autenticação
- ✅ LoginRequiredMixin em todas views protegidas
- ✅ AdminRequiredMixin para views admin
- ✅ Verificar perfil antes de operações críticas

### Password Hashing
- Django faz automaticamente com PBKDF2

---

## 📁 ESTRUTURA DE PASTAS (EXATA)

```
packing/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── core/
│   │   ├── models.py (User)
│   │   ├── views.py (Login, Dashboard)
│   │   ├── forms.py (LoginForm)
│   │   ├── urls.py
│   │   ├── signals.py
│   │   └── decorators.py
│   │
│   ├── producao/
│   │   ├── models.py (Cultura, Embalador, Producao)
│   │   ├── views.py (CRUD + Registrar)
│   │   ├── forms.py (ProducaoForm, etc)
│   │   ├── urls.py
│   │   ├── signals.py
│   │   └── management/
│   │       └── commands/
│   │           └── criar_admin.py
│   │
│   ├── relatorio/
│   │   ├── models.py (ConfiguracaoLog)
│   │   ├── views.py (Relatórios, Exports)
│   │   ├── urls.py
│   │   └── services.py
│   │
│   └── api/ (opcional)
│       ├── serializers.py
│       └── viewsets.py
│
├── templates/
│   ├── base.html
│   ├── includes/
│   │   ├── navbar.html
│   │   ├── footer.html
│   │   └── messages.html
│   ├── auth/
│   │   └── login.html
│   ├── producao/
│   │   ├── registrar.html
│   │   ├── lista.html
│   │   └── cultura_lista.html
│   ├── dashboard.html
│   └── relatorio_bonificacao.html
│
├── static/
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   └── custom.css
│   ├── js/
│   │   ├── jquery.js
│   │   ├── datatables.js
│   │   ├── chart.js
│   │   └── app.js
│   └── img/
│
├── logs/
│   └── app.log
│
└── tests/
    ├── test_models.py
    ├── test_views.py
    └── test_auth.py
```

---

## 🚀 SETUP INICIAL (PASSO A PASSO)

### Passo 1: Criar Ambiente
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### Passo 2: Instalar Django
```bash
pip install django
django-admin startproject config .
python manage.py startapp apps.core
python manage.py startapp apps.producao
python manage.py startapp apps.relatorio
```

### Passo 3: Instalar Dependências
```bash
pip install -r requirements.txt
```

### Passo 4: Configurar settings.py
Copiar arquivo completo de 4_CODIGO_PRONTO.md

### Passo 5: Banco de Dados
```bash
# PostgreSQL
createdb packing_db
createuser -P packing

# Django
python manage.py makemigrations
python manage.py migrate
```

### Passo 6: Rodar
```bash
python manage.py runserver
# http://localhost:8000
```

---

## 📝 19 FASES DE IMPLEMENTAÇÃO

### FASE 1: Models (Dia 1) - 4 horas
- [ ] Copiar User, Cultura, Embalador, Producao models
- [ ] Copiar ConfiguracaoLog
- [ ] Rodar migrations
- [ ] Testar no shell

### FASE 2: Forms (Dia 2) - 3 horas
- [ ] LoginForm, ProducaoForm, CulturaForm, EmbaladorForm
- [ ] ConfiguracaoForm
- [ ] Adicionar validators

### FASE 3: Autenticação (Dia 3) - 4 horas
- [ ] CustomLoginView
- [ ] Template login.html
- [ ] LogoutView
- [ ] Proteção de rotas (mixins)

### FASE 4: Dashboard (Dia 4) - 5 horas
- [ ] DashboardView com KPIs
- [ ] Gráficos com Chart.js
- [ ] Filtros
- [ ] Template dashboard.html

### FASE 5: Registrar Produção (Dia 5) - 4 horas
- [ ] RegistrarProducaoView
- [ ] Template com input barcode
- [ ] Auto-calculate turno
- [ ] JavaScript para UX

### FASE 6: CRUD Culturas (Dia 6) - 3 horas
- [ ] Create, Read, Update, Delete views
- [ ] Templates CRUD
- [ ] Paginação

### FASE 7: CRUD Embaladores (Dia 7) - 3 horas
- [ ] Similar ao Culturas
- [ ] Mostrar estatísticas

### FASE 8: CRUD Usuários (Dia 8) - 3 horas
- [ ] AdminRequiredMixin
- [ ] Gerenciar perfis

### FASE 9: Listagem Produção (Dia 9) - 2 horas
- [ ] ListaProducaoView com filtros
- [ ] DataTables
- [ ] select_related, prefetch_related

### FASE 10: Relatório Bonificação (Dia 10) - 3 horas
- [ ] Cálculos: bonif, penal, final
- [ ] Totalizadores
- [ ] Template

### FASE 11: Exportação Excel (Dia 11) - 3 horas
- [ ] openpyxl
- [ ] Formatação profissional
- [ ] Fórmulas

### FASE 12: Configurações (Dia 12) - 2 horas
- [ ] ConfiguracaoView
- [ ] Editar valores
- [ ] Logar mudanças

### FASE 13: Auditoria (Dia 13) - 2 horas
- [ ] AuditoriaView
- [ ] Listar ConfiguracaoLog
- [ ] Mostrar quem alterou

### FASE 14-15: Estilo (2 dias) - 6 horas
- [ ] CSS customizado
- [ ] Bootstrap theme
- [ ] Responsividade

### FASE 16-17: Testes (2 dias) - 6 horas
- [ ] test_models.py
- [ ] test_views.py
- [ ] Coverage > 80%

### FASE 18: Documentação (1 dia) - 2 horas
- [ ] Docstrings
- [ ] README.md
- [ ] API docs

### FASE 19: Deploy (1 dia) - 4 horas
- [ ] Gunicorn
- [ ] Nginx
- [ ] SSL

---

## ✅ CHECKLIST DE QUALIDADE

### Segurança
- [ ] Nenhuma SQL injection
- [ ] CSRF tokens em todos formulários
- [ ] XSS protection
- [ ] Passwords com PBKDF2
- [ ] Validação multi-layer

### Performance
- [ ] Sem N+1 queries
- [ ] Índices corretos
- [ ] Cache implementado
- [ ] Paginação

### Funcionalidade
- [ ] Login funciona
- [ ] Dashboard mostra dados corretos
- [ ] CRUD completo
- [ ] Filtros funcionam
- [ ] Relatórios calculam correto
- [ ] Exportação funciona

### Código
- [ ] Sem erros de sintaxe
- [ ] DRY (Don't Repeat Yourself)
- [ ] Docstrings
- [ ] PEP 8

### Testes
- [ ] Coverage > 80%
- [ ] Todos passando
- [ ] Testes de segurança

---

## 🎯 DICAS IMPORTANTES

### Ao Implementar
1. ✅ Sempre use ORM Django
2. ✅ Adicione {% csrf_token %} em TODOS formulários POST
3. ✅ Use select_related/prefetch_related
4. ✅ Valide em modelo, form E view
5. ✅ Use signals para efeitos colaterais
6. ✅ Adicione docstrings
7. ✅ Testes ENQUANTO desenvolve
8. ✅ Commit git frequente

### Debug
1. Use `python manage.py shell`
2. Adicione `print()` ou debugger
3. Verifique `DEBUG=True`
4. Use django-debug-toolbar
5. Logs em vez de print()

---

## 📚 REFERÊNCIAS

| Arquivo | Use Para |
|---------|----------|
| 4_CODIGO_PRONTO.md | Copiar código |
| 5_QUICK_REFERENCE.md | Referência rápida |
| 6_CHECKLIST_IMPLEMENTACAO.md | Planejamento |
| DOCUMENTACAO_DJANGO.md | Detalhes técnicos |

---

## 🚀 PRÓXIMOS PASSOS

### Hoje
1. [ ] Ler este arquivo completamente
2. [ ] Revisar 6_CHECKLIST_IMPLEMENTACAO.md
3. [ ] Executar setup inicial

### Amanhã
1. [ ] Implementar Models (Fase 1)
2. [ ] Rodar migrations
3. [ ] Criar dados de teste

### Semana 1
1. [ ] Models + Forms + Auth
2. [ ] Dashboard básico
3. [ ] Registrar Produção

---

**Status:** ✅ Pronto para Começar  
**Data:** 01/07/2026  
**Versão:** 1.0

**Próximo passo: Leia 4_CODIGO_PRONTO.md →**
