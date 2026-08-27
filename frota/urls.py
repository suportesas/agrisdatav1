"""URLs do módulo Frota."""
from django.urls import path

from . import views, views_motorista, views_vehicle

app_name = 'frota'

urlpatterns = [
    # ==================== COMBOBOX UNIFICADO (Select2 AJAX) ====================
    path('api/veiculos/buscar/', views.ajax_buscar_veiculos, name='ajax_buscar_veiculos'),
    path('api/motoristas/buscar/', views.ajax_buscar_motoristas, name='ajax_buscar_motoristas'),

    # ==================== VEÍCULOS ====================
    path('veiculos/', views_vehicle.vehicle_list, name='vehicle_list'),
    path('veiculos/novo/', views_vehicle.vehicle_create, name='vehicle_create'),
    path('veiculos/<int:pk>/', views_vehicle.vehicle_detail, name='vehicle_detail'),
    path('veiculos/<int:pk>/editar/', views_vehicle.vehicle_update, name='vehicle_update'),
    path('veiculos/<int:pk>/excluir/', views_vehicle.vehicle_delete, name='vehicle_delete'),
    path('veiculos/<int:vehicle_pk>/placas/nova/', views_vehicle.vehicle_plate_create, name='vehicle_plate_create'),
    path('veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/editar/', views_vehicle.vehicle_plate_update, name='vehicle_plate_update'),
    path('veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/excluir/', views_vehicle.vehicle_plate_delete, name='vehicle_plate_delete'),
    path('api/veiculos/', views_vehicle.api_vehicles, name='api_vehicles'),
    path('veiculos/export/csv/', views_vehicle.vehicle_export_csv, name='vehicle_export_csv'),

    # ==================== MOTORISTAS ====================
    path('motoristas/', views_motorista.motorista_list, name='motorista_list'),
    path('motoristas/criar/', views_motorista.motorista_create, name='motorista_create'),
    path('motoristas/<int:pk>/', views_motorista.motorista_detail, name='motorista_detail'),
    path('motoristas/<int:pk>/editar/', views_motorista.motorista_update, name='motorista_update'),
    path('motoristas/<int:pk>/deletar/', views_motorista.motorista_delete, name='motorista_delete'),
    path('motoristas/<int:pk>/portal-acesso/', views_motorista.motorista_set_pin, name='motorista_set_pin'),

    # Histórico Motorista x Placa
    path('motoristas/vinculos/', views_motorista.motorista_vinculo_list, name='motorista_vinculo_list'),
    path('motoristas/vinculos/novo/', views_motorista.motorista_vinculo_create, name='motorista_vinculo_create'),
    path('motoristas/vinculos/<int:pk>/', views_motorista.motorista_vinculo_detail, name='motorista_vinculo_detail'),
    path('motoristas/vinculos/<int:pk>/editar/', views_motorista.motorista_vinculo_update, name='motorista_vinculo_update'),
    path('motoristas/vinculos/consulta/', views_motorista.motorista_vinculo_consulta, name='motorista_vinculo_consulta'),
    path('motoristas/vinculos/consulta/pdf/', views_motorista.motorista_vinculo_consulta_pdf, name='motorista_vinculo_consulta_pdf'),

    # Documentos do Motorista
    path('motoristas/<int:motorista_pk>/documentos/criar/', views_motorista.motorista_documento_create, name='motorista_documento_create'),
    path('motoristas/<int:motorista_pk>/documentos/<int:documento_pk>/deletar/', views_motorista.motorista_documento_delete, name='motorista_documento_delete'),

    # API Motorista
    path('api/buscar-cep-motorista/', views_motorista.buscar_cep_motorista, name='buscar_cep_motorista'),

    # ==================== MÓDULO FROTA (abastecimento, manutenção, etc.) ====================
    path('', views.frota_dashboard, name='frota_dashboard'),

    # Abastecimentos
    path('abastecimentos/', views.abastecimento_list, name='abastecimento_list'),
    path('abastecimentos/novo/', views.abastecimento_create, name='abastecimento_create'),
    path('abastecimentos/<int:pk>/', views.abastecimento_detail, name='abastecimento_detail'),
    path('abastecimentos/<int:pk>/editar/', views.abastecimento_update, name='abastecimento_update'),
    path('abastecimentos/<int:pk>/excluir/', views.abastecimento_delete, name='abastecimento_delete'),
    path('abastecimentos/<int:pk>/conta-pagar/', views.abastecimento_gerar_conta_pagar, name='abastecimento_gerar_conta_pagar'),
    path('abastecimentos/importar/', views.abastecimento_importar, name='abastecimento_importar'),
    path('abastecimentos/modelo-csv/', views.abastecimento_download_modelo, name='abastecimento_download_modelo'),
    path('api/veiculo-abastecimento-info/', views.api_veiculo_info_abastecimento, name='api_veiculo_info_abastecimento'),

    # Manutenções
    path('manutencoes/', views.manutencao_list, name='manutencao_list'),
    path('manutencoes/nova/', views.manutencao_create, name='manutencao_create'),
    path('manutencoes/<int:pk>/', views.manutencao_detail, name='manutencao_detail'),
    path('manutencoes/<int:pk>/editar/', views.manutencao_update, name='manutencao_update'),
    path('manutencoes/<int:pk>/excluir/', views.manutencao_delete, name='manutencao_delete'),
    path('manutencoes/<int:pk>/aprovar/', views.manutencao_aprovar, name='manutencao_aprovar'),
    path('manutencoes/<int:pk>/reprovar/', views.manutencao_reprovar, name='manutencao_reprovar'),
    path('manutencoes/<int:pk>/itens/novo/', views.manutencao_item_add, name='manutencao_item_add'),
    path('manutencoes/<int:pk>/itens/<int:item_pk>/excluir/', views.manutencao_item_delete, name='manutencao_item_delete'),
    path('manutencoes/<int:pk>/documentos/novo/', views.manutencao_documento_add, name='manutencao_documento_add'),
    path('manutencoes/<int:pk>/documentos/<int:doc_pk>/excluir/', views.manutencao_documento_delete, name='manutencao_documento_delete'),
    path('manutencoes/<int:pk>/conta-pagar/', views.manutencao_gerar_conta_pagar, name='manutencao_gerar_conta_pagar'),
    path('alertas/', views.alertas_manutencao_list, name='alertas_manutencao_list'),
    path('alertas/<int:pk>/resolver/', views.alerta_resolver, name='alerta_resolver'),
    path('api/lote-produto-data/', views.get_lote_produto_data, name='lote_produto_data'),

    # Pedágios
    path('pedagios/', views.pedagio_list, name='pedagio_list'),
    path('pedagios/novo/', views.pedagio_create, name='pedagio_create'),
    path('pedagios/<int:pk>/editar/', views.pedagio_update, name='pedagio_update'),
    path('pedagios/<int:pk>/excluir/', views.pedagio_delete, name='pedagio_delete'),

    # Viagens (frota)
    path('viagens/', views.viagem_list, name='viagem_list'),
    path('viagens/nova/', views.viagem_create, name='viagem_create'),
    path('viagens/<int:pk>/', views.viagem_detail, name='viagem_frota_detail'),
    path('viagens/<int:pk>/editar/', views.viagem_update, name='viagem_frota_update'),
    path('viagens/<int:pk>/excluir/', views.viagem_delete, name='viagem_frota_delete'),

    # Telemetria
    path('telemetria/', views.telemetria_list, name='telemetria_list'),
    path('telemetria/nova/', views.telemetria_create, name='telemetria_create'),
    path('telemetria/<int:pk>/excluir/', views.telemetria_delete, name='telemetria_delete'),
    path('telemetria/mapa/<int:vehicle_pk>/', views.telemetria_mapa, name='telemetria_mapa'),
    path('api/telemetria/', views.api_telemetria_ingest, name='api_telemetria_ingest'),
]
