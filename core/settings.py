"""
Django settings for core project - ERP Agrícola SaaS
Configurações corrigidas e otimizadas
"""

import os
import sys
import socket
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente do arquivo .env
load_dotenv(BASE_DIR / '.env')


def get_bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 't', 'yes', 'y', 'on'}


def get_list_env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(',') if item.strip()]


# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = get_bool_env('DEBUG', False)

SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-only-insecure-secret-key-change-me-in-env'
    else:
        raise ImproperlyConfigured('Defina SECRET_KEY no arquivo .env antes de iniciar o sistema.')

ALLOWED_HOSTS = get_list_env('ALLOWED_HOSTS', ['localhost', '127.0.0.1'])


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Apps de terceiros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',  # Para API (instale: pip install django-cors-headers)
    'widget_tweaks',  # Para customização de widgets de formulários
    
    # Apps do projeto
    'core',  # Configurações do sistema
    'usuarios',
    'empresas',
    'dashboard',
    'metricas',  # Dashboard Executivo e Métricas
    'cadastros',
    'patrimonio',  # Módulo de Patrimônio
    'produtos',
    'estoque',
    'compras',
    'financeiro',  # Módulo Contábil - Contas a Pagar, Juros, Multas
    'exportacao',  # Módulo de Exportação e Booking
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # CORS para API
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Middleware customizado
    'core.middleware.empresa_bloqueada.EmpresaBloqueadaMiddleware',
    'core.middleware.fornecedor_portal_only.FornecedorPortalOnlyMiddleware',
    'core.middleware.restrito_produtor.RestrictProdutorMiddleware',
]

ROOT_URLCONF = 'core.urls'

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
                'django.template.context_processors.media',  # Para upload de arquivos
                'core.context_processors.alertas_estoque',  # Context processor customizado para alertas
                'core.context_processors.notificacoes_emprestimo',  # Mensagens não lidas de empréstimos no menu
                'usuarios.context_processors.supabase_context',  # Injecta contexto Supabase
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# By default use SQLite for local development. To use PostgreSQL, set environment variables:
# PG_NAME, PG_USER, PG_PASSWORD, PG_HOST, PG_PORT
def _host_resolves(hostname: str) -> bool:
    """Retorna True quando o hostname pode ser resolvido por DNS."""
    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except OSError:
        return False


PG_NAME = os.getenv('PG_NAME')
PG_HOST = os.getenv('PG_HOST', 'localhost')
DB_FALLBACK_SQLITE = get_bool_env('DB_FALLBACK_SQLITE', DEBUG)
DB_FORCE_SQLITE = get_bool_env('DB_FORCE_SQLITE', False)

use_postgres = bool(PG_NAME) and not DB_FORCE_SQLITE
if use_postgres and DB_FALLBACK_SQLITE and not _host_resolves(PG_HOST):
    # Em ambiente de desenvolvimento, evita quebrar o app inteiro se o DNS do banco externo falhar.
    use_postgres = False

if use_postgres:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': PG_NAME,
            'USER': os.getenv('PG_USER', ''),
            'PASSWORD': os.getenv('PG_PASSWORD', ''),
            'HOST': PG_HOST,
            'PORT': os.getenv('PG_PORT', '5432'),
            # Configurações críticas para Supabase
            'CONN_MAX_AGE': 600,  # Reutilizar conexão por 10 minutos
            'OPTIONS': {
                'connect_timeout': 10,  # Timeout de conexão 10s
                'options': '-c statement_timeout=30000'  # Timeout SQL 30s
            },
            'ATOMIC_REQUESTS': False,  # Evitar locks desnecessários
            # Evita erro "InvalidCursorName" em conexões pool/proxy
            # (ex.: Supabase/PgBouncer) durante renderização de querysets em forms.
            'DISABLE_SERVER_SIDE_CURSORS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================
# CACHE CONFIGURATION (Redis ou Memcached)
# ============================================
# Se usar PostgreSQL (Supabase), cache é importante
if os.getenv('PG_NAME'):
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'erp-agricola-cache',
            'TIMEOUT': 300,  # 5 minutos
            'OPTIONS': {
                'MAX_ENTRIES': 10000
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'erp-agricola-cache',
        }
    }


# Internationalization - CORRIGIDO PARA PT-BR
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Fortaleza'  # Fuso horário do RN
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Encoding configuration - UTF-8 para suportar caracteres especiais
FILE_CHARSET = 'utf-8'
DEFAULT_CHARSET = 'utf-8'

# Formato de data brasileiro
DATE_FORMAT = 'd/m/Y'
DATETIME_FORMAT = 'd/m/Y H:i:s'
DATE_INPUT_FORMATS = ['%d/%m/%Y', '%Y-%m-%d']


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# ============================================
# MEDIA FILES (UPLOADS) - CONFIGURAÇÃO CORRETA
# ============================================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================
# SUPABASE STORAGE CONFIGURATION
# ============================================
SUPABASE_STORAGE_ENABLED = bool(os.getenv('SUPABASE_URL'))
SUPABASE_STORAGE_USE_AS_DEFAULT = get_bool_env('SUPABASE_STORAGE_USE_AS_DEFAULT', SUPABASE_STORAGE_ENABLED)
SUPABASE_STORAGE_DEFAULT_BUCKET = 'uploads-gerais'

SUPABASE_STORAGE_BUCKETS = {
    'empresas-logos': 'Logos de empresas',
    'documentos': 'Documentos (PDF, Word, Excel)',
    'produtos-imagens': 'Fotos de produtos',
    'funcionarios-fotos': 'Fotos de colaboradores',
    'compras-xml': 'Arquivos XML de compras',
    'safra-imagens': 'Imagens de safra',
    'cultura-imagens': 'Imagens de culturas',
    'uploads-gerais': 'Uploads diversos',
}

SUPABASE_STORAGE_PUBLIC_BUCKETS = {
    'empresas-logos',
    'produtos-imagens',
    'funcionarios-fotos',
    'uploads-gerais',
}

SUPABASE_STORAGE_SIGNED_URL_TTL = int(os.getenv('SUPABASE_STORAGE_SIGNED_URL_TTL', '3600'))

SUPABASE_STORAGE_BUCKET_ROUTES = [
    ('empresas/logos/', 'empresas-logos'),
    ('funcionarios/fotos/', 'funcionarios-fotos'),
    ('usuarios/fotos/', 'funcionarios-fotos'),
    ('safra/', 'safra-imagens'),
    ('culturas/imagens/', 'cultura-imagens'),
    ('produtos/documentos/', 'documentos'),
    ('fazendas/documentos/', 'documentos'),
    ('fornecedores/documentos/', 'documentos'),
    ('clientes/documentos/', 'documentos'),
    ('funcionarios/documentos/', 'documentos'),
    ('rh/', 'documentos'),
    ('vehicle_docs/', 'documentos'),
    ('motorista_docs/', 'documentos'),
    ('comprovantes_pagamento/', 'documentos'),
    ('compras/nfe/', 'compras-xml'),
    ('produtos/', 'produtos-imagens'),
    ('pragas/', 'uploads-gerais'),
    ('monitoramento_mip/', 'uploads-gerais'),
    ('monitoramento_pontos/', 'uploads-gerais'),
    ('compras/divergencias/', 'uploads-gerais'),
    ('patrimonio/', 'uploads-gerais'),
    ('vendedores/fotos/', 'uploads-gerais'),
    ('exportacao/ordens_coleta/fotos/', 'uploads-gerais'),
]

if SUPABASE_STORAGE_USE_AS_DEFAULT:
    STORAGES = {
        'default': {
            'BACKEND': 'core.supabase_storage.RoutedSupabaseStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
    DEFAULT_FILE_STORAGE = 'core.supabase_storage.RoutedSupabaseStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============================================
# AUTENTICAÇÃO E USUÁRIOS
# ============================================
AUTH_USER_MODEL = 'usuarios.Usuario'
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'


# ============================================
# REST FRAMEWORK & JWT
# ============================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] += (
        'rest_framework.renderers.BrowsableAPIRenderer',
    )

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# CORS Settings (para API)
CORS_ALLOWED_ORIGINS = get_list_env('CORS_ALLOWED_ORIGINS', [
    'http://localhost:3000',
    'http://localhost:8080',
    'http://127.0.0.1:3000',
])
CORS_ALLOW_CREDENTIALS = True


# ============================================
# SUPABASE CONFIGURATION (PostgreSQL + Auth)
# ============================================
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
AUTH_MODE = os.getenv('AUTH_MODE', 'django')  # 'django', 'dual', 'supabase'

# Validação em produção
if not DEBUG:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ImproperlyConfigured(
            'SUPABASE_URL e SUPABASE_ANON_KEY devem ser configuradas em produção'
        )

# Google OAuth (para Supabase)
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')


# ============================================
# EMAIL CONFIGURATION
# ============================================
# Para testar sem enviar emails reais, use:
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Para enviar emails reais via SMTP:
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')  # ou smtp-mail.outlook.com, smtp.office365.com
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')  # seu email completo
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')  # senha de app (não a senha normal)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'ERP Agrícola <no-reply@erp-agricola.com>')
EMAIL_SUBJECT_PREFIX = '[ERP Agrícola] '

# Domínio público do sistema (usado em links de e-mail).
# Em desenvolvimento: configure com ngrok (ex: abc123.ngrok-free.app)
# Em produção: coloque o domínio real (ex: erp.minhaempresa.com.br)
SITE_DOMAIN = os.getenv('SITE_DOMAIN', '')   # vazio = usa o host da requisição
SITE_HTTPS = get_bool_env('SITE_HTTPS', False)

# CSRF: aceita origens confiáveis via .env e também o SITE_DOMAIN configurado.
# Exemplo .env: CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app,https://erp.minhaempresa.com.br
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if SITE_DOMAIN:
    csrf_origin = f"https://{SITE_DOMAIN}" if SITE_HTTPS else f"http://{SITE_DOMAIN}"
    if csrf_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(csrf_origin)

# IMPORTANTE: Crie um arquivo .env na raiz do projeto com:
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=seu.email@gmail.com
# EMAIL_HOST_PASSWORD=sua_senha_de_app_aqui
# DEFAULT_FROM_EMAIL=ERP Agrícola <seu.email@gmail.com>


# ============================================
# CONFIGURAÇÕES DO SISTEMA SAAS
# ============================================
# Dias de teste gratuito
DIAS_TESTE_GRATIS = 15

# Tolerância após vencimento (dias)
DIAS_TOLERANCIA_VENCIMENTO = 5

# Limites padrão por plano (podem ser sobrescritos no banco)
LIMITES_PLANO = {
    'PEQUENO': {
        'fazendas': 1,
        'usuarios': 3,
        'talhoes': 10,
        'produtos': 5,
    },
    'MEDIO': {
        'fazendas': 3,
        'usuarios': 10,
        'talhoes': 50,
        'produtos': 20,
    },
    'GRANDE': {
        'fazendas': 999,  # Ilimitado
        'usuarios': 999,
        'talhoes': 999,
        'produtos': 999,
    },
}


# ============================================
# FEATURE FLAGS (FASE 0 - LIBERACAO SEGURA)
# ============================================
# Objetivo: habilitar releases graduais por modulo sem impactar fluxos estaveis.
#
# Uso recomendado no codigo:
# from core.feature_flags import is_feature_enabled
# if is_feature_enabled('COMPRAS_XML_IMPORT'):
#     ... novo fluxo ...

FEATURE_FLAGS = {
    # Fase 1
    'COMPRAS_XML_IMPORT': get_bool_env('FF_COMPRAS_XML_IMPORT', False),

    # Fase 2
    'ESTOQUE_QUARENTENA_BLOQUEIO': get_bool_env('FF_ESTOQUE_QUARENTENA_BLOQUEIO', False),
    'ESTOQUE_DEVOLUCOES_FLUXO': get_bool_env('FF_ESTOQUE_DEVOLUCOES_FLUXO', False),

    # Fase 3
    'RASTREABILIDADE_FULL_CHAIN': get_bool_env('FF_RASTREABILIDADE_FULL_CHAIN', False),

    # Fase 4
    'FINANCEIRO_RENEGOCIACAO': get_bool_env('FF_FINANCEIRO_RENEGOCIACAO', False),

    # Fase 6
    'RECEITUARIO_AGRONOMICO_V1': get_bool_env('FF_RECEITUARIO_AGRONOMICO_V1', False),

    # Fase 7
    'ARMADOR_INTEGRACOES_EXTERNAS': get_bool_env('FF_ARMADOR_INTEGRACOES_EXTERNAS', False),
}


# ============================================
# SEGURANÇA
# ============================================
# Sessão expira ao fechar navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 86400  # 24 horas
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = get_bool_env('SESSION_COOKIE_SECURE', not DEBUG)
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
CSRF_COOKIE_SECURE = get_bool_env('CSRF_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_HTTPONLY = get_bool_env('CSRF_COOKIE_HTTPONLY', False)
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'Lax')
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'DENY')
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'same-origin')
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.getenv('SECURE_CROSS_ORIGIN_OPENER_POLICY', 'same-origin')
SECURE_SSL_REDIRECT = get_bool_env('SECURE_SSL_REDIRECT', False)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if get_bool_env('USE_X_FORWARDED_PROTO', False) else None

if not DEBUG:
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = get_bool_env('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = get_bool_env('SECURE_HSTS_PRELOAD', True)
else:
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False


# ============================================
# LOGGING
# ============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'erp_agricola.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Durante test runs, reduz ruído ajustando o nível de log do servidor HTTP
if 'test' in sys.argv or any('pytest' in s for s in sys.argv):
    # Silencia mensagens como "Bad Request: /path" ou "Conflict: /path" durante testes
    LOGGING['loggers'].setdefault('django.server', {'handlers': ['console'], 'level': 'ERROR', 'propagate': False})
    LOGGING['loggers'].setdefault('django.request', {'handlers': ['console'], 'level': 'ERROR', 'propagate': False})

# Cria pasta de logs se não existir
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Procure por estas configurações:
USE_L10N = True  # Se True, formata datas automaticamente
DATE_INPUT_FORMATS = [...]  # Pode estar forçando formato brasileiro