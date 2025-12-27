"""
Django settings for core project - ERP Agrícola SaaS
Configurações corrigidas e otimizadas
"""

import os
from pathlib import Path
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 's_#plt(uejrjtdoh&_((ajet($=b+euzkeyn))0v0+puysf61+'

#'django-insecure-lopjd&u(&g8ei6j4!vltv6b1xgd(5fxn-kz3*35l0ma!2&8#+h'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']  # Em produção, especifique os domínios permitidos


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Apps de terceiros
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',  # Para API (instale: pip install django-cors-headers)
    
    # Apps do projeto
    'usuarios',
    'empresas',
    'dashboard',
    'cadastros',
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
    'core.middleware.EmpresaBloqueadaMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
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


# Internationalization - CORRIGIDO PARA PT-BR
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Fortaleza'  # Fuso horário do RN
USE_I18N = True
USE_L10N = True
USE_TZ = True

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
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

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
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React/Vue frontend
    "http://localhost:8080",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True


# ============================================
# EMAIL CONFIGURATION
# ============================================
# Desenvolvimento - console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = 'ERP Agrícola <no-reply@erp-agricola.com>'
EMAIL_SUBJECT_PREFIX = '[ERP Agrícola] '


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
# SEGURANÇA
# ============================================
# Sessão expira ao fechar navegador
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 86400  # 24 horas


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
            'level': 'DEBUG',
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

# Cria pasta de logs se não existir
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)

# Procure por estas configurações:
USE_L10N = True  # Se True, formata datas automaticamente
DATE_INPUT_FORMATS = [...]  # Pode estar forçando formato brasileiro