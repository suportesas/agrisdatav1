# 💻 CÓDIGO PRONTO - DJANGO
## Exemplos Copy & Paste para Implementação

---

## 📋 CONTEÚDO

Este arquivo contém **código pronto para copiar e colar** na sua implementação.

1. **settings.py** - Configuração Django completa
2. **models.py** - Todos os modelos de dados
3. **views.py** - Views principais (Login, Dashboard, CRUD)
4. **forms.py** - Formulários com validação
5. **urls.py** - Padrão de URLs
6. **signals.py** - Cache invalidation
7. **decorators.py** e **mixins.py** - Proteção de views
8. **management/criar_admin.py** - Command para criar admin

---

## ⚠️ NOTA IMPORTANTE

Este arquivo contém **resumo do código**. Para o código COMPLETO e DETALHADO:

👉 **Consulte o arquivo original:** `CODIGO_DJANGO_PRONTO.md` (na raiz da pasta)

---

## 🔧 settings.py (COPIE INTEIRO)

```python
# config/settings.py

import os
from pathlib import Path
from decouple import config, Csv
from datetime import timedelta
import dj_database_url  # Para Supabase

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-in-prod')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'django_filters',
    'crispy_forms',
    'crispy_bootstrap5',
    'apps.core',
    'apps.producao',
    'apps.relatorio',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ===== OPÇÃO 1: PostgreSQL Local =====
# Descomente esta seção para usar banco local
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME', default='packing_db'),
#         'USER': config('DB_USER', default='postgres'),
#         'PASSWORD': config('DB_PASSWORD', default=''),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default='5432'),
#     }
# }

# ===== OPÇÃO 2: Supabase (RECOMENDADO) =====
# Use DATABASE_URL da Supabase
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default=''),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Fallback para local se DATABASE_URL vazio
if not config('DATABASE_URL', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='packing_db'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Fortaleza'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.User'
LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'core:login'

SESSION_COOKIE_AGE = 86400 * 7
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ===== SUPABASE CONFIGURATION =====
# Se usar Supabase, adicione estas configurações extras
if 'supabase' in config('DATABASE_URL', default='').lower():
    # Supabase pooling
    DATABASES['default']['CONN_MAX_AGE'] = 600
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
    }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('CACHE_URL', default='redis://127.0.0.1:6379/0'),
    }
}

os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
```

---

## 📊 models.py (COPIE PARTES CONFORME NECESSÁRIO)

### User Model
```python
# apps/core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    """Usuário customizado com suporte a perfis."""
    
    PERFIL_CHOICES = [
        ('admin', 'Administrador'),
        ('usuario', 'Usuário Comum'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    perfil = models.CharField(max_length=10, choices=PERFIL_CHOICES, default='usuario')
    criado_em = models.DateTimeField(auto_now_add=True)
    modificado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        ordering = ['-criado_em']
    
    def __str__(self):
        return self.get_full_name() or self.email
    
    @property
    def eh_admin(self):
        return self.perfil == 'admin'
    
    @property
    def eh_usuario_ativo(self):
        return self.ativo and self.is_active
```

### Production Models
```python
# apps/producao/models.py

from django.db import models
from django.db.models import Sum, Count
from django.core.validators import MinLengthValidator, MinValueValidator
from django.utils import timezone
from apps.core.models import User

class Cultura(models.Model):
    """Tipos de culturas/produtos."""
    
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100, unique=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    modificado_em = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Cultura'
        verbose_name_plural = 'Culturas'
        ordering = ['nome']
        indexes = [models.Index(fields=['nome'])]
    
    def __str__(self):
        return self.nome
    
    def pode_deletar(self):
        """Verifica se pode ser deletada."""
        return not self.producao_set.exists()


class Embalador(models.Model):
    """Funcionários que embalam."""
    
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    codigo_barra = models.CharField(
        max_length=20, 
        unique=True, 
        validators=[MinLengthValidator(3)]
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    modificado_em = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Embalador'
        verbose_name_plural = 'Embaladores'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['codigo_barra']),
            models.Index(fields=['ativo']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.codigo_barra})"
    
    def pode_deletar(self):
        return not self.producao_set.exists()
    
    @property
    def producao_total(self):
        return self.producao_set.aggregate(Sum('quantidade'))['quantidade__sum'] or 0
    
    @property
    def reembalagem_total(self):
        return self.producao_set.filter(reembalagem=True).count()
    
    @property
    def percentual_reembalagem(self):
        total = self.producao_total
        if total == 0:
            return 0.0
        return (self.reembalagem_total / total) * 100


class Producao(models.Model):
    """Registros de produção."""
    
    TURNO_CHOICES = [
        ('Manhã', 'Manhã (5h-12h)'),
        ('Tarde', 'Tarde (12h-18h)'),
        ('Noite', 'Noite (18h-5h)'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    embalador = models.ForeignKey(Embalador, on_delete=models.PROTECT)
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT)
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES)
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    reembalagem = models.BooleanField(default=False)
    data = models.DateField(default=timezone.now)
    hora = models.TimeField()
    valor_bonificacao = models.DecimalField(max_digits=10, decimal_places=2)
    valor_penalidade = models.DecimalField(max_digits=10, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Produção'
        verbose_name_plural = 'Produções'
        ordering = ['-data', '-hora']
        indexes = [
            models.Index(fields=['-data']),
            models.Index(fields=['embalador', '-data']),
        ]
    
    def __str__(self):
        return f"{self.embalador.nome} - {self.cultura.nome}"
    
    @property
    def bonificacao_total(self):
        return self.quantidade * self.valor_bonificacao
    
    @property
    def penalidade_total(self):
        return self.valor_penalidade if self.reembalagem else 0
    
    @property
    def final_liquido(self):
        return self.bonificacao_total - self.penalidade_total
    
    @staticmethod
    def calcular_turno(hora):
        """Calcula turno baseado na hora."""
        h = hora.hour
        if 5 <= h < 12:
            return 'Manhã'
        elif 12 <= h < 18:
            return 'Tarde'
        else:
            return 'Noite'


class Configuracao(models.Model):
    """Configurações globais do sistema."""
    
    id = models.AutoField(primary_key=True)
    valor_bonificacao = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    valor_penalidade = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    criado_em = models.DateTimeField(auto_now_add=True)
    modificado_em = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Configuração'
        verbose_name_plural = 'Configurações'
    
    def __str__(self):
        return f"Bonif: R$ {self.valor_bonificacao} | Penal: R$ {self.valor_penalidade}"
    
    @classmethod
    def get_configuracao(cls):
        """Obtém ou cria a configuração padrão."""
        obj, created = cls.objects.get_or_create(id=1)
        return obj


# apps/relatorio/models.py

class ConfiguracaoLog(models.Model):
    """Histórico de alterações nas configurações."""
    
    id = models.BigAutoField(primary_key=True)
    valor_bonificacao_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    valor_bonificacao_novo = models.DecimalField(max_digits=10, decimal_places=2)
    valor_penalidade_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    valor_penalidade_novo = models.DecimalField(max_digits=10, decimal_places=2)
    alterado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_alteracao = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Log de Configuração'
        verbose_name_plural = 'Logs de Configuração'
        ordering = ['-data_alteracao']
```

---

## 📝 forms.py

```python
# apps/core/forms.py

from django import forms
from django.contrib.auth import authenticate
from apps.core.models import User

class LoginForm(forms.Form):
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'seu@email.com'
    }))
    senha = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Sua senha'
    }))
    
    def clean(self):
        email = self.cleaned_data.get('email')
        senha = self.cleaned_data.get('senha')
        
        if email and senha:
            self.user = authenticate(email=email, password=senha)
            if self.user is None:
                raise forms.ValidationError('Email ou senha inválidos.')
        
        return self.cleaned_data


# apps/producao/forms.py

from apps.producao.models import Producao, Cultura, Embalador

class ProducaoForm(forms.ModelForm):
    codigo_barra = forms.CharField(label='Código de Barras', widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Escanear...',
        'autofocus': True
    }))
    cultura = forms.ModelChoiceField(queryset=Cultura.objects.all(), label='Cultura', widget=forms.Select(attrs={
        'class': 'form-control'
    }))
    quantidade = forms.IntegerField(label='Quantidade', initial=1, widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'min': '1'
    }))
    reembalagem = forms.BooleanField(label='Reembalagem?', required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))
    
    class Meta:
        model = Producao
        fields = ['cultura', 'quantidade', 'reembalagem']


class CulturaForm(forms.ModelForm):
    class Meta:
        model = Cultura
        fields = ['nome']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da Cultura'
            })
        }


class EmbaladorForm(forms.ModelForm):
    class Meta:
        model = Embalador
        fields = ['nome', 'codigo_barra', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'codigo_barra': forms.TextInput(attrs={'class': 'form-control'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
```

---

## 🔗 urls.py (PADRÃO)

```python
# apps/core/urls.py

from django.urls import path
from apps.core import views

app_name = 'core'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
]

# apps/producao/urls.py

from django.urls import path
from apps.producao import views

app_name = 'producao'

urlpatterns = [
    path('registrar/', views.RegistrarProducaoView.as_view(), name='registrar'),
    path('lista/', views.ListaProducaoView.as_view(), name='lista'),
    path('culturas/', views.ListaCulturasView.as_view(), name='culturas_lista'),
    path('culturas/criar/', views.CriarCulturaView.as_view(), name='cultura_criar'),
    path('culturas/editar/<int:pk>/', views.EditarCulturaView.as_view(), name='cultura_editar'),
    path('embaladores/', views.ListaEmbaladoresView.as_view(), name='embaladores_lista'),
]

# config/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('producao/', include('apps.producao.urls')),
    path('relatorio/', include('apps.relatorio.urls')),
]
```

---

## 🎯 signals.py (CACHE INVALIDATION)

```python
# apps/producao/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from apps.producao.models import Producao, Configuracao

@receiver(post_save, sender=Producao)
@receiver(post_delete, sender=Producao)
def invalidar_cache_producao(sender, instance, **kwargs):
    """Invalida cache ao salvar/deletar produção."""
    cache.delete('dashboard_data')
    cache.delete(f'embalador_{instance.embalador_id}_stats')

@receiver(post_save, sender=Configuracao)
def invalidar_cache_configuracao(sender, instance, **kwargs):
    """Invalida cache de configuração."""
    cache.delete('configuracao')
```

---

## 🔐 decorators.py e mixins.py

```python
# apps/core/decorators.py

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    """Decorador para views que requerem admin."""
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.eh_admin:
            messages.error(request, 'Acesso negado. Você precisa ser administrador.')
            return redirect('core:login')
        return view_func(request, *args, **kwargs)
    return wrapped_view


# apps/core/mixins.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages

class AdminRequiredMixin(LoginRequiredMixin):
    """Mixin para views que requerem admin."""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.eh_admin:
            messages.error(request, 'Acesso negado. Você precisa ser administrador.')
            return redirect('core:login')
        return super().dispatch(request, *args, **kwargs)
```

---

## 📦 requirements.txt

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
pytest-cov==4.1.0
python-decouple==3.8
```

---

## 🚀 PRÓXIMOS PASSOS

1. **Copie código** de acordo com sua fase atual
2. **Adapte** conforme necessário (nomes, campos, lógica)
3. **Teste** cada parte antes de prosseguir
4. **Consulte** DOCUMENTACAO_DJANGO.md para detalhes técnicos
5. **Use** CHECKLIST_IMPLEMENTACAO.md para rastrear progresso

---

## 📌 IMPORTANTE

Este arquivo contém **código simplificado** para quick start.

Para **implementação completa com:**
- ✅ Views com lógica complexa
- ✅ Exportação Excel com formatação
- ✅ Cache com invalidation
- ✅ Testes completos
- ✅ Management commands

👉 **Consulte o arquivo original:** `CODIGO_DJANGO_PRONTO.md` (raiz da pasta)

---

**Status:** ✅ Pronto para Usar  
**Versão:** 1.0  
**Última atualização:** 01/07/2026
