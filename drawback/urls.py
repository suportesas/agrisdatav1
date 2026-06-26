from django.urls import path
from . import views

app_name = 'drawback'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('ajuda/', views.ajuda, name='ajuda'),

    # Ato Concessório
    path('ac/novo/', views.ac_create, name='ac_create'),
    path('ac/<int:pk>/', views.ac_detail, name='ac_detail'),
    path('ac/<int:pk>/editar/', views.ac_edit, name='ac_edit'),

    # Entradas manuais
    path('ac/<int:ac_pk>/entrada/nova/', views.entrada_create, name='entrada_create'),
    path('entrada/<int:pk>/anular/', views.entrada_anular, name='entrada_anular'),

    # Saídas manuais
    path('ac/<int:ac_pk>/saida/nova/', views.saida_create, name='saida_create'),
    path('saida/<int:pk>/anular/', views.saida_anular, name='saida_anular'),

    # Importação XLSX
    path('ac/<int:ac_pk>/importar/', views.importar_xlsx, name='importar_xlsx'),
    path('ac/<int:ac_pk>/importar/confirmar/', views.importar_confirmar, name='importar_confirmar'),
    path('ac/<int:ac_pk>/modelo/<str:tipo>/', views.download_modelo_xlsx, name='download_modelo_xlsx'),

    # Relatório
    path('ac/<int:ac_pk>/relatorio/', views.relatorio, name='relatorio'),
    path('ac/<int:ac_pk>/relatorio/xlsx/', views.relatorio_xlsx, name='relatorio_xlsx'),

    # Vínculo via ERP (ajax)
    path('vincular/entrada/<int:item_recebimento_id>/', views.vincular_entrada_erp, name='vincular_entrada_erp'),
    path('vincular/saida/<int:item_nfe_id>/', views.vincular_saida_erp, name='vincular_saida_erp'),

    # AJAX — saldo por produto e info do produto
    path('ajax/saldo/<int:produto_ac_id>/', views.ajax_saldo_produto, name='ajax_saldo_produto'),
    path('ajax/produto/<int:produto_id>/', views.ajax_produto_info, name='ajax_produto_info'),
]
