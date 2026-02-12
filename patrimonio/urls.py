"""
URLs do módulo Patrimônio
"""

from django.urls import path
from . import views

app_name = 'patrimonio'

urlpatterns = [
    # Patrimônio
    path('', views.patrimonio_list, name='patrimonio_list'),
    path('novo/', views.patrimonio_create, name='patrimonio_create'),
    path('<int:pk>/', views.patrimonio_detail, name='patrimonio_detail'),
    path('<int:pk>/editar/', views.patrimonio_edit, name='patrimonio_edit'),
    path('<int:pk>/excluir/', views.patrimonio_delete, name='patrimonio_delete'),
    
    # Exportar veículo como patrimônio
    path('veiculo/<int:vehicle_pk>/exportar/', views.patrimonio_from_veiculo, name='patrimonio_from_veiculo'),
    
    # Movimentações
    path('<int:pk>/movimentacao/nova/', views.patrimonio_movimentacao_add, name='patrimonio_movimentacao_add'),
    
    # Relatórios
    path('relatorio/', views.patrimonio_relatorio, name='patrimonio_relatorio'),
]
