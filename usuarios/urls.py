from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    # CRUD de Usuários
    path('', views.usuario_list, name='usuario_list'),
    path('novo/', views.usuario_create, name='usuario_create'),
    path('<int:pk>/editar/', views.usuario_update, name='usuario_update'),
    path('<int:pk>/excluir/', views.usuario_delete, name='usuario_delete'),
    
    # Perfil do Usuário Logado
    path('meu-perfil/', views.meu_perfil, name='meu_perfil'),  # ← DESCOMENTAR
    path('alterar-senha/', views.alterar_senha, name='alterar_senha'),  # ← DESCOMENTAR
    
    # Logs de Acesso (Auditoria)
    path('registros/', views.login_registros, name='login_registros'),
]