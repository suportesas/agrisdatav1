from django.urls import path
from . import (
    views_os, views_colheita, views_caderno_campo,
    views_pluviometria, views_qualidade_campo, views_planejamento_custo,
    views_portal_config, views_lote_producao,
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
    path('ordens-servico/<int:pk>/horimetro-pendente/', views_os.os_horimetro_pendente, name='os_horimetro_pendente'),
    path('ordens-servico/<int:pk>/recalcular-custos/', views_os.os_recalcular_custos, name='os_recalcular_custos'),
    path('ordens-servico/<int:pk>/pausar/', views_os.os_pausar_admin, name='os_pausar_admin'),
    path('ordens-servico/<int:pk>/retomar/', views_os.os_retomar_admin, name='os_retomar_admin'),
    path('ordens-servico/<int:pk>/insumos/novo/', views_os.os_insumo_add, name='os_insumo_add'),
    path('ordens-servico/<int:pk>/insumos/<int:insumo_pk>/editar/', views_os.os_insumo_edit, name='os_insumo_edit'),
    path('ordens-servico/<int:pk>/insumos/<int:insumo_pk>/excluir/', views_os.os_insumo_delete, name='os_insumo_delete'),
    path('ordens-servico/<int:pk>/funcionarios/novo/', views_os.os_funcionario_add, name='os_funcionario_add'),
    path('ordens-servico/<int:pk>/funcionarios/<int:funcionario_pk>/editar/', views_os.os_funcionario_edit, name='os_funcionario_edit'),
    path('ordens-servico/<int:pk>/funcionarios/<int:funcionario_pk>/excluir/', views_os.os_funcionario_delete, name='os_funcionario_delete'),
    path('ordens-servico/<int:pk>/maquinas/novo/', views_os.os_maquina_add, name='os_maquina_add'),
    path('ordens-servico/<int:pk>/maquinas/<int:maquina_pk>/editar/', views_os.os_maquina_edit, name='os_maquina_edit'),
    path('ordens-servico/<int:pk>/maquinas/<int:maquina_pk>/excluir/', views_os.os_maquina_delete, name='os_maquina_delete'),

    # Custo/Hora de Máquinas
    path('custos-maquina/', views_os.custo_maquina_list, name='custo_maquina_list'),
    path('custos-maquina/novo/', views_os.custo_maquina_create, name='custo_maquina_create'),
    path('custos-maquina/<int:pk>/editar/', views_os.custo_maquina_update, name='custo_maquina_update'),

    # AJAX – Classificação de OS
    path('ordens-servico/ajax/opcoes-servico/', views_os.ajax_opcoes_servico, name='os_ajax_opcoes_servico'),
    path('ordens-servico/ajax/opcoes-talhao/', views_os.ajax_opcoes_talhao, name='os_ajax_opcoes_talhao'),
    path('ordens-servico/ajax/culturas-por-safra/', views_os.ajax_culturas_por_safra, name='os_ajax_culturas_por_safra'),
    path('ordens-servico/ajax/talhoes-por-safra-cultura/', views_os.ajax_talhoes_por_safra_cultura, name='os_ajax_talhoes_por_safra_cultura'),
    path('ordens-servico/ajax/numero-corte/', views_os.ajax_numero_corte, name='os_ajax_numero_corte'),
    path('ordens-servico/ajax/produto-info/', views_os.ajax_produto_info, name='os_ajax_produto_info'),

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
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/liberar-retorno/', views_colheita.viagem_liberar_retorno, name='colheita_viagem_liberar_retorno'),
    path('ordens-servico/<int:os_pk>/colheita/<int:etapa_pk>/viagem/<int:viagem_pk>/reverter-liberacao/', views_colheita.viagem_reverter_liberacao, name='colheita_viagem_reverter_liberacao'),
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
    path('planejamento-custo/<int:pk>/editar/', views_planejamento_custo.planejamento_custo_edit, name='planejamento_custo_edit'),
    path('planejamento-custo/<int:pk>/excluir/', views_planejamento_custo.planejamento_custo_delete, name='planejamento_custo_delete'),
    path('planejamento-custo/<int:pk>/itens/novo/', views_planejamento_custo.planejamento_custo_item_add, name='planejamento_custo_item_add'),
    path('planejamento-custo/<int:pk>/itens/<int:item_pk>/editar/', views_planejamento_custo.planejamento_custo_item_edit, name='planejamento_custo_item_edit'),
    path('planejamento-custo/<int:pk>/itens/<int:item_pk>/excluir/', views_planejamento_custo.planejamento_custo_item_delete, name='planejamento_custo_item_delete'),
    path('planejamento-custo/<int:pk>/indireto/novo/', views_planejamento_custo.planejamento_custo_indireto_add, name='planejamento_custo_indireto_add'),
    path('planejamento-custo/<int:pk>/indireto/<int:item_pk>/excluir/', views_planejamento_custo.planejamento_custo_indireto_delete, name='planejamento_custo_indireto_delete'),
    path('planejamento-custo/<int:pk>/formacao-preco/', views_planejamento_custo.planejamento_custo_formacao_preco_salvar, name='planejamento_custo_formacao_preco'),
    path('planejamento-custo/ajax/preco-produto/', views_planejamento_custo.ajax_preco_produto, name='ajax_preco_produto'),
    path('planejamento-custo/ajax/safras/', views_planejamento_custo.ajax_safras_por_cultura, name='ajax_safras_planejamento_custo'),
    path('planejamento-custo/ajax/talhoes/', views_planejamento_custo.ajax_talhoes_por_safra, name='ajax_talhoes_planejamento_custo'),
    path('planejamento-custo/ajax/cotacoes/', views_planejamento_custo.ajax_cotacoes_bcb, name='ajax_cotacoes_bcb'),
    path('planejamento-custo/ajax/energia/', views_planejamento_custo.ajax_energia_periodo, name='ajax_energia_periodo'),
    path('planejamento-custo/ajax/subcategorias/', views_planejamento_custo.ajax_subcategorias_por_categoria, name='ajax_subcategorias_custo'),
    path('planejamento-custo/<int:pk>/ajax/talhoes-comparativo/', views_planejamento_custo.ajax_talhoes_comparativo, name='ajax_talhoes_comparativo'),
    path('planejamento-custo/<int:pk>/ajax/comparativo-talhao/', views_planejamento_custo.ajax_comparativo_talhao, name='ajax_comparativo_talhao'),

    # ==================== LOTES DE PRODUÇÃO (RF-109, RF-110) ====================
    path('lotes-producao/', views_lote_producao.lote_list, name='lote_list'),
    path('lotes-producao/<int:pk>/', views_lote_producao.lote_detail, name='lote_detail'),
    path('lotes-producao/<int:pk>/recepcao/', views_lote_producao.lote_recepcao_packing, name='lote_recepcao'),
]
