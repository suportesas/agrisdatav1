"""
URLs do módulo Fazendas/Cadastros
"""

from django.urls import path
from . import views

app_name = 'cadastros'

urlpatterns = [
    # ==================== FAZENDAS ====================
    path('fazendas/', views.fazenda_list, name='fazenda_list'),
    path('fazendas/nova/', views.fazenda_create, name='fazenda_create'),
    path('fazendas/<int:pk>/', views.fazenda_detail, name='fazenda_detail'),
    path('fazendas/<int:pk>/editar/', views.fazenda_update, name='fazenda_update'),
    path('fazendas/<int:pk>/excluir/', views.fazenda_delete, name='fazenda_delete'),
    
    # ==================== APIs EXTERNAS ====================
    path('api/buscar-cnpj/', views.buscar_cnpj, name='buscar_cnpj'),
    path('api/buscar-cep/', views.buscar_cep, name='buscar_cep'),
    
    # ==================== ENDEREÇOS ====================
    path('fazendas/<int:fazenda_pk>/enderecos/novo/', views.endereco_create, name='endereco_create'),
    path('fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/editar/', views.endereco_update, name='endereco_update'),
    path('fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/excluir/', views.endereco_delete, name='endereco_delete'),
    
    # ==================== CONTATOS ====================
    path('fazendas/<int:fazenda_pk>/contatos/novo/', views.contato_create, name='contato_create'),
    path('fazendas/<int:fazenda_pk>/contatos/<int:contato_pk>/editar/', views.contato_update, name='contato_update'),
    path('fazendas/<int:fazenda_pk>/contatos/<int:contato_pk>/excluir/', views.contato_delete, name='contato_delete'),
    
    # ==================== CONTAS BANCÁRIAS ====================
    path('fazendas/<int:fazenda_pk>/contas/nova/', views.conta_bancaria_create, name='conta_bancaria_create'),
    path('fazendas/<int:fazenda_pk>/contas/<int:conta_pk>/editar/', views.conta_bancaria_update, name='conta_bancaria_update'),
    path('fazendas/<int:fazenda_pk>/contas/<int:conta_pk>/excluir/', views.conta_bancaria_delete, name='conta_bancaria_delete'),
    
    # ==================== DOCUMENTOS ====================
    path('fazendas/<int:fazenda_pk>/documentos/novo/', views.documento_create, name='documento_create'),
    path('fazendas/<int:fazenda_pk>/documentos/<int:documento_pk>/excluir/', views.documento_delete, name='documento_delete'),
    path('fazendas/<int:fazenda_pk>/documentos/<int:documento_pk>/editar/', views.documento_update, name='documento_update'),
    
    # ==================== ALERTAS ====================
    path('alertas/', views.dashboard_alertas, name='dashboard_alertas'),
    
    # ==================== FUNÇÕES ====================
    path('funcoes/', views.funcao_list, name='funcao_list'),
    path('funcoes/criar-ajax/', views.funcao_create_ajax, name='funcao_create_ajax'),
    
    # ==================== FUNCIONÁRIOS ====================
    path('funcionarios/', views.funcionario_list, name='funcionario_list'),
    path('funcionarios/novo/', views.funcionario_create, name='funcionario_create'),
    path('funcionarios/<int:pk>/', views.funcionario_detail, name='funcionario_detail'),
    path('funcionarios/<int:pk>/editar/', views.funcionario_update, name='funcionario_update'),
    path('funcionarios/<int:pk>/excluir/', views.funcionario_delete, name='funcionario_delete'),
    

    # ==================== CULTURAS ====================
    path('culturas/', views.cultura_list, name='cultura_list'),
    path('culturas/nova/', views.cultura_create, name='cultura_create'),
    path('culturas/<int:pk>/', views.cultura_detail, name='cultura_detail'),
    path('culturas/<int:pk>/editar/', views.cultura_update, name='cultura_update'),
    path('culturas/<int:pk>/excluir/', views.cultura_delete, name='cultura_delete'),

    
    # ====================  Áreas ====================== 
    path('areas/', views.area_list, name='area_list'),
    path('areas/nova/', views.area_create, name='area_create'),
    path('areas/<int:pk>/', views.area_detail, name='area_detail'),
    path('areas/<int:pk>/editar/', views.area_update, name='area_update'),
    path('areas/<int:pk>/excluir/', views.area_delete, name='area_delete'),
    
    # Talhões
    path('talhoes/', views.talhao_list, name='talhao_list'),
    path('talhoes/novo/', views.talhao_create, name='talhao_create'),
    path('talhoes/<int:pk>/', views.talhao_detail, name='talhao_detail'),
    path('talhoes/<int:pk>/editar/', views.talhao_update, name='talhao_update'),
    path('talhoes/<int:pk>/excluir/', views.talhao_delete, name='talhao_delete'),
    # Histórico de cultivo
    path('talhoes/<int:talhao_pk>/historico/nova/', views.historico_create, name='historico_create'),
    path('historico/<int:pk>/editar/', views.historico_update, name='historico_update'),
    path('historico/<int:pk>/excluir/', views.historico_delete, name='historico_delete'),
    path('historico/<int:pk>/', views.historico_detail, name='historico_detail'),
    
    # Safras
    path('safras/', views.safra_list, name='safra_list'),
    path('safras/nova/', views.safra_create, name='safra_create'),
    path('safras/<int:pk>/', views.safra_detail, name='safra_detail'),
    path('safras/<int:pk>/editar/', views.safra_update, name='safra_update'),
    path('safras/<int:pk>/excluir/', views.safra_delete, name='safra_delete'),
    
    # AJAX
    path('ajax/areas-por-fazenda/<int:fazenda_id>/', views.ajax_areas_por_fazenda, name='ajax_areas_fazenda'),
    path('ajax/talhoes-por-fazenda/<int:fazenda_id>/', views.ajax_talhoes_por_fazenda, name='ajax_talhoes_fazenda'),

    # Vendedores    
    path('vendedores/', views.vendedor_list, name='vendedor_list'),
    path('vendedores/novo/', views.vendedor_create, name='vendedor_create'),
    path('vendedores/<int:pk>/', views.vendedor_detail, name='vendedor_detail'),
    path('vendedores/<int:pk>/editar/', views.vendedor_update, name='vendedor_update'),
    path('vendedores/<int:pk>/excluir/', views.vendedor_delete, name='vendedor_delete'),
    path('vendedores/<int:pk>/inativar/', views.vendedor_inativar, name='vendedor_inativar'),
    path('vendedores/<int:pk>/reativar/', views.vendedor_reativar, name='vendedor_reativar'),
    
    # Comissões
    path('comissoes/', views.comissao_list, name='comissao_list'),
    path('comissoes/nova/', views.comissao_create, name='comissao_create'),
    path('comissoes/<int:pk>/pagar/', views.comissao_pagar, name='comissao_pagar'),
    
    # APIs
    path('vendedores/api/json/', views.vendedor_json, name='vendedor_json'),
    path('api/vendedores-por-tipo/', views.vendedores_por_tipo, name='vendedores_por_tipo'),


   
    # Fornecedores
    path('fornecedores/', views.fornecedor_list, name='fornecedor_list'),
    path('fornecedores/novo/', views.fornecedor_create, name='fornecedor_create'),
    path('fornecedores/<int:pk>/', views.fornecedor_detail, name='fornecedor_detail'),
    path('fornecedores/<int:pk>/editar/', views.fornecedor_update, name='fornecedor_update'),
    path('fornecedores/<int:pk>/excluir/', views.fornecedor_delete, name='fornecedor_delete'),

    # Fornecedor: endereços
    path('fornecedores/<int:fornecedor_pk>/enderecos/novo/', views.fornecedor_endereco_create, name='fornecedor_endereco_create'),
    path('fornecedores/<int:fornecedor_pk>/enderecos/<int:endereco_pk>/editar/', views.fornecedor_endereco_update, name='fornecedor_endereco_update'),
    path('fornecedores/<int:fornecedor_pk>/enderecos/<int:endereco_pk>/excluir/', views.fornecedor_endereco_delete, name='fornecedor_endereco_delete'),

    # Fornecedor: contatos
    path('fornecedores/<int:fornecedor_pk>/contatos/novo/', views.fornecedor_contato_create, name='fornecedor_contato_create'),
    path('fornecedores/<int:fornecedor_pk>/contatos/<int:contato_pk>/editar/', views.fornecedor_contato_update, name='fornecedor_contato_update'),
    path('fornecedores/<int:fornecedor_pk>/contatos/<int:contato_pk>/excluir/', views.fornecedor_contato_delete, name='fornecedor_contato_delete'),

    # Fornecedor: contas bancárias
    path('fornecedores/<int:fornecedor_pk>/contas/nova/', views.fornecedor_conta_create, name='fornecedor_conta_create'),
    path('fornecedores/<int:fornecedor_pk>/contas/<int:conta_pk>/editar/', views.fornecedor_conta_update, name='fornecedor_conta_update'),
    path('fornecedores/<int:fornecedor_pk>/contas/<int:conta_pk>/excluir/', views.fornecedor_conta_delete, name='fornecedor_conta_delete'),

    # Fornecedor: documentos
    path('fornecedores/<int:fornecedor_pk>/documentos/novo/', views.fornecedor_documento_create, name='fornecedor_documento_create'),
    path('fornecedores/<int:fornecedor_pk>/documentos/<int:documento_pk>/excluir/', views.fornecedor_documento_delete, name='fornecedor_documento_delete'),
    path('fornecedores/<int:fornecedor_pk>/documentos/<int:documento_pk>/editar/', views.fornecedor_documento_update, name='fornecedor_documento_update'),

    # Clientes
    path('clientes/', views.cliente_list, name='cliente_list'),
    path('clientes/novo/', views.cliente_create, name='cliente_create'),
    path('clientes/<int:pk>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:pk>/editar/', views.cliente_update, name='cliente_update'),
    path('clientes/<int:pk>/excluir/', views.cliente_delete, name='cliente_delete'),
    path('clientes/<int:pk>/reativar/', views.cliente_activate, name='cliente_activate'),

    # Cliente: endereços
    path('clientes/<int:cliente_pk>/enderecos/novo/', views.cliente_endereco_create, name='cliente_endereco_create'),
    path('clientes/<int:cliente_pk>/enderecos/<int:endereco_pk>/editar/', views.cliente_endereco_update, name='cliente_endereco_update'),
    path('clientes/<int:cliente_pk>/enderecos/<int:endereco_pk>/excluir/', views.cliente_endereco_delete, name='cliente_endereco_delete'),

    # Cliente: contatos
    path('clientes/<int:cliente_pk>/contatos/novo/', views.cliente_contato_create, name='cliente_contato_create'),
    path('clientes/<int:cliente_pk>/contatos/ajax/novo/', views.cliente_contato_create_ajax, name='cliente_contato_create_ajax'),
    path('clientes/<int:cliente_pk>/contatos/<int:contato_pk>/editar/', views.cliente_contato_update, name='cliente_contato_update'),
    path('clientes/<int:cliente_pk>/contatos/<int:contato_pk>/excluir/', views.cliente_contato_delete, name='cliente_contato_delete'),

    # Cliente: contas bancárias
    path('clientes/<int:cliente_pk>/contas/nova/', views.cliente_conta_create, name='cliente_conta_create'),
    path('clientes/<int:cliente_pk>/contas/ajax/nova/', views.cliente_conta_create_ajax, name='cliente_conta_create_ajax'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/editar/', views.cliente_conta_update, name='cliente_conta_update'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/excluir/', views.cliente_conta_delete, name='cliente_conta_delete'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/editar/ajax/', views.cliente_conta_update_ajax, name='cliente_conta_update_ajax'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/excluir/ajax/', views.cliente_conta_delete_ajax, name='cliente_conta_delete_ajax'),

    # Cliente: documentos
    path('clientes/<int:cliente_pk>/documentos/novo/', views.cliente_documento_create, name='cliente_documento_create'),
    path('clientes/<int:cliente_pk>/documentos/ajax/novo/', views.cliente_documento_create_ajax, name='cliente_documento_create_ajax'),
    path('clientes/<int:cliente_pk>/documentos/<int:documento_pk>/excluir/', views.cliente_documento_delete, name='cliente_documento_delete'),
    path('clientes/<int:cliente_pk>/documentos/<int:documento_pk>/editar/', views.cliente_documento_update, name='cliente_documento_update'),

    # ==================== PORTOS ====================
    path('portos/', views.porto_list, name='porto_list'),
    path('portos/novo/', views.porto_create, name='porto_create'),
    path('portos/<int:pk>/', views.porto_detail, name='porto_detail'),
    path('portos/<int:pk>/editar/', views.porto_update, name='porto_update'),
    path('portos/<int:pk>/excluir/', views.porto_delete, name='porto_delete'),

]
