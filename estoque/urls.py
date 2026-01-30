"""
URLs do módulo Estoque
"""
from django.urls import path
from . import views

app_name = 'estoque'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Armazéns
    path('armazens/', views.armazem_list, name='armazem_list'),
    path('armazens/create/', views.armazem_create, name='armazem_create'),
    path('armazens/<int:pk>/', views.armazem_detail, name='armazem_detail'),
    path('armazens/<int:pk>/edit/', views.armazem_edit, name='armazem_edit'),
    path('armazens/<int:pk>/delete/', views.armazem_delete, name='armazem_delete'),
    
    # Locais de Estocagem
    path('locais/', views.local_list, name='local_list'),
    path('locais/create/', views.local_create, name='local_create'),
    path('locais/<int:pk>/edit/', views.local_edit, name='local_edit'),
    path('locais/<int:pk>/delete/', views.local_delete, name='local_delete'),
    path('locais/<int:pk>/bloquear/', views.local_bloquear, name='local_bloquear'),
    path('locais/<int:pk>/desbloquear/', views.local_desbloquear, name='local_desbloquear'),
    
    # Lotes
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/create/', views.lote_create, name='lote_create'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote_detail'),
    path('lotes/<int:pk>/edit/', views.lote_edit, name='lote_edit'),
    path('lotes/<int:pk>/bloquear/', views.lote_bloquear, name='lote_bloquear'),
    path('lotes/<int:pk>/desbloquear/', views.lote_desbloquear, name='lote_desbloquear'),
    
    # Movimentações de Estoque (FASE 2)
    path('movimentacoes/', views.movimentacao_list, name='movimentacao_list'),
    path('movimentacoes/create/', views.movimentacao_create, name='movimentacao_create'),
    path('movimentacoes/<int:pk>/', views.movimentacao_detail, name='movimentacao_detail'),
    path('movimentacoes/<int:pk>/aprovar/', views.movimentacao_aprovar, name='movimentacao_aprovar'),
    path('movimentacoes/<int:pk>/executar/', views.movimentacao_executar, name='movimentacao_executar'),
    path('movimentacoes/<int:pk>/cancelar/', views.movimentacao_cancelar, name='movimentacao_cancelar'),
    
    # Tipos específicos de movimentação
    path('entrada/', views.entrada_create, name='entrada_create'),
    path('saida/', views.saida_create, name='saida_create'),
    path('transferencia/', views.transferencia_create, name='transferencia_create'),
    
    # Relatórios
    path('relatorio/', views.relatorio_estoque, name='relatorio_estoque'),
    path('relatorio/produto/', views.relatorio_produto, name='relatorio_produto'),
    
    # API
    path('api/lotes-disponiveis/', views.get_lotes_disponiveis, name='api_lotes_disponiveis'),
    
    # Produtos em Estoque
    path('produtos/', views.estoque_produtos_list, name='estoque_produtos_list'),
    path('produto/<int:pk>/historico/', views.produto_historico, name='produto_historico'),
    path('produto/<int:pk>/historico/pdf/', views.produto_historico_pdf, name='produto_historico_pdf'),
]
