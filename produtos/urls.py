from django.urls import path
from . import views

app_name = 'produtos'

urlpatterns = [
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
    
    # Tributação
    path('<int:produto_id>/tributacao/cadastrar/', views.produtotributacao_create, name='tributacao_create'),
    path('tributacao/<int:pk>/editar/', views.produtotributacao_update, name='tributacao_update'),
    path('tributacao/<int:pk>/excluir/', views.produtotributacao_delete, name='tributacao_delete'),
    
    # Defensivo Cultura
    path('<int:produto_pk>/defensivo-cultura/cadastrar/', views.defensivo_cultura_create, name='defensivo_cultura_create'),
    path('defensivo-cultura/<int:pk>/edit/', views.defensivo_cultura_edit, name='defensivo_cultura_edit'),
    path('defensivo-cultura/<int:pk>/delete/', views.defensivo_cultura_delete, name='defensivo_cultura_delete'),
    
    # AJAX - Cadastro rápido de cultura
    path('culturas/ajax/criar/', views.cultura_create_ajax, name='cultura_create_ajax'),
    
    # Documentos do Produto
    path('<int:produto_pk>/documentos/upload/', views.documento_upload, name='documento_upload'),
    path('documentos/<int:pk>/delete/', views.documento_delete, name='documento_delete'),
]
