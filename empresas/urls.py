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
    path('roles/<int:role_id>/editar/', views.role_update, name='role_update'),
    path('roles/<int:role_id>/permissions/save-template/', views.save_permission_template, name='save_permission_template'),
    path('roles/<int:role_id>/permissions/apply-template/', views.apply_template_to_role, name='apply_template_to_role'),
    path('roles/templates/apply-bulk/', views.apply_template_bulk, name='apply_template_bulk'),
    path('roles/templates/', views.permission_templates_list, name='permission_templates_list'),
    path('roles/templates/<int:pk>/', views.permission_template_detail, name='permission_template_detail'),
    
    # Planos
    path('planos/', views.plano_list, name='plano_list'),
    path('planos/novo/', views.plano_create, name='plano_create'),
    path('planos/<int:pk>/editar/', views.plano_update, name='plano_update'),
    path('planos/<int:pk>/excluir/', views.plano_delete, name='plano_delete'),
    path('planos/inicializar/', views.inicializar_planos_padrao, name='inicializar_planos'),
]