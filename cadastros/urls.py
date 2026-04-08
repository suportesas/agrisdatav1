"""
URLs do módulo Fazendas/Cadastros
"""

from django.urls import path
from . import views
from . import views_motorista
from . import views_monitoramento_mip
from . import views_requisicao
from . import views_rh
from . import views_os
from . import views_colheita

app_name = 'cadastros'

urlpatterns = [
    # ==================== FAZENDAS ====================
    path('fazendas/', views.fazenda_list, name='fazenda_list'),
    path('fazendas/nova/', views.fazenda_create, name='fazenda_create'),
    path('fazendas/<int:pk>/', views.fazenda_detail, name='fazenda_detail'),
    path('fazendas/<int:pk>/editar/', views.fazenda_update, name='fazenda_update'),
    path('fazendas/<int:pk>/excluir/', views.fazenda_delete, name='fazenda_delete'),
    
    # ==================== APIs EXTERNAS ====================
    path('api/buscar-cnpj/', views.buscar_cnpj, name='buscar_cnpj'),
    path('api/buscar-cep/', views.buscar_cep, name='buscar_cep'),
    path('api/buscar-geolocalizacao/', views.buscar_geolocalizacao, name='buscar_geolocalizacao'),
    
    # ==================== ENDEREÇOS ====================
    path('fazendas/<int:fazenda_pk>/enderecos/novo/', views.endereco_create, name='endereco_create'),
    path('fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/editar/', views.endereco_update, name='endereco_update'),
    path('fazendas/<int:fazenda_pk>/enderecos/<int:endereco_pk>/excluir/', views.endereco_delete, name='endereco_delete'),
    
    # ==================== CONTATOS ====================
    path('fazendas/<int:fazenda_pk>/contatos/novo/', views.contato_create, name='contato_create'),
    path('fazendas/<int:fazenda_pk>/contatos/<int:contato_pk>/editar/', views.contato_update, name='contato_update'),
    path('fazendas/<int:fazenda_pk>/contatos/<int:contato_pk>/excluir/', views.contato_delete, name='contato_delete'),
    
    # ==================== CONTAS BANCÁRIAS ====================
    path('fazendas/<int:fazenda_pk>/contas/nova/', views.conta_bancaria_create, name='conta_bancaria_create'),
    path('fazendas/<int:fazenda_pk>/contas/<int:conta_pk>/editar/', views.conta_bancaria_update, name='conta_bancaria_update'),
    path('fazendas/<int:fazenda_pk>/contas/<int:conta_pk>/excluir/', views.conta_bancaria_delete, name='conta_bancaria_delete'),
    
    # ==================== DOCUMENTOS ====================
    path('fazendas/<int:fazenda_pk>/documentos/novo/', views.documento_create, name='documento_create'),
    path('fazendas/<int:fazenda_pk>/documentos/<int:documento_pk>/excluir/', views.documento_delete, name='documento_delete'),
    path('fazendas/<int:fazenda_pk>/documentos/<int:documento_pk>/editar/', views.documento_update, name='documento_update'),
    
    # ==================== ALERTAS ====================
    path('alertas/', views.dashboard_alertas, name='dashboard_alertas'),
    
    # ==================== FUNÇÕES ====================
    path('funcoes/', views.funcao_list, name='funcao_list'),
    path('funcoes/novo/', views.funcao_create, name='funcao_create'),
    path('funcoes/criar-ajax/', views.funcao_create_ajax, name='funcao_create_ajax'),
    path('funcoes/get-salario/', views.funcao_get_salario, name='funcao_get_salario'),
    path('funcoes/<int:pk>/editar/', views.funcao_update, name='funcao_update'),
    path('funcoes/<int:pk>/excluir/', views.funcao_delete, name='funcao_delete'),
    
    # ==================== FUNCIONÁRIOS ====================
    path('funcionarios/', views.funcionario_list, name='funcionario_list'),
    path('funcionarios/novo/', views.funcionario_create, name='funcionario_create'),
    path('funcionarios/<int:pk>/', views.funcionario_detail, name='funcionario_detail'),
    path('funcionarios/<int:pk>/editar/', views.funcionario_update, name='funcionario_update'),
    path('funcionarios/<int:pk>/excluir/', views.funcionario_delete, name='funcionario_delete'),

        # Documentos Funcionário
        path('funcionarios/<int:funcionario_pk>/documentos/novo/', views.funcionario_documento_create, name='funcionario_documento_create'),
    

    # ==================== CULTURAS ====================
    path('culturas/', views.cultura_list, name='cultura_list'),
    path('culturas/nova/', views.cultura_create, name='cultura_create'),
    path('culturas/<int:pk>/', views.cultura_detail, name='cultura_detail'),
    path('culturas/<int:pk>/editar/', views.cultura_update, name='cultura_update'),
    path('culturas/<int:pk>/excluir/', views.cultura_delete, name='cultura_delete'),

    # ==================== PRAGAS ====================
    path('pragas/', views.praga_list, name='praga_list'),
    path('pragas/nova/', views.praga_create, name='praga_create'),
    path('pragas/<int:pk>/', views.praga_detail, name='praga_detail'),
    path('pragas/<int:pk>/editar/', views.praga_update, name='praga_update'),
    path('pragas/<int:pk>/excluir/', views.praga_delete, name='praga_delete'),

    
    # ====================  Áreas ====================== 
    path('areas/', views.area_list, name='area_list'),
    path('areas/nova/', views.area_create, name='area_create'),
    path('areas/<int:pk>/', views.area_detail, name='area_detail'),
    path('areas/<int:pk>/editar/', views.area_update, name='area_update'),
    path('areas/<int:pk>/excluir/', views.area_delete, name='area_delete'),
    
    # Talhões
    path('talhoes/', views.talhao_list, name='talhao_list'),
    path('talhoes/novo/', views.talhao_create, name='talhao_create'),
    path('talhoes/<int:pk>/', views.talhao_detail, name='talhao_detail'),
    path('talhoes/<int:pk>/editar/', views.talhao_update, name='talhao_update'),
    path('talhoes/<int:pk>/excluir/', views.talhao_delete, name='talhao_delete'),
    # Histórico de cultivo
    path('talhoes/<int:talhao_pk>/historico/nova/', views.historico_create, name='historico_create'),
    path('historico/<int:pk>/editar/', views.historico_update, name='historico_update'),
    path('historico/<int:pk>/excluir/', views.historico_delete, name='historico_delete'),
    path('historico/<int:pk>/', views.historico_detail, name='historico_detail'),
    
    # Safras
    path('safras/', views.safra_list, name='safra_list'),
    path('safras/nova/', views.safra_create, name='safra_create'),
    path('safras/<int:pk>/', views.safra_detail, name='safra_detail'),
    path('safras/<int:pk>/editar/', views.safra_update, name='safra_update'),
    path('safras/<int:pk>/planejamento/novo/', views.safra_plan_create, name='safra_plan_create'),
    path('safras/<int:pk>/planejamento/editar/', views.safra_plan_update, name='safra_plan_update'),
    path('safras/<int:pk>/planejamento/excluir/', views.safra_plan_delete, name='safra_plan_delete'),
    path('safras/<int:pk>/excluir/', views.safra_delete, name='safra_delete'),
    
    # AJAX
    path('ajax/areas-por-fazenda/<int:fazenda_id>/', views.ajax_areas_por_fazenda, name='ajax_areas_fazenda'),
    path('ajax/talhoes-por-fazenda/<int:fazenda_id>/', views.ajax_talhoes_por_fazenda, name='ajax_talhoes_fazenda'),

    # Vendedores    
    path('vendedores/', views.vendedor_list, name='vendedor_list'),
    path('vendedores/novo/', views.vendedor_create, name='vendedor_create'),
    path('vendedores/<int:pk>/', views.vendedor_detail, name='vendedor_detail'),
    path('vendedores/<int:pk>/editar/', views.vendedor_update, name='vendedor_update'),
    path('vendedores/<int:pk>/excluir/', views.vendedor_delete, name='vendedor_delete'),
    path('vendedores/<int:pk>/inativar/', views.vendedor_inativar, name='vendedor_inativar'),
    path('vendedores/<int:pk>/reativar/', views.vendedor_reativar, name='vendedor_reativar'),
    
    # Comissões
    path('comissoes/', views.comissao_list, name='comissao_list'),
    path('comissoes/nova/', views.comissao_create, name='comissao_create'),
    path('comissoes/<int:pk>/pagar/', views.comissao_pagar, name='comissao_pagar'),
    
    # APIs
    path('vendedores/api/json/', views.vendedor_json, name='vendedor_json'),
    path('api/vendedores-por-tipo/', views.vendedores_por_tipo, name='vendedores_por_tipo'),


   
    # Fornecedores
    path('fornecedores/', views.fornecedor_list, name='fornecedor_list'),
    path('fornecedores/novo/', views.fornecedor_create, name='fornecedor_create'),
    path('fornecedores/<int:pk>/', views.fornecedor_detail, name='fornecedor_detail'),
    path('fornecedores/<int:pk>/pdf/', views.fornecedor_pdf, name='fornecedor_pdf'),
    path('fornecedores/<int:pk>/editar/', views.fornecedor_update, name='fornecedor_update'),
    path('fornecedores/<int:pk>/excluir/', views.fornecedor_delete, name='fornecedor_delete'),
    path('fornecedores/<int:pk>/portal/criar-acesso/', views.fornecedor_criar_acesso_portal, name='fornecedor_criar_acesso_portal'),
    path('fornecedores/<int:pk>/portal/bloquear/', views.fornecedor_bloquear_portal, name='fornecedor_bloquear_portal'),
    path('fornecedores/relatorio/', views.relatorio_fornecedor, name='relatorio_fornecedor'),
    path('fornecedores/relatorio-ranking/', views.relatorio_fornecedor_ranking, name='relatorio_fornecedor_ranking'),

    # Transportadoras
    path('transportadoras/', views.transportadora_list, name='transportadora_list'),
    path('transportadoras/<int:pk>/', views.transportadora_detail, name='transportadora_detail'),
    path('transportadoras/novo/', views.transportadora_create, name='transportadora_create'),
    path('transportadoras/<int:pk>/editar/', views.transportadora_update, name='transportadora_update'),
    path('transportadoras/<int:pk>/excluir/', views.transportadora_delete, name='transportadora_delete'),
    # Inline edit frete (AJAX)
    path('transportadoras/<int:pk>/frete/', views.transportadora_update_frete, name='transportadora_update_frete'),
    # API JSON endpoints
    path('api/transportadoras/', views.api_transportadoras, name='api_transportadoras'),
    path('api/transportadoras/<int:pk>/viagens/', views.api_transportadora_viagens, name='api_transportadora_viagens'),

    # ==================== VEÍCULOS / FROTA ====================
    path('veiculos/', views.vehicle_list, name='vehicle_list'),
    path('veiculos/novo/', views.vehicle_create, name='vehicle_create'),
    path('veiculos/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
    path('veiculos/<int:pk>/editar/', views.vehicle_update, name='vehicle_update'),
    path('veiculos/<int:pk>/excluir/', views.vehicle_delete, name='vehicle_delete'),
    path('veiculos/<int:vehicle_pk>/placas/nova/', views.vehicle_plate_create, name='vehicle_plate_create'),
    path('veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/editar/', views.vehicle_plate_update, name='vehicle_plate_update'),
    path('veiculos/<int:vehicle_pk>/placas/<int:plate_pk>/excluir/', views.vehicle_plate_delete, name='vehicle_plate_delete'),

    # API: vehicles
    path('api/veiculos/', views.api_vehicles, name='api_vehicles'),
    path('veiculos/export/csv/', views.vehicle_export_csv, name='vehicle_export_csv'),

    # ==================== REQUISICOES ====================
    path('requisicoes/', views_requisicao.requisicao_list, name='requisicao_list'),
    path('requisicoes/pendentes-aprovacao/', views_requisicao.requisicao_pendentes_aprovacao, name='requisicao_pendentes_aprovacao'),
    path('requisicoes/nova/', views_requisicao.requisicao_create, name='requisicao_create'),
    path('requisicoes/<int:pk>/', views_requisicao.requisicao_detail, name='requisicao_detail'),
    path('requisicoes/<int:pk>/editar/', views_requisicao.requisicao_update, name='requisicao_update'),
    path('requisicoes/<int:pk>/excluir/', views_requisicao.requisicao_delete, name='requisicao_delete'),
    path('requisicoes/<int:pk>/aprovar/', views_requisicao.requisicao_aprovar, name='requisicao_aprovar'),
    path('requisicoes/<int:pk>/atender/', views_requisicao.requisicao_atender, name='requisicao_atender'),
    path('requisicoes/<int:pk>/cancelar/', views_requisicao.requisicao_cancelar, name='requisicao_cancelar'),
    path('requisicoes/<int:requisicao_id>/itens/novo/', views_requisicao.requisicao_item_create, name='requisicao_item_create'),
    path('requisicoes/<int:requisicao_id>/itens/<int:item_id>/editar/', views_requisicao.requisicao_item_update, name='requisicao_item_update'),
    path('requisicoes/<int:requisicao_id>/itens/<int:item_id>/excluir/', views_requisicao.requisicao_item_delete, name='requisicao_item_delete'),
    path('api/requisicoes/safras-por-talhao/<int:talhao_id>/', views_requisicao.ajax_safras_por_talhao, name='ajax_safras_por_talhao'),
    path('api/requisicoes/talhao-por-codigo/', views_requisicao.ajax_talhao_por_codigo, name='ajax_talhao_por_codigo'),

    # Fornecedor: endereços
    path('fornecedores/<int:fornecedor_pk>/enderecos/novo/', views.fornecedor_endereco_create, name='fornecedor_endereco_create'),
    path('fornecedores/<int:fornecedor_pk>/enderecos/<int:endereco_pk>/editar/', views.fornecedor_endereco_update, name='fornecedor_endereco_update'),
    path('fornecedores/<int:fornecedor_pk>/enderecos/<int:endereco_pk>/excluir/', views.fornecedor_endereco_delete, name='fornecedor_endereco_delete'),

    # Fornecedor: contatos
    path('fornecedores/<int:fornecedor_pk>/contatos/novo/', views.fornecedor_contato_create, name='fornecedor_contato_create'),
    path('fornecedores/<int:fornecedor_pk>/contatos/<int:contato_pk>/editar/', views.fornecedor_contato_update, name='fornecedor_contato_update'),
    path('fornecedores/<int:fornecedor_pk>/contatos/<int:contato_pk>/excluir/', views.fornecedor_contato_delete, name='fornecedor_contato_delete'),

    # Fornecedor: contas bancárias
    path('fornecedores/<int:fornecedor_pk>/contas/nova/', views.fornecedor_conta_create, name='fornecedor_conta_create'),
    path('fornecedores/<int:fornecedor_pk>/contas/<int:conta_pk>/editar/', views.fornecedor_conta_update, name='fornecedor_conta_update'),
    path('fornecedores/<int:fornecedor_pk>/contas/<int:conta_pk>/excluir/', views.fornecedor_conta_delete, name='fornecedor_conta_delete'),

    # Fornecedor: documentos
    path('fornecedores/<int:fornecedor_pk>/documentos/novo/', views.fornecedor_documento_create, name='fornecedor_documento_create'),
    path('fornecedores/<int:fornecedor_pk>/documentos/<int:documento_pk>/excluir/', views.fornecedor_documento_delete, name='fornecedor_documento_delete'),
    path('fornecedores/<int:fornecedor_pk>/documentos/<int:documento_pk>/editar/', views.fornecedor_documento_update, name='fornecedor_documento_update'),

    # Clientes
    path('clientes/', views.cliente_list, name='cliente_list'),
    path('clientes/novo/', views.cliente_create, name='cliente_create'),
    path('clientes/<int:pk>/', views.cliente_detail, name='cliente_detail'),
    path('clientes/<int:pk>/pdf/', views.cliente_pdf, name='cliente_pdf'),
    path('clientes/<int:pk>/editar/', views.cliente_update, name='cliente_update'),
    path('clientes/<int:pk>/excluir/', views.cliente_delete, name='cliente_delete'),
    path('clientes/<int:pk>/reativar/', views.cliente_activate, name='cliente_activate'),
    path('clientes/relatorio/', views.relatorio_cliente, name='relatorio_cliente'),

    # AJAX endpoints
    path('moedas/novo-ajax/', views.moeda_create_ajax, name='moeda_create_ajax'),

    # NCM (Nomenclatura Comum do Mercosul)
    path('ncm/', views.ncm_list, name='ncm_list'),
    path('ncm/popular/', views.ncm_seed, name='ncm_seed'),
    path('ncm/novo/', views.ncm_create, name='ncm_create'),
    path('ncm/<int:pk>/editar/', views.ncm_update, name='ncm_update'),
    path('ncm/<int:pk>/excluir/', views.ncm_delete, name='ncm_delete'),
    path('api/ncm/autocomplete/', views.ncm_autocomplete, name='ncm_autocomplete'),
    path('ncm/importar/', views.ncm_import, name='ncm_import'),

    # CFOP (Código Fiscal de Operações e Prestações)
    path('cfop/', views.cfop_list, name='cfop_list'),
    path('cfop/popular/', views.cfop_seed, name='cfop_seed'),
    path('cfop/novo/', views.cfop_create, name='cfop_create'),
    path('cfop/importar/', views.cfop_import, name='cfop_import'),
    path('cfop/<int:pk>/editar/', views.cfop_update, name='cfop_update'),
    path('cfop/<int:pk>/excluir/', views.cfop_delete, name='cfop_delete'),

    # Cliente: endereços
    path('clientes/<int:cliente_pk>/enderecos/novo/', views.cliente_endereco_create, name='cliente_endereco_create'),
    path('clientes/<int:cliente_pk>/enderecos/<int:endereco_pk>/editar/', views.cliente_endereco_update, name='cliente_endereco_update'),
    path('clientes/<int:cliente_pk>/enderecos/<int:endereco_pk>/excluir/', views.cliente_endereco_delete, name='cliente_endereco_delete'),

    # Cliente: contatos
    path('clientes/<int:cliente_pk>/contatos/novo/', views.cliente_contato_create, name='cliente_contato_create'),
    path('clientes/<int:cliente_pk>/contatos/ajax/novo/', views.cliente_contato_create_ajax, name='cliente_contato_create_ajax'),
    path('clientes/<int:cliente_pk>/contatos/<int:contato_pk>/editar/', views.cliente_contato_update, name='cliente_contato_update'),
    path('clientes/<int:cliente_pk>/contatos/<int:contato_pk>/excluir/', views.cliente_contato_delete, name='cliente_contato_delete'),

    # Cliente: contas bancárias
    path('clientes/<int:cliente_pk>/contas/nova/', views.cliente_conta_create, name='cliente_conta_create'),
    path('clientes/<int:cliente_pk>/contas/ajax/nova/', views.cliente_conta_create_ajax, name='cliente_conta_create_ajax'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/editar/', views.cliente_conta_update, name='cliente_conta_update'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/excluir/', views.cliente_conta_delete, name='cliente_conta_delete'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/editar/ajax/', views.cliente_conta_update_ajax, name='cliente_conta_update_ajax'),
    path('clientes/<int:cliente_pk>/contas/<int:conta_pk>/excluir/ajax/', views.cliente_conta_delete_ajax, name='cliente_conta_delete_ajax'),

    # Cliente: documentos
    path('clientes/<int:cliente_pk>/documentos/novo/', views.cliente_documento_create, name='cliente_documento_create'),
    path('clientes/<int:cliente_pk>/documentos/ajax/novo/', views.cliente_documento_create_ajax, name='cliente_documento_create_ajax'),
    path('clientes/<int:cliente_pk>/documentos/<int:documento_pk>/excluir/', views.cliente_documento_delete, name='cliente_documento_delete'),
    path('clientes/<int:cliente_pk>/documentos/<int:documento_pk>/editar/', views.cliente_documento_update, name='cliente_documento_update'),

    # ==================== PORTOS ====================
    path('portos/', views.porto_list, name='porto_list'),
    path('portos/novo/', views.porto_create, name='porto_create'),
    path('portos/<int:pk>/', views.porto_detail, name='porto_detail'),
    path('portos/<int:pk>/editar/', views.porto_update, name='porto_update'),
    path('portos/<int:pk>/excluir/', views.porto_delete, name='porto_delete'),

    # ==================== ARMADORES ====================
    path('armadores/', views.armador_list, name='armador_list'),
    path('armadores/create/', views.armador_create, name='armador_create'),
    path('armadores/<int:pk>/', views.armador_detail, name='armador_detail'),
    path('armadores/<int:pk>/edit/', views.armador_update, name='armador_update'),
    path('armadores/<int:pk>/delete/', views.armador_delete, name='armador_delete'),
    
    # Armador Endereço
    path('armadores/<int:armador_pk>/endereco/create/', views.armador_endereco_create, name='armador_endereco_create'),
    path('armadores/<int:armador_pk>/endereco/<int:pk>/edit/', views.armador_endereco_update, name='armador_endereco_update'),
    path('armadores/<int:armador_pk>/endereco/<int:pk>/delete/', views.armador_endereco_delete, name='armador_endereco_delete'),
    
    # Armador Contato
    path('armadores/<int:armador_pk>/contato/create/', views.armador_contato_create, name='armador_contato_create'),
    path('armadores/<int:armador_pk>/contato/<int:pk>/edit/', views.armador_contato_update, name='armador_contato_update'),
    path('armadores/<int:armador_pk>/contato/<int:pk>/delete/', views.armador_contato_delete, name='armador_contato_delete'),
    
    # Armador Banco
    path('armadores/<int:armador_pk>/banco/create/', views.armador_banco_create, name='armador_banco_create'),
    path('armadores/<int:armador_pk>/banco/<int:pk>/edit/', views.armador_banco_update, name='armador_banco_update'),
    path('armadores/<int:armador_pk>/banco/<int:pk>/delete/', views.armador_banco_delete, name='armador_banco_delete'),

    # ==================== NAVIOS ====================
    path('navios/', views.navio_list, name='navio_list'),
    path('navios/create/', views.navio_create, name='navio_create'),
    path('navios/<int:pk>/', views.navio_detail, name='navio_detail'),
    path('navios/<int:pk>/edit/', views.navio_update, name='navio_update'),
    path('navios/<int:pk>/delete/', views.navio_delete, name='navio_delete'),

    # ==================== MOTORISTAS ====================
    path('motoristas/', views_motorista.motorista_list, name='motorista_list'),
    path('motoristas/criar/', views_motorista.motorista_create, name='motorista_create'),
    path('motoristas/<int:pk>/', views_motorista.motorista_detail, name='motorista_detail'),
    path('motoristas/<int:pk>/editar/', views_motorista.motorista_update, name='motorista_update'),
    path('motoristas/<int:pk>/deletar/', views_motorista.motorista_delete, name='motorista_delete'),

    # Historico Motorista x Placa
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
    
    # ==================== PRAZOS DE PAGAMENTO ====================
    path('prazos-pagamento/', views.prazo_pagamento_list, name='prazo_pagamento_list'),
    path('prazos-pagamento/novo/', views.prazo_pagamento_create, name='prazo_pagamento_create'),
    path('prazos-pagamento/<int:pk>/', views.prazo_pagamento_detail, name='prazo_pagamento_detail'),
    path('prazos-pagamento/<int:pk>/editar/', views.prazo_pagamento_update, name='prazo_pagamento_update'),
    path('prazos-pagamento/<int:pk>/excluir/', views.prazo_pagamento_delete, name='prazo_pagamento_delete'),
    
    # ==================== MONITORAMENTO MIP (Manejo Integrado de Pragas) ====================
    # Estágios de Desenvolvimento
    path('estagios/', views_monitoramento_mip.estagio_list, name='estagio_list'),
    path('estagios/novo/', views_monitoramento_mip.estagio_create, name='estagio_create'),
    path('estagios/<int:pk>/editar/', views_monitoramento_mip.estagio_update, name='estagio_update'),
    path('estagios/<int:pk>/excluir/', views_monitoramento_mip.estagio_delete, name='estagio_delete'),
    
    # Monitoramentos MIP
    path('monitoramento-mip/', views_monitoramento_mip.monitoramento_mip_list, name='monitoramento_mip_list'),
    path('monitoramento-mip/novo/', views_monitoramento_mip.monitoramento_mip_create, name='monitoramento_mip_create'),
    path('monitoramento-mip/<int:pk>/', views_monitoramento_mip.monitoramento_mip_detail, name='monitoramento_mip_detail'),
    path('monitoramento-mip/<int:pk>/pdf/', views_monitoramento_mip.monitoramento_mip_pdf, name='monitoramento_mip_pdf'),
    path('monitoramento-mip/<int:pk>/adicionar-praga/', views_monitoramento_mip.monitoramento_mip_add_praga, name='monitoramento_mip_add_praga'),
    path('monitoramento-mip/praga/<int:pk>/', views_monitoramento_mip.monitoramento_mip_praga_detail, name='monitoramento_mip_praga_detail'),
    path('monitoramento-mip/praga/<int:pk>/adicionar-ponto/', views_monitoramento_mip.monitoramento_mip_add_ponto, name='monitoramento_mip_add_ponto'),
    
    # AJAX endpoints
    path('ajax/estagios-praga/', views_monitoramento_mip.ajax_get_estagios_praga, name='ajax_get_estagios_praga'),
    path('ajax/pragas-cultura/', views_monitoramento_mip.ajax_get_pragas_cultura, name='ajax_get_pragas_cultura'),
    path('ajax/calcular-incidencia/', views_monitoramento_mip.ajax_calcular_incidencia, name='ajax_calcular_incidencia'),
    
    # Cadastro em Lote de Estágios
    path('estagios/cadastro-lote/', views_monitoramento_mip.estagio_cadastro_em_lote, name='estagio_cadastro_em_lote'),
    path('ajax/adicionar-estagio/', views_monitoramento_mip.ajax_adicionar_estagio, name='ajax_adicionar_estagio'),
    path('ajax/carregar-estagios/', views_monitoramento_mip.ajax_carregar_estagios, name='ajax_carregar_estagios'),
    path('ajax/deletar-estagio/<int:pk>/', views_monitoramento_mip.ajax_deletar_estagio, name='ajax_deletar_estagio'),
    path('ajax/buscar-talhoes/', views_monitoramento_mip.ajax_buscar_talhoes, name='ajax_buscar_talhoes'),
    path('ajax/talhao-info/<int:talhao_id>/', views_monitoramento_mip.ajax_talhao_info, name='ajax_talhao_info'),

    # ==================== RH - RECURSOS HUMANOS ====================
    # Dashboard
    path('rh/', views_rh.rh_dashboard, name='rh_dashboard'),
    
    # Férias
    path('rh/ferias/', views_rh.ferias_list, name='ferias_list'),
    path('rh/ferias/novo/', views_rh.ferias_create, name='ferias_create'),
    path('rh/ferias/<int:pk>/', views_rh.ferias_detail, name='ferias_detail'),
    path('rh/ferias/<int:pk>/editar/', views_rh.ferias_update, name='ferias_update'),
    path('rh/ferias/<int:pk>/excluir/', views_rh.ferias_delete, name='ferias_delete'),
    
    # Afastamentos
    path('rh/afastamentos/', views_rh.afastamento_list, name='afastamento_list'),
    path('rh/afastamentos/novo/', views_rh.afastamento_create, name='afastamento_create'),
    path('rh/afastamentos/<int:pk>/', views_rh.afastamento_detail, name='afastamento_detail'),
    path('rh/afastamentos/<int:pk>/editar/', views_rh.afastamento_update, name='afastamento_update'),
    path('rh/afastamentos/<int:pk>/excluir/', views_rh.afastamento_delete, name='afastamento_delete'),
    
    # Rescisões
    path('rh/rescisoes/', views_rh.rescisao_list, name='rescisao_list'),
    path('rh/rescisoes/novo/', views_rh.rescisao_create, name='rescisao_create'),
    path('rh/rescisoes/<int:pk>/', views_rh.rescisao_detail, name='rescisao_detail'),
    path('rh/rescisoes/<int:pk>/editar/', views_rh.rescisao_update, name='rescisao_update'),
    path('rh/rescisoes/<int:pk>/excluir/', views_rh.rescisao_delete, name='rescisao_delete'),
    
    # Relatórios RH
    path('rh/relatorio/', views_rh.relatorio_rh, name='relatorio_rh'),
    path('rh/relatorio/pdf/', views_rh.relatorio_rh_pdf, name='relatorio_rh_pdf'),

    # ==================== ORDENS DE SERVIÇO ====================
    path('ordens-servico/', views_os.os_list, name='os_list'),
    path('ordens-servico/nova/', views_os.os_create, name='os_create'),
    path('ordens-servico/custos-talhao/', views_os.custo_talhao_list, name='custo_talhao_list'),
    path('ordens-servico/<int:pk>/', views_os.os_detail, name='os_detail'),
    path('ordens-servico/<int:pk>/editar/', views_os.os_update, name='os_update'),
    path('ordens-servico/<int:pk>/excluir/', views_os.os_delete, name='os_delete'),
    path('ordens-servico/<int:pk>/aprovar/', views_os.os_aprovar, name='os_aprovar'),
    path('ordens-servico/<int:pk>/iniciar/', views_os.os_iniciar, name='os_iniciar'),
    path('ordens-servico/<int:pk>/concluir/', views_os.os_concluir, name='os_concluir'),
    path('ordens-servico/<int:pk>/insumos/novo/', views_os.os_insumo_add, name='os_insumo_add'),
    path('ordens-servico/<int:pk>/insumos/<int:insumo_pk>/editar/', views_os.os_insumo_edit, name='os_insumo_edit'),
    path('ordens-servico/<int:pk>/insumos/<int:insumo_pk>/excluir/', views_os.os_insumo_delete, name='os_insumo_delete'),

    # Custo/Hora de Máquinas
    path('custos-maquina/', views_os.custo_maquina_list, name='custo_maquina_list'),
    path('custos-maquina/novo/', views_os.custo_maquina_create, name='custo_maquina_create'),
    path('custos-maquina/<int:pk>/editar/', views_os.custo_maquina_update, name='custo_maquina_update'),

    # AJAX – Classificação de OS
    path('ordens-servico/ajax/opcoes-servico/', views_os.ajax_opcoes_servico, name='os_ajax_opcoes_servico'),
    path('ordens-servico/ajax/opcoes-talhao/', views_os.ajax_opcoes_talhao, name='os_ajax_opcoes_talhao'),

    # ==================== COLHEITA ====================
    path('ordens-servico/<int:os_pk>/colheita/nova-etapa/', views_colheita.etapa_nova, name='colheita_nova_etapa'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/', views_colheita.etapa_detalhe, name='colheita_detalhe'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/concluir/', views_colheita.etapa_concluir, name='colheita_concluir'),

    # Frotas (tratores)
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/adicionar/', views_colheita.frota_adicionar, name='colheita_frota_adicionar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/<int:frota_pk>/horimetro/', views_colheita.frota_horimetro_final, name='colheita_frota_horimetro'),

    # Carroções
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/<int:frota_pk>/carrocao/adicionar/', views_colheita.carrocao_adicionar, name='colheita_carrocao_adicionar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/carrocao/<int:carrocao_pk>/remover/', views_colheita.carrocao_remover, name='colheita_carrocao_remover'),

    # Viagens / Pesagens
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/carrocao/<int:carrocao_pk>/viagem/nova/', views_colheita.viagem_nova, name='colheita_viagem_nova'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/editar/', views_colheita.viagem_editar, name='colheita_viagem_editar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/excluir/', views_colheita.viagem_excluir, name='colheita_viagem_excluir'),

    # AJAX
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/ajax/carrocoes/', views_colheita.ajax_carrocoes_disponiveis, name='colheita_ajax_carrocoes'),

]
