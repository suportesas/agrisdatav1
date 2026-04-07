"""
URLs para autenticação Supabase
"""

from django.urls import path
from . import views, api

app_name = 'supabase_auth'

urlpatterns = [
    # ============================================================
    # PÁGINAS DE AUTENTICAÇÃO (GET)
    # ============================================================
    path('login-page/', views.login_page, name='login_page'),
    path('register-page/', views.register_page, name='register_page'),
    
    # ============================================================
    # API ENDPOINTS (POST/GET)
    # ============================================================
    # Registro e Login (com backend)
    path('register/', views.supabase_register, name='register'),
    path('login/', views.supabase_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # OAuth Callback
    path('callback/google/', views.google_oauth_callback, name='google_callback'),
    
    # ============================================================
    # API SEGURA (Sem chaves expostas)
    # ============================================================
    path('api/auth-config/', api.auth_config, name='auth_config'),
    path('api/validate-token/', api.validate_token, name='validate_token'),
    path('api/callback-proxy/', api.auth_callback_proxy, name='callback_proxy'),
    path('api/current-user/', api.current_user, name='current_user'),
]
