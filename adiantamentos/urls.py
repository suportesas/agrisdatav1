from django.urls import path

from . import views

app_name = 'adiantamentos'

urlpatterns = [
    path('', views.adiantamento_list, name='adiantamento_list'),
    path('novo/', views.adiantamento_create, name='adiantamento_create'),
    path('<int:pk>/', views.adiantamento_detail, name='adiantamento_detail'),
    path('<int:pk>/editar/', views.adiantamento_edit, name='adiantamento_edit'),
    path('<int:pk>/cancelar/', views.adiantamento_cancelar, name='adiantamento_cancelar'),
    path('<int:pk>/aplicar-desconto/', views.aplicar_desconto, name='aplicar_desconto'),
    path('<int:pk>/pular-desconto/', views.pular_desconto, name='pular_desconto'),
    path('<int:pk>/migrar/', views.migrar_adiantamento, name='migrar_adiantamento'),
    path('descontos/<int:desconto_pk>/cancelar/', views.cancelar_desconto, name='cancelar_desconto'),
    path('relatorio/', views.relatorio_adiantamentos, name='relatorio_adiantamentos'),
    path('ajax/cliente/<int:cliente_pk>/', views.ajax_adiantamentos_cliente, name='ajax_adiantamentos_cliente'),
    path('ajax/<int:pk>/desconto-sugerido/', views.ajax_desconto_sugerido, name='ajax_desconto_sugerido'),
]
