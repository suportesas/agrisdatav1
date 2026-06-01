from django.urls import path
from . import views

app_name = 'bancario'

urlpatterns = [
    # ContaBancaria CRUD
    path('contas/', views.conta_bancaria_list, name='conta_bancaria_list'),
    path('contas/nova/', views.conta_bancaria_create, name='conta_bancaria_create'),
    path('contas/<int:pk>/', views.conta_bancaria_detail, name='conta_bancaria_detail'),
    path('contas/<int:pk>/editar/', views.conta_bancaria_edit, name='conta_bancaria_edit'),
    path('contas/<int:pk>/toggle/', views.conta_bancaria_toggle, name='conta_bancaria_toggle'),
    path('contas/<int:pk>/importar/', views.importar_extrato, name='importar_extrato'),

    # Importações
    path('importacoes/<int:pk>/', views.importacao_detail, name='importacao_detail'),
    path('importacoes/<int:pk>/deletar/', views.importacao_deletar, name='importacao_deletar'),

    # Conciliação — strings literais ANTES do int converter para evitar colisão
    path('conciliacao/confirmar/', views.conciliacao_confirmar, name='conciliacao_confirmar'),
    path('conciliacao/ignorar/', views.conciliacao_ignorar, name='conciliacao_ignorar'),
    path('conciliacao/desfazer/', views.conciliacao_desfazer, name='conciliacao_desfazer'),
    path('conciliacao/manual/', views.conciliacao_manual, name='conciliacao_manual'),
    path('conciliacao/<int:importacao_pk>/', views.conciliacao_workspace, name='conciliacao_workspace'),

    # Relatório
    path('relatorio/', views.relatorio_conciliacao, name='relatorio_conciliacao'),

    # AJAX
    path('ajax/sugestoes/<int:lancamento_pk>/', views.ajax_sugestoes, name='ajax_sugestoes'),
]
