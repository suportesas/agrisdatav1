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
    path('relatorio/pdf/', views.patrimonio_relatorio_pdf, name='patrimonio_relatorio_pdf'),
    path('relatorio/excel/', views.patrimonio_relatorio_excel, name='patrimonio_relatorio_excel'),

    # Auditorias
    path('auditorias/', views.patrimonio_auditoria_list, name='auditoria_list'),
    path('auditorias/nova/', views.patrimonio_auditoria_create, name='auditoria_create'),
    path('auditorias/<int:pk>/', views.patrimonio_auditoria_detail, name='auditoria_detail'),
    path('auditorias/<int:pk>/finalizar/', views.patrimonio_auditoria_finalizar, name='auditoria_finalizar'),
    path('auditorias/<int:pk>/pdf/', views.patrimonio_auditoria_pdf, name='auditoria_pdf'),
    path('auditorias/<int:pk>/item/<int:item_pk>/', views.patrimonio_auditoria_item_update, name='auditoria_item_update'),
]
