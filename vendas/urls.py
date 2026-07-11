from django.urls import path
from . import views

app_name = 'vendas'

urlpatterns = [
    path('', views.pedido_list, name='pedido_list'),
    path('novo/', views.pedido_create, name='pedido_create'),
    path('<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('<int:pk>/editar/', views.pedido_update, name='pedido_update'),
    path('<int:pk>/aprovar/', views.pedido_aprovar, name='pedido_aprovar'),
    path('<int:pk>/emitir/', views.pedido_emitir_documento, name='pedido_emitir'),
    path('<int:pk>/cancelar/', views.pedido_cancelar, name='pedido_cancelar'),

    path('tabelas-preco/', views.tabela_preco_list, name='tabela_preco_list'),
    path('tabelas-preco/nova/', views.tabela_preco_create, name='tabela_preco_create'),
    path('tabelas-preco/<int:pk>/', views.tabela_preco_detail, name='tabela_preco_detail'),
    path('tabelas-preco/<int:pk>/editar/', views.tabela_preco_update, name='tabela_preco_update'),
    path('tabelas-preco/<int:pk>/excluir/', views.tabela_preco_delete, name='tabela_preco_delete'),
]
