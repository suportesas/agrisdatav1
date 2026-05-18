"""
URLs para o módulo financeiro
"""
from django.urls import path
from . import views

app_name = 'financeiro'

urlpatterns = [
    # DASHBOARD
    path('', views.financeiro_dashboard, name='dashboard'),
    
    # CONTAS A PAGAR
    path('contas/', views.conta_pagar_list, name='conta_pagar_list'),
    path('contas/<int:pk>/', views.conta_pagar_detail, name='conta_pagar_detail'),
    path('contas/criar/', views.conta_pagar_create, name='conta_pagar_create'),
    path('contas/<int:pk>/editar/', views.conta_pagar_edit, name='conta_pagar_edit'),
    path('contas/<int:pk>/aprovar/', views.conta_pagar_aprovar, name='conta_pagar_aprovar'),
    
    # PARCELAS
    path('parcelas/', views.parcela_list, name='parcela_list'),
    path('contas/<int:conta_pk>/parcelas/criar/', views.parcela_criar, name='parcela_criar'),
    
    # PAGAMENTOS
    path('parcelas/<int:parcela_pk>/pagar/', views.parcela_pagar, name='parcela_pagar'),
    
    # RELATÓRIOS
    path('relatorios/contas-a-vencer/', views.relatorio_contas_vencer, name='relatorio_contas_vencer'),
    path('relatorios/contas-vencidas/', views.relatorio_contas_vencidas, name='relatorio_contas_vencidas'),
    path('relatorios/fluxo-caixa/', views.relatorio_fluxo_caixa, name='relatorio_fluxo_caixa'),
    
    # API AUXILIARES
    path('contas/<int:conta_pk>/recalcular-juros/', views.recalcular_juros_multas, name='recalcular_juros'),

    # CONTAS A RECEBER
    path('contas-receber/', views.conta_receber_list, name='conta_receber_list'),
    path('contas-receber/nova/', views.conta_receber_create, name='conta_receber_create'),
    path('contas-receber/<int:pk>/', views.conta_receber_detail, name='conta_receber_detail'),
    path('contas-receber/<int:pk>/cancelar/', views.conta_receber_cancelar, name='conta_receber_cancelar'),
    path('contas-receber/parcela/<int:parcela_pk>/receber/', views.parcela_receber_registrar, name='parcela_receber_registrar'),
]
