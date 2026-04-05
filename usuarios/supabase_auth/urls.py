"""
URLs para autenticação Supabase
"""

from django.urls import path
from . import views

app_name = 'supabase_auth'

urlpatterns = [
    # Página de login (GET)
    path('login-page/', views.login_page, name='login_page'),
    # Página de registro (GET)
    path('register-page/', views.register_page, name='register_page'),
    # API endpoints (POST)
    path('register/', views.supabase_register, name='register'),
    path('login/', views.supabase_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('callback/google/', views.google_oauth_callback, name='google_callback'),
]
