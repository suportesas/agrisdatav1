from django.urls import path

from . import portal_fornecedor_views as views

app_name = 'portal_fornecedor'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil_usuario, name='perfil'),
    path('pedidos/', views.pedidos_list, name='pedidos_list'),
    path('pedidos/<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('cotacoes/', views.cotacoes_list, name='cotacoes_list'),
    path('cotacoes/<int:pk>/responder/', views.cotacao_responder, name='cotacao_responder'),
]
