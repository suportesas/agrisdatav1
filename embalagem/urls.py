from django.urls import path
from . import views

app_name = 'embalagem'

urlpatterns = [
    # Dashboard
    path('', views.embalagem_dashboard, name='dashboard'),

    # Tipos de Embalagem
    path('tipos/', views.tipo_embalagem_list, name='tipo_embalagem_list'),
    path('tipos/novo/', views.tipo_embalagem_create, name='tipo_embalagem_create'),
    path('tipos/<int:pk>/editar/', views.tipo_embalagem_update, name='tipo_embalagem_update'),

    # Ordens de Embalagem
    path('ordens/', views.ordem_list, name='ordem_list'),
    path('ordens/nova/', views.ordem_create, name='ordem_create'),
    path('ordens/<int:pk>/', views.ordem_detail, name='ordem_detail'),
    path('ordens/<int:pk>/gerar-pallets/', views.ordem_gerar_pallets, name='ordem_gerar_pallets'),
    path('ordens/<int:pk>/etiquetas/', views.ordem_etiquetas_pdf, name='ordem_etiquetas_pdf'),

    # Pallets
    path('pallets/', views.pallet_list, name='pallet_list'),
    path('pallets/<int:pk>/etiqueta/', views.pallet_etiqueta_pdf, name='pallet_etiqueta_pdf'),

    # Pallet Misto
    path('ordens/<int:ordem_pk>/pallet-misto/', views.pallet_misto_create, name='pallet_misto_create'),
    path('pallets/<int:pk>/misto/', views.pallet_misto_detail, name='pallet_misto_detail'),
    path('pallets/<int:pk>/misto/adicionar/', views.pallet_misto_add_item, name='pallet_misto_add_item'),
    path('pallets/<int:pk>/misto/remover/<int:item_pk>/', views.pallet_misto_remove_item, name='pallet_misto_remove_item'),
    path('pallets/<int:pk>/misto/finalizar/', views.pallet_misto_finalizar, name='pallet_misto_finalizar'),

    # Romaneios
    path('romaneios/', views.romaneio_list, name='romaneio_list'),
    path('romaneios/novo/', views.romaneio_create, name='romaneio_create'),
    path('romaneios/<int:pk>/', views.romaneio_detail, name='romaneio_detail'),
    path('romaneios/<int:pk>/editar/', views.romaneio_update, name='romaneio_update'),
    path('romaneios/<int:pk>/confirmar/', views.romaneio_confirmar, name='romaneio_confirmar'),
    path('romaneios/<int:pk>/gerar-pedido/', views.romaneio_gerar_pedido, name='romaneio_gerar_pedido'),
    path('romaneios/<int:pk>/etiquetas/', views.romaneio_etiquetas_pdf, name='romaneio_etiquetas_pdf'),
    path('romaneios/<int:pk>/conferencia/', views.romaneio_conferencia, name='romaneio_conferencia'),
    path('romaneios/<int:pk>/conferencia-pdf/', views.romaneio_conferencia_pdf, name='romaneio_conferencia_pdf'),
    path('romaneios/<int:pk>/remover-pallet/<int:item_pk>/', views.romaneio_remover_pallet, name='romaneio_remover_pallet'),
    path('romaneios/<int:pk>/trocar-cliente/', views.romaneio_trocar_cliente, name='romaneio_trocar_cliente'),
    path('romaneios/<int:pk>/gerar-invoice/', views.romaneio_gerar_invoice, name='romaneio_gerar_invoice'),
    path('romaneios/<int:pk>/gerar-nota-fiscal/', views.romaneio_gerar_nota_fiscal, name='romaneio_gerar_nota_fiscal'),
    path('romaneios/<int:pk>/gerar-cte/', views.romaneio_gerar_cte, name='romaneio_gerar_cte'),

    # Cargas de Frete
    path('cargas-frete/', views.carga_frete_list, name='carga_frete_list'),
    path('cargas-frete/nova/', views.carga_frete_create, name='carga_frete_create'),
    path('cargas-frete/<int:pk>/', views.carga_frete_detail, name='carga_frete_detail'),
    path('cargas-frete/<int:pk>/editar/', views.carga_frete_update, name='carga_frete_update'),
    path('cargas-frete/<int:pk>/ratear/', views.carga_frete_ratear, name='carga_frete_ratear'),

    # AJAX
    path('ajax/pallets/', views.ajax_pallets_disponiveis, name='ajax_pallets_disponiveis'),
    path('ajax/adicionar-pallet/', views.ajax_adicionar_pallet, name='ajax_adicionar_pallet'),
    path('ajax/conferir-pallet/', views.ajax_conferir_pallet, name='ajax_conferir_pallet'),
]
