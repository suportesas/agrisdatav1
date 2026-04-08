from django.urls import path
from . import views
from . import views_2fa

app_name = 'usuarios'

urlpatterns = [
    # CRUD de Usuários
    path('', views.usuario_list, name='usuario_list'),
    path('novo/', views.usuario_create, name='usuario_create'),
    path('<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('<int:pk>/excluir/', views.usuario_delete, name='usuario_delete'),
    path('tipos/', views.tipo_usuario_list, name='tipo_usuario_list'),
    path('tipos/novo/', views.tipo_usuario_create, name='tipo_usuario_create'),
    path('tipos/quick-create/', views.tipo_usuario_quick_create, name='tipo_usuario_quick_create'),
    path('tipos/<int:pk>/editar/', views.tipo_usuario_update, name='tipo_usuario_update'),
    path('tipos/<int:pk>/excluir/', views.tipo_usuario_delete, name='tipo_usuario_delete'),
    path('<int:pk>/senha-emergencial/', views.usuario_troca_senha_emergencial, name='usuario_troca_senha_emergencial'),
    path('senha-emergencial/cancelar/<str:token>/', views.cancelar_troca_senha_emergencial, name='cancelar_troca_senha_emergencial'),
    
    # Perfil do Usuário Logado
    path('meu-perfil/', views.meu_perfil, name='meu_perfil'),  # ← DESCOMENTAR
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),  # ← DESCOMENTAR
    
    # Logs de Acesso (Auditoria)
    path('registros/', views.login_registros, name='login_registros'),
    
    # Autenticação Dois Fatores (2FA)
    path('2fa/configurar/', views_2fa.configurar_2fa, name='configurar_2fa'),
    path('2fa/verificacao/', views_2fa.verificacao_2fa_login, name='verificacao_2fa_login'),
    path('2fa/codigos-backup/', views_2fa.listar_codigos_backup, name='listar_codigos_backup'),
    path('2fa/desabilitar/', views_2fa.desabilitar_2fa, name='desabilitar_2fa'),
    path('2fa/info-seguranca/', views_2fa.info_seguranca, name='info_seguranca'),
    
    # API Endpoints
    path('api/verificar-2fa/', views_2fa.api_verificar_2fa_necessario, name='api_verificar_2fa'),
]