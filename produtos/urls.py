from django.urls import path
from . import views
from . import views_tipo_produto

app_name = 'produtos'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Tipo de Produto
    path('tipos-produto/', views_tipo_produto.tipo_produto_list, name='tipo_produto_list'),
    path('tipos-produto/cadastrar/', views_tipo_produto.tipo_produto_create, name='tipo_produto_create'),
    path('tipos-produto/<int:pk>/editar/', views_tipo_produto.tipo_produto_update, name='tipo_produto_update'),
    path('tipos-produto/<int:pk>/excluir/', views_tipo_produto.tipo_produto_delete, name='tipo_produto_delete'),
    path('tipos-produto/ajax/listar/', views_tipo_produto.tipo_produto_listar_ajax, name='tipo_produto_listar_ajax'),
    
    # Unidade de Medida
    path('unidades/', views.unidademedida_list, name='unidademedida_list'),
    path('unidades/cadastrar/', views.unidademedida_create, name='unidademedida_create'),
    path('unidades/<int:pk>/editar/', views.unidademedida_update, name='unidademedida_update'),
    path('unidades/<int:pk>/excluir/', views.unidademedida_delete, name='unidademedida_delete'),
    path('unidades/ajax/criar/', views.unidademedida_create_ajax, name='unidademedida_create_ajax'),
    
    # NCM
    path('ncm/buscar/', views.ncm_buscar_ajax, name='ncm_buscar_ajax'),
    
    # CFOP
    path('cfop/buscar/', views.cfop_buscar_ajax, name='cfop_buscar_ajax'),
    
    # Natureza da Operação
    path('naturezas/', views.naturezaoperacao_list, name='naturezaoperacao_list'),
    path('naturezas/cadastrar/', views.naturezaoperacao_create, name='naturezaoperacao_create'),
    path('naturezas/<int:pk>/editar/', views.naturezaoperacao_update, name='naturezaoperacao_update'),
    path('naturezas/<int:pk>/excluir/', views.naturezaoperacao_delete, name='naturezaoperacao_delete'),
    
    # Categoria
    path('categorias/', views.categoria_list, name='categoria_list'),
    path('categorias/popular/', views.categoria_seed, name='categoria_seed'),
    path('categorias/cadastrar/', views.categoria_create, name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.categoria_update, name='categoria_update'),
    path('categorias/<int:pk>/excluir/', views.categoria_delete, name='categoria_delete'),
    path('categorias/ajax/criar/', views.categoria_create_ajax, name='categoria_create_ajax'),
    
    # Subcategoria
    path('subcategorias/', views.subcategoria_list, name='subcategoria_list'),
    path('subcategorias/cadastrar/', views.subcategoria_create, name='subcategoria_create'),
    path('subcategorias/<int:pk>/editar/', views.subcategoria_update, name='subcategoria_update'),
    path('subcategorias/<int:pk>/excluir/', views.subcategoria_delete, name='subcategoria_delete'),
    path('subcategorias/ajax/criar/', views.subcategoria_create_ajax, name='subcategoria_create_ajax'),
    
    # Produto
    path('', views.produto_list, name='produto_list'),
    path('<int:pk>/', views.produto_detail, name='produto_detail'),
    path('cadastrar/', views.produto_create, name='produto_create'),
    path('<int:pk>/editar/', views.produto_update, name='produto_update'),
    path('<int:pk>/excluir/', views.produto_delete, name='produto_delete'),
    path('<int:pk>/clonar/', views.produto_clone, name='produto_clone'),
    
    # Tributação
    path('<int:produto_id>/tributacao/cadastrar/', views.produtotributacao_create, name='tributacao_create'),
    path('tributacao/<int:pk>/editar/', views.produtotributacao_update, name='tributacao_update'),
    path('tributacao/<int:pk>/excluir/', views.produtotributacao_delete, name='tributacao_delete'),
    path('ajax/buscar/', views.ajax_buscar_produtos, name='ajax_buscar_produtos'),
    path('ajax/<int:produto_id>/tributacoes/', views.ajax_produto_tributacoes, name='ajax_produto_tributacoes'),
    
    # Defensivo Cultura
    path('<int:produto_pk>/defensivo-cultura/cadastrar/', views.defensivo_cultura_create, name='defensivo_cultura_create'),
    path('defensivo-cultura/<int:pk>/edit/', views.defensivo_cultura_edit, name='defensivo_cultura_edit'),
    path('defensivo-cultura/<int:pk>/delete/', views.defensivo_cultura_delete, name='defensivo_cultura_delete'),
    
    # AJAX - Cadastro rápido de cultura
    path('culturas/ajax/criar/', views.cultura_create_ajax, name='cultura_create_ajax'),
    
    # Fornecedores do Produto
    path('fornecedores/listar/', views.fornecedores_listar, name='fornecedores_listar'),
    path('<int:produto_pk>/fornecedor/criar/', views.produto_fornecedor_create, name='produto_fornecedor_create'),
    path('fornecedor/<int:pk>/excluir/', views.produto_fornecedor_delete, name='produto_fornecedor_delete'),
    path('fornecedor/<int:pk>/json/', views.produto_fornecedor_json, name='produto_fornecedor_json'),
    path('fornecedor/<int:pk>/editar/', views.produto_fornecedor_editar, name='produto_fornecedor_editar'),
    
    # Documentos do Produto
    path('<int:produto_pk>/documentos/upload/', views.documento_upload, name='documento_upload'),
    path('documentos/<int:pk>/delete/', views.documento_delete, name='documento_delete'),
]
