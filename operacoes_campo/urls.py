from django.urls import path
from . import (
    views_os, views_colheita, views_caderno_campo,
    views_pluviometria, views_qualidade_campo, views_planejamento_custo,
    views_portal_config,
)


app_name = 'operacoes_campo'

urlpatterns = [
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

    # Delegação
    path('delegacao/', views_os.os_painel_delegacao, name='os_painel_delegacao'),

    # Configurações do Portal do Campo
    path('portal-campo/config/', views_portal_config.portal_campo_config_view, name='portal_campo_config'),
    path('ordens-servico/<int:pk>/atribuir/', views_os.os_atribuir_responsavel, name='os_atribuir_responsavel'),

    # ==================== COLHEITA ====================
    path('ordens-servico/<int:os_pk>/colheita/nova-etapa/', views_colheita.etapa_nova, name='colheita_nova_etapa'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/', views_colheita.etapa_detalhe, name='colheita_detalhe'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/concluir/', views_colheita.etapa_concluir, name='colheita_concluir'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/adicionar/', views_colheita.frota_adicionar, name='colheita_frota_adicionar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/<int:frota_pk>/horimetro/', views_colheita.frota_horimetro_final, name='colheita_frota_horimetro'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/frota/<int:frota_pk>/carrocao/adicionar/', views_colheita.carrocao_adicionar, name='colheita_carrocao_adicionar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/carrocao/<int:carrocao_pk>/remover/', views_colheita.carrocao_remover, name='colheita_carrocao_remover'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/carrocao/<int:carrocao_pk>/viagem/nova/', views_colheita.viagem_nova, name='colheita_viagem_nova'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/editar/', views_colheita.viagem_editar, name='colheita_viagem_editar'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/excluir/', views_colheita.viagem_excluir, name='colheita_viagem_excluir'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/ajax/carrocoes/', views_colheita.ajax_carrocoes_disponiveis, name='colheita_ajax_carrocoes'),

    # ==================== PLUVIOMETRIA ====================
    path('pluviometria/', views_pluviometria.pluviometria_list, name='pluviometria_list'),
    path('pluviometria/novo/', views_pluviometria.pluviometria_create, name='pluviometria_create'),
    path('pluviometria/<int:pk>/editar/', views_pluviometria.pluviometria_update, name='pluviometria_update'),
    path('pluviometria/<int:pk>/excluir/', views_pluviometria.pluviometria_delete, name='pluviometria_delete'),
    path('pluviometria/dashboard/', views_pluviometria.pluviometria_dashboard, name='pluviometria_dashboard'),

    # ==================== QUALIDADE DE CAMPO ====================
    path('qualidade-campo/', views_qualidade_campo.qualidade_campo_list, name='qualidade_campo_list'),
    path('qualidade-campo/nova/', views_qualidade_campo.qualidade_campo_create, name='qualidade_campo_create'),
    path('qualidade-campo/<int:pk>/', views_qualidade_campo.qualidade_campo_detail, name='qualidade_campo_detail'),
    path('qualidade-campo/<int:pk>/editar/', views_qualidade_campo.qualidade_campo_update, name='qualidade_campo_update'),
    path('qualidade-campo/<int:pk>/excluir/', views_qualidade_campo.qualidade_campo_delete, name='qualidade_campo_delete'),
    path('qualidade-campo/<int:pk>/pdf/', views_qualidade_campo.qualidade_campo_pdf, name='qualidade_campo_pdf'),

    # ==================== CADERNO DE CAMPO ====================
    path('caderno-campo/', views_caderno_campo.caderno_campo_list, name='caderno_campo_list'),
    path('caderno-campo/novo/', views_caderno_campo.caderno_campo_create, name='caderno_campo_create'),
    path('caderno-campo/pdf/', views_caderno_campo.caderno_campo_pdf, name='caderno_campo_pdf'),
    path('caderno-campo/<int:pk>/', views_caderno_campo.caderno_campo_detail, name='caderno_campo_detail'),
    path('caderno-campo/<int:pk>/editar/', views_caderno_campo.caderno_campo_update, name='caderno_campo_update'),
    path('caderno-campo/<int:pk>/excluir/', views_caderno_campo.caderno_campo_delete, name='caderno_campo_delete'),
    path('caderno-campo/<int:pk>/insumos/novo/', views_caderno_campo.caderno_campo_insumo_add, name='caderno_campo_insumo_add'),
    path('caderno-campo/<int:pk>/insumos/<int:insumo_pk>/excluir/', views_caderno_campo.caderno_campo_insumo_delete, name='caderno_campo_insumo_delete'),
    path('caderno-campo/<int:pk>/funcionarios/novo/', views_caderno_campo.caderno_campo_funcionario_add, name='caderno_campo_funcionario_add'),
    path('caderno-campo/<int:pk>/funcionarios/<int:func_pk>/excluir/', views_caderno_campo.caderno_campo_funcionario_delete, name='caderno_campo_funcionario_delete'),

    # ==================== PLANEJAMENTO DE CUSTO ====================
    path('planejamento-custo/', views_planejamento_custo.planejamento_custo_list, name='planejamento_custo_list'),
    path('planejamento-custo/novo/', views_planejamento_custo.planejamento_custo_create, name='planejamento_custo_create'),
    path('planejamento-custo/<int:pk>/', views_planejamento_custo.planejamento_custo_detail, name='planejamento_custo_detail'),
    path('planejamento-custo/<int:pk>/excluir/', views_planejamento_custo.planejamento_custo_delete, name='planejamento_custo_delete'),
    path('planejamento-custo/<int:pk>/itens/novo/', views_planejamento_custo.planejamento_custo_item_add, name='planejamento_custo_item_add'),
    path('planejamento-custo/<int:pk>/itens/<int:item_pk>/excluir/', views_planejamento_custo.planejamento_custo_item_delete, name='planejamento_custo_item_delete'),
    path('planejamento-custo/ajax/preco-produto/', views_planejamento_custo.ajax_preco_produto, name='ajax_preco_produto'),
    path('planejamento-custo/ajax/safras/', views_planejamento_custo.ajax_safras_por_cultura, name='ajax_safras_planejamento_custo'),
    path('planejamento-custo/ajax/talhoes/', views_planejamento_custo.ajax_talhoes_por_safra, name='ajax_talhoes_planejamento_custo'),
]
