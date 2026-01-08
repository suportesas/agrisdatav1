from django.urls import path
from . import views

app_name = 'empresas'

urlpatterns = [
    # Empresas
    path('', views.empresa_list, name='empresa_list'),
    path('nova/', views.empresa_create, name='empresa_create'),
    path('<int:pk>/editar/', views.empresa_update, name='empresa_update'),
    path('<int:pk>/excluir/', views.empresa_delete, name='empresa_delete'),
    path('minha/', views.minha_empresa, name='minha_empresa'),
    path('painel-admin/', views.painel_admin, name='painel_admin'),

    # Roles / Permissões
    path('roles/', views.role_list, name='roles_list'),
    path('roles/<int:role_id>/permissions/', views.role_permissions, name='role_permissions'),
    path('roles/novo/', views.role_create, name='role_create'),
    
    # Planos
    path('planos/', views.plano_list, name='plano_list'),
    path('planos/novo/', views.plano_create, name='plano_create'),
    path('planos/<int:pk>/editar/', views.plano_update, name='plano_update'),
    path('planos/<int:pk>/excluir/', views.plano_delete, name='plano_delete'),
    path('planos/inicializar/', views.inicializar_planos_padrao, name='inicializar_planos'),
]