from django.urls import path
from . import views

app_name = 'energia'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('consolidado/', views.consolidado, name='consolidado'),

    # Usinas
    path('usinas/', views.usina_list, name='usina_list'),
    path('usinas/nova/', views.usina_create, name='usina_create'),
    path('usinas/<int:pk>/', views.usina_detail, name='usina_detail'),
    path('usinas/<int:pk>/editar/', views.usina_update, name='usina_update'),

    # Unidades Consumidoras
    path('unidades/', views.uc_list, name='uc_list'),
    path('unidades/nova/', views.uc_create, name='uc_create'),
    path('unidades/<int:pk>/', views.uc_detail, name='uc_detail'),
    path('unidades/<int:pk>/editar/', views.uc_update, name='uc_update'),

    # Lançamentos Mensais
    path('lancamentos/', views.lancamento_list, name='lancamento_list'),
    path('lancamentos/novo/', views.lancamento_create, name='lancamento_create'),
    path('lancamentos/<int:pk>/', views.lancamento_detail, name='lancamento_detail'),
    path('lancamentos/<int:pk>/editar/', views.lancamento_update, name='lancamento_update'),

    # Relatórios Mensais de Usina
    path('relatorios-usina/', views.relatorio_usina_list, name='relatorio_usina_list'),
    path('relatorios-usina/novo/', views.relatorio_usina_create, name='relatorio_usina_create'),
    path('relatorios-usina/<int:pk>/', views.relatorio_usina_detail, name='relatorio_usina_detail'),
    path('relatorios-usina/<int:pk>/editar/', views.relatorio_usina_update, name='relatorio_usina_update'),

    # Ocorrências
    path('ocorrencias/', views.ocorrencia_list, name='ocorrencia_list'),
    path('ocorrencias/nova/', views.ocorrencia_create, name='ocorrencia_create'),
    path('ocorrencias/nova/usina/<int:usina_pk>/', views.ocorrencia_create, name='ocorrencia_create_usina'),
    path('ocorrencias/<int:pk>/', views.ocorrencia_detail, name='ocorrencia_detail'),
    path('ocorrencias/<int:pk>/editar/', views.ocorrencia_update, name='ocorrencia_update'),
    path('ocorrencias/<int:pk>/resolver/', views.ocorrencia_resolver, name='ocorrencia_resolver'),
]
