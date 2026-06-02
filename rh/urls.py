from django.urls import path
from . import views

app_name = 'rh'

urlpatterns = [
    # ==================== FUNÇÕES ====================
    path('funcoes/', views.funcao_list, name='funcao_list'),
    path('funcoes/novo/', views.funcao_create, name='funcao_create'),
    path('funcoes/criar-ajax/', views.funcao_create_ajax, name='funcao_create_ajax'),
    path('funcoes/get-salario/', views.funcao_get_salario, name='funcao_get_salario'),
    path('funcoes/<int:pk>/editar/', views.funcao_update, name='funcao_update'),
    path('funcoes/<int:pk>/excluir/', views.funcao_delete, name='funcao_delete'),

    # ==================== RISCOS AMBIENTAIS (CATÁLOGO) ====================
    path('riscos-ambientais/', views.risco_ambiental_catalogo_list, name='risco_ambiental_catalogo_list'),
    path('riscos-ambientais/novo/', views.risco_ambiental_catalogo_create, name='risco_ambiental_catalogo_create'),
    path('riscos-ambientais/<int:pk>/editar/', views.risco_ambiental_catalogo_update, name='risco_ambiental_catalogo_update'),
    path('riscos-ambientais/<int:pk>/excluir/', views.risco_ambiental_catalogo_delete, name='risco_ambiental_catalogo_delete'),

    # ==================== FUNCIONÁRIOS ====================
    path('funcionarios/', views.funcionario_list, name='funcionario_list'),
    path('funcionarios/novo/', views.funcionario_create, name='funcionario_create'),
    path('funcionarios/<int:pk>/', views.funcionario_detail, name='funcionario_detail'),
    path('funcionarios/<int:pk>/editar/', views.funcionario_update, name='funcionario_update'),
    path('funcionarios/<int:pk>/excluir/', views.funcionario_delete, name='funcionario_delete'),
    path('funcionarios/<int:pk>/pin/', views.funcionario_set_pin, name='funcionario_set_pin'),
    path('funcionarios/<int:funcionario_pk>/documentos/novo/', views.funcionario_documento_create, name='funcionario_documento_create'),

    # ==================== RH - RECURSOS HUMANOS ====================
    path('', views.rh_dashboard, name='rh_dashboard'),

    # Férias
    path('ferias/', views.ferias_list, name='ferias_list'),
    path('ferias/relatorio/previsao-pdf/', views.ferias_previsao_pdf, name='ferias_previsao_pdf'),
    path('ferias/novo/', views.ferias_create, name='ferias_create'),
    path('ferias/<int:pk>/', views.ferias_detail, name='ferias_detail'),
    path('ferias/<int:pk>/editar/', views.ferias_update, name='ferias_update'),
    path('ferias/<int:pk>/excluir/', views.ferias_delete, name='ferias_delete'),

    # Afastamentos
    path('afastamentos/', views.afastamento_list, name='afastamento_list'),
    path('afastamentos/novo/', views.afastamento_create, name='afastamento_create'),
    path('afastamentos/<int:pk>/', views.afastamento_detail, name='afastamento_detail'),
    path('afastamentos/<int:pk>/editar/', views.afastamento_update, name='afastamento_update'),
    path('afastamentos/<int:pk>/excluir/', views.afastamento_delete, name='afastamento_delete'),

    # Vínculos Contratuais
    path('vinculos/', views.vinculo_list, name='vinculo_list'),
    path('vinculos/novo/', views.vinculo_create, name='vinculo_create'),
    path('vinculos/<int:pk>/', views.vinculo_detail, name='vinculo_detail'),
    path('vinculos/<int:pk>/editar/', views.vinculo_update, name='vinculo_update'),

    # Laudos de Risco
    path('laudos/', views.laudo_list, name='laudo_list'),
    path('laudos/novo/', views.laudo_create, name='laudo_create'),
    path('laudos/<int:pk>/', views.laudo_detail, name='laudo_detail'),
    path('laudos/<int:pk>/editar/', views.laudo_update, name='laudo_update'),

    # Tipos de Exame ASO
    path('aso/tipos-exame/', views.tipo_exame_aso_list, name='tipo_exame_aso_list'),
    path('aso/tipos-exame/novo/', views.tipo_exame_aso_create, name='tipo_exame_aso_create'),
    path('aso/tipos-exame/<int:pk>/editar/', views.tipo_exame_aso_update, name='tipo_exame_aso_update'),
    path('aso/tipos-exame/<int:pk>/toggle-ativo/', views.tipo_exame_aso_toggle_ativo, name='tipo_exame_aso_toggle_ativo'),

    # Solicitações de ASO
    path('aso/solicitacoes/', views.aso_solicitacao_list, name='aso_solicitacao_list'),
    path('aso/solicitacoes/nova/', views.aso_solicitacao_create, name='aso_solicitacao_create'),
    path('aso/funcionarios/<int:funcionario_id>/riscos/', views.aso_funcionario_riscos, name='aso_funcionario_riscos'),
    path('aso/buscar-laboratorio/', views.aso_buscar_laboratorio, name='aso_buscar_laboratorio'),
    path('aso/solicitacoes/<int:pk>/', views.aso_solicitacao_detail, name='aso_solicitacao_detail'),
    path('aso/solicitacoes/<int:pk>/editar/', views.aso_solicitacao_update, name='aso_solicitacao_update'),
    path('aso/solicitacoes/<int:pk>/assinar/', views.aso_solicitacao_assinar, name='aso_solicitacao_assinar'),
    path('aso/solicitacoes/<int:pk>/pdf/', views.aso_solicitacao_pdf, name='aso_solicitacao_pdf'),
    path('aso/solicitacoes/<int:pk>/enviar-email/', views.aso_solicitacao_enviar_email, name='aso_solicitacao_enviar_email'),
    path('aso/solicitacoes/<int:pk>/enviar-whatsapp/', views.aso_solicitacao_enviar_whatsapp, name='aso_solicitacao_enviar_whatsapp'),

    # Rescisões
    path('rescisoes/', views.rescisao_list, name='rescisao_list'),
    path('rescisoes/novo/', views.rescisao_create, name='rescisao_create'),
    path('rescisoes/vinculos-por-funcionario/', views.vinculos_por_funcionario, name='vinculos_por_funcionario'),
    path('rescisoes/calcular/', views.rescisao_calcular, name='rescisao_calcular'),
    path('rescisoes/<int:pk>/', views.rescisao_detail, name='rescisao_detail'),
    path('rescisoes/<int:pk>/editar/', views.rescisao_update, name='rescisao_update'),
    path('rescisoes/<int:pk>/excluir/', views.rescisao_delete, name='rescisao_delete'),

    # Relatórios RH
    path('relatorio/', views.relatorio_rh, name='relatorio_rh'),
    path('relatorio/pdf/', views.relatorio_rh_pdf, name='relatorio_rh_pdf'),
]
