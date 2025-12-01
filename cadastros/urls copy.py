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
]