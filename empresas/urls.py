from django.urls import path
from . import views
from . import views_grupo
from . import views_programa

app_name = 'empresas'

urlpatterns = [
    # Empresas
    path('', views.empresa_list, name='empresa_list'),
    path('nova/', views.empresa_create, name='empresa_create'),
    path('<int:pk>/editar/', views.empresa_update, name='empresa_update'),
    path('minha-empresa/logo/', views.empresa_logo_update, name='empresa_logo_update'),
    path('<int:pk>/excluir/', views.empresa_delete, name='empresa_delete'),
    path('minha/', views.minha_empresa, name='minha_empresa'),
    path('preferencias/', views.empresa_preferencias, name='empresa_preferencias'),
    path('painel-admin/', views.painel_admin, name='painel_admin'),

    # Roles / Permissões
    path('roles/', views.role_list, name='roles_list'),
    path('roles/<int:role_id>/permissions/', views.role_permissions, name='role_permissions'),
    path('roles/novo/', views.role_create, name='role_create'),
    path('roles/<int:role_id>/editar/', views.role_update, name='role_update'),
    path('roles/<int:role_id>/clonar/', views.role_clone, name='role_clone'),
    path('roles/<int:role_id>/personalizar/', views.role_fork, name='role_fork'),
    path('roles/<int:role_id>/permissions/save-template/', views.save_permission_template, name='save_permission_template'),
    path('roles/<int:role_id>/permissions/apply-template/', views.apply_template_to_role, name='apply_template_to_role'),
    path('roles/templates/apply-bulk/', views.apply_template_bulk, name='apply_template_bulk'),
    path('roles/templates/', views.permission_templates_list, name='permission_templates_list'),
    path('roles/templates/<int:pk>/', views.permission_template_detail, name='permission_template_detail'),

    # Programas (telas do sistema) — estilo MadBuilder
    path('programas/', views_programa.programa_list, name='programa_list'),
    path('programas/<int:pk>/', views_programa.programa_detail, name='programa_detail'),
    path('programas/<int:pk>/editar/', views_programa.programa_update, name='programa_update'),
    path('programas/<int:pk>/grupos/', views_programa.programa_set_roles, name='programa_set_roles'),
    path('programas/<int:pk>/acoes/nova/', views_programa.programa_acao_create, name='programa_acao_create'),

    # Configuração da Plataforma (Softhouse IntegraNotas)
    path('configuracao/softhouse/', views.configuracao_softhouse, name='configuracao_softhouse'),
    path('<int:pk>/integranotas/', views.empresa_emitente_softhouse, name='empresa_emitente_softhouse'),
    path('<int:pk>/integranotas/testar-conexao/', views.empresa_testar_conexao_integranotas, name='empresa_testar_conexao_integranotas'),

    # Planos
    path('planos/', views.plano_list, name='plano_list'),
    path('planos/novo/', views.plano_create, name='plano_create'),
    path('planos/<int:pk>/editar/', views.plano_update, name='plano_update'),
    path('planos/<int:pk>/excluir/', views.plano_delete, name='plano_delete'),
    path('planos/inicializar/', views.inicializar_planos_padrao, name='inicializar_planos'),
    path('api/plano/<int:plano_id>/', views.api_plano_dados, name='api_plano_dados'),

    # Grupos Corporativos (Enterprise Plus)
    path('grupos/', views_grupo.grupo_list, name='grupo_list'),
    path('grupos/novo/', views_grupo.grupo_create, name='grupo_create'),
    path('grupos/<int:pk>/', views_grupo.grupo_detail, name='grupo_detail'),
    path('grupos/<int:pk>/editar/', views_grupo.grupo_update, name='grupo_update'),
    path('grupos/<int:pk>/deletar/', views_grupo.grupo_delete, name='grupo_delete'),
    path('grupos/<int:pk>/adicionar-empresas/', views_grupo.grupo_adicionar_empresas, name='grupo_adicionar_empresas'),
    path('grupos/<int:grupo_id>/empresas/<int:empresa_id>/remover/', views_grupo.remover_empresa_do_grupo, name='remover_empresa_do_grupo'),
    path('grupos/<int:pk>/relatorio/', views_grupo.grupo_relatorio_consolidado, name='grupo_relatorio_consolidado'),
    path('grupos/ajuda/', views_grupo.ajuda_grupos_corporativos, name='ajuda_grupos_corporativos'),
    path('ajuda/usuarios-grupos/', views_grupo.ajuda_usuarios_grupos, name='ajuda_usuarios_grupos'),

    # Chaves de API
    path('api-keys/', views.api_key_list, name='api_key_list'),
    path('api-keys/nova/', views.api_key_create, name='api_key_create'),
    path('api-keys/<int:pk>/revogar/', views.api_key_revoke, name='api_key_revoke'),
]