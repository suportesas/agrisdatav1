# ⚡ QUICK REFERENCE - SISTEMA PACKING DJANGO
## Guia Rápido de Implementação

---

## 🎯 VISÃO GERAL EM 60 SEGUNDOS

**Sistema:** Gerenciamento de produção em casa de embalagem  
**Stack Django:** Python 3.10+ | Django 4.2 | PostgreSQL 13+  
**Modelos:** 5 tabelas (User, Cultura, Embalador, Producao, Configuracao)  
**Funcionalidades:** CRUD | Dashboard | Relatórios | Exportação Excel  
**Segurança:** ORM | CSRF | Validação | Auditoria | Rate Limiting  

---

## 📁 ESTRUTURA RÁPIDA

```
packing/
├── config/           # settings, urls, wsgi
├── apps/
│   ├── core/        # Auth, Dashboard
│   ├── producao/    # CRUD, Registro
│   ├── relatorio/   # Relatórios, Exports
│   └── api/         # REST Framework
├── templates/       # HTML Bootstrap 5
├── static/          # CSS, JS, Assets
├── manage.py
└── requirements.txt
```

---

## 🚀 INSTALAÇÃO (5 PASSOS)

```bash
# 1. Ambiente
python -m venv venv && source venv/bin/activate

# 2. Dependências
pip install -r requirements.txt

# 3. Banco
python manage.py migrate

# 4. Admin
python manage.py createsuperuser

# 5. Rodas
python manage.py runserver
```

---

## 📊 MODELOS PRINCIPAIS

### User (Autenticação)
```python
email (PK)
nome
perfil (admin | usuario)
ativo
criado_em, modificado_em
```

### Producao (Core)
```python
id (PK)
embalador_id (FK)
cultura_id (FK)
turno (Enum: Manhã, Tarde, Noite)
quantidade (int)
reembalagem (bool)
data, hora
valor_bonificacao, valor_penalidade
criado_por (FK User)
```

### Cultura, Embalador, Configuracao
```
Campos simples: id, nome, código, valores
Auditoria: criado_em, modificado_em, modificado_por
Restrições: unique, not null, validators
```

---

## 🔐 AUTENTICAÇÃO (PRONTO)

### LoginView
```python
class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('core:dashboard')
```

### Proteger Views
```python
# Option 1: Decorator
@login_required
def view(request):
    pass

# Option 2: Mixin
class MyView(LoginRequiredMixin, TemplateView):
    pass

# Option 3: Admin Check
if not request.user.perfil == 'admin':
    raise PermissionDenied
```

---

## 🎨 VIEWS ESSENCIAIS

### Dashboard
```python
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'
    # KPIs: total_caixas, reembalagens, %, média
    # Gráficos: por dia, cultura, turno
```

### Registrar Produção
```python
class RegistrarProducaoView(LoginRequiredMixin, CreateView):
    # Campo: codigo_barra
    # Auto: turno, data, hora, valores de config
    # Session: guarda cultura_selecionada
```

### CRUD (Cultura, Embalador, Usuário)
```python
# Create, Read, Update, Delete
class CriarXView(LoginRequiredMixin, CreateView)
class ListaXView(LoginRequiredMixin, ListView)
class EditarXView(LoginRequiredMixin, UpdateView)
class DeletarXView(LoginRequiredMixin, DeleteView)
```

### Relatório Bonificação
```python
class RelatorioBonificacaoView(LoginRequiredMixin, TemplateView):
    # Filtro: data_inicio, data_fim
    # Cálculo: SUM(quantidade), SUM(reembalagem), bonif, penal, final
    # Totalizadores
```

### Exportar Excel
```python
class ExportarExcelView(LoginRequiredMixin, View):
    # openpyxl: criar workbook
    # Formatação: cores, bordas, fórmulas
    # Response: HttpResponse com arquivo
```

---

## 📝 FORMULÁRIOS (PRONTO)

### Login
```python
class LoginForm(forms.Form):
    email = EmailField()
    senha = CharField(widget=PasswordInput)
    # clean(): valida credenciais
```

### Producao
```python
class ProducaoForm(forms.ModelForm):
    codigo_barra = CharField()  # Escanear
    cultura = ModelChoiceField() # Select
    quantidade = IntegerField(min=1)
    reembalagem = BooleanField()
```

### CRUD (Cultura, Embalador, Usuario)
```python
class XForm(forms.ModelForm):
    # Widgets: form-control, form-select
    # Bootstrap 5 styling
```

---

## 🔗 URLS (PROTOTIPO)

```python
# Core
path('', DashboardView.as_view(), name='dashboard')
path('login/', CustomLoginView.as_view(), name='login')
path('logout/', LogoutView.as_view(), name='logout')

# Producao
path('producao/registrar/', RegistrarProducaoView.as_view())
path('producao/lista/', ListaProducaoView.as_view())
path('culturas/', CRUD...)
path('embaladores/', CRUD...)

# Relatorio
path('relatorio/bonificacao/', RelatorioBonificacaoView.as_view())
path('relatorio/exportar/', ExportarExcelView.as_view())
```

---

## 💾 DATABASE (POSTGRESQL)

### Opção 1: PostgreSQL Local

```bash
# Setup
CREATE DATABASE packing_db;
CREATE USER packing WITH PASSWORD 'senha';
ALTER ROLE packing SET client_encoding TO 'utf8';

# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'packing_db',
        'USER': 'packing',
        'PASSWORD': 'senha',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Migrate
python manage.py migrate
```

### Opção 2: Supabase (RECOMENDADO para Produção)

```bash
# 1. Criar conta: https://supabase.com
# 2. Novo projeto → Copiar Database URL
# 3. Adicionar em .env
DATABASE_URL=postgresql://postgres:[password]@[project-id].supabase.co:5432/postgres

# 4. Django settings.py
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
    )
}

# 5. Migrate
python manage.py migrate
```

**Vantagens Supabase:**
- ✅ Sem manutenção de servidor
- ✅ Backups automáticos
- ✅ SSL por padrão
- ✅ Escalável automaticamente
- ✅ Integração fácil

---

## 🔧 SETTINGS KEY CONFIG

```python
# auth
AUTH_USER_MODEL = 'core.User'
LOGIN_URL = 'core:login'

# security
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# cache (Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
    }
}

# email (reset password)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
```

---

## 🎨 TEMPLATE BASE (EXEMPLO)

```html
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <!-- Navbar -->
    {% include 'includes/navbar.html' %}
    
    <!-- Mensagens -->
    {% include 'includes/messages.html' %}
    
    <!-- Content -->
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>
    
    <!-- Scripts -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
</body>
</html>
```

---

## 📊 GRÁFICOS (CHART.JS)

```html
<!-- Template -->
<canvas id="chartCaixasPorDia"></canvas>

<!-- JavaScript -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
    const ctx = document.getElementById('chartCaixasPorDia').getContext('2d');
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: {{ dados_graficos.dias|safe }},
            datasets: [{
                label: 'Caixas por Dia',
                data: {{ dados_graficos.valores_dia|safe }},
                borderColor: 'rgb(75, 192, 192)',
            }]
        }
    });
</script>
```

---

## 🧪 TESTES (PYTEST)

```bash
# Instalar
pip install pytest pytest-django pytest-cov

# Rodar todos
pytest

# Com cobertura
pytest --cov=apps tests/

# Específico
pytest tests/test_auth.py
```

### Exemplo Test
```python
# tests/test_producao.py
def test_registrar_producao(client, user_factory):
    user = user_factory()
    client.force_login(user)
    
    response = client.post('/producao/registrar/', {
        'codigo_barra': '0001',
        'cultura_id': 1,
    })
    
    assert response.status_code == 302
    assert Producao.objects.count() == 1
```

---

## 📦 DEPENDÊNCIAS ESSENCIAIS

```
Django==4.2.11
djangorestframework==3.14.0
django-filter==24.1
django-crispy-forms==2.1
crispy-bootstrap5==2.0.2
psycopg2-binary==2.9.9
openpyxl==3.1.2
celery==5.3.6
redis==5.0.1
pytest-django==4.7.0
```

---

## 🚀 DEPLOY CHECKLIST

```
[ ] DEBUG = False
[ ] SECRET_KEY = secure random
[ ] ALLOWED_HOSTS configurado
[ ] Database = PostgreSQL produção
[ ] Email = SMTP real
[ ] Statics = coletados (collectstatic)
[ ] Cache = Redis produção
[ ] Logs = arquivo rotativo
[ ] SSL = HTTPS
[ ] Sentry = integrado
[ ] Backup = automático
[ ] Monitoring = ativo
```

---

## 🔍 DEBUG COMUM

### Error: "No such table"
```bash
python manage.py migrate
```

### Error: "TemplateDoesNotExist"
```python
# settings.py
TEMPLATES[0]['DIRS'] = [os.path.join(BASE_DIR, 'templates')]
```

### Error: "CSRF token missing"
```html
<!-- form -->
{% csrf_token %}
```

### Error: "Permission denied"
```python
# decorador
@login_required
# ou mixin
LoginRequiredMixin
```

---

## 📚 REFERÊNCIAS

- **Django Docs:** https://docs.djangoproject.com/
- **DRF:** https://www.django-rest-framework.org/
- **Bootstrap 5:** https://getbootstrap.com/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **openpyxl:** https://openpyxl.readthedocs.io/

---

## 💡 DICAS IMPORTANTES

1. **ORM First:** Use QuerySet do Django, NÃO raw SQL
2. **Signals:** Use para cache invalidation e logging
3. **Middleware:** Para proteção global (CORS, Security)
4. **Celery:** Para tarefas pesadas (exports, emails)
5. **Cache:** Redis para session e query cache
6. **Test:** Mínimo 80% coverage
7. **Logging:** Não use print(), use logger
8. **Secrets:** Use .env para tudo sensível
9. **Security:** CSRF, HTTPS, Rate Limit
10. **Performance:** select_related, prefetch_related, índices

---

**Status:** ✅ Pronto para Codificação  
**Última atualização:** 01/07/2026  
**Versão:** 1.0
