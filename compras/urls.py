"""
URLs para o módulo de Compras
"""
from django.urls import path
from . import views
from .views_dashboard import dashboard_compras
from . import views_simples
from . import views_alertas
from .views_forma_pagamento import (
    forma_pagamento_list, forma_pagamento_create, forma_pagamento_edit,
    forma_pagamento_delete
)
from .views_planejamento_embalagem import (
    planejamento_embalagem_list,
    planejamento_embalagem_create,
    planejamento_embalagem_detail,
    planejamento_embalagem_update,
    planejamento_embalagem_aprovar,
    planejamento_embalagem_revisar_precos,
    planejamento_embalagem_gerar,
    get_dados_planejamento_embalagem_por_produto,
)

app_name = 'compras'

urlpatterns = [
    # ========================================
    # 📋 FLUXO DE COMPRAS
    # ========================================

    # Solicitações de Compra
    path('solicitacoes/', views.solicitacao_list, name='solicitacao_list'),
    path('solicitacoes/nova/', views.solicitacao_create, name='solicitacao_create'),
    path('solicitacoes/<int:pk>/', views.solicitacao_detail, name='solicitacao_detail'),
    path('solicitacoes/<int:pk>/aprovar/', views.solicitacao_aprovar, name='solicitacao_aprovar'),
    path('solicitacoes/<int:pk>/cancelar/', views.solicitacao_cancelar, name='solicitacao_cancelar'),
    path('solicitacoes/<int:pk>/selecionar-itens/', views.selecionar_itens_cotar, name='selecionar_itens_cotar'),
    
    # Cotações
    path('cotacoes/', views.cotacao_list, name='cotacao_list'),
    path('cotacoes/nova/<int:solicitacao_pk>/', views.cotacao_create, name='cotacao_create'),
    path('cotacoes/<int:pk>/', views.cotacao_detail, name='cotacao_detail'),
    path('cotacoes/<int:pk>/comparativo/', views.cotacao_item_comparativo, name='cotacao_item_comparativo'),
    path('cotacoes/<int:pk>/concluir/', views.cotacao_concluir, name='cotacao_concluir'),
    
    # Propostas
    path('cotacoes/<int:cotacao_pk>/item/<int:item_pk>/proposta/', views.adicionar_proposta, name='adicionar_proposta'),
    path('propostas/<int:proposta_pk>/selecionar/', views.selecionar_fornecedor, name='selecionar_fornecedor'),
    path('propostas/<int:proposta_pk>/remover/', views.remover_proposta, name='remover_proposta'),
    
    # Geração de Solicitação de Compra em lote a partir do Relatório de Alertas de Estoque
    path('alertas-estoque-minimo/gerar-solicitacao/', views_alertas.central_alertas_gerar_solicitacao, name='central_alertas_gerar_solicitacao'),

    # Pedidos de Compra
    path('pedidos/', views.pedido_list, name='pedido_list'),
    path('pedidos/<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('pedidos/gerar/<int:cotacao_pk>/', views.pedido_gerar, name='pedido_gerar'),
    path('pedidos/direto/', views.pedido_direto_create, name='pedido_direto_create'),
    path('pedidos/<int:pk>/enviar/', views.pedido_enviar, name='pedido_enviar'),
    path('pedidos/<int:pk>/cancelar/', views.pedido_cancelar, name='pedido_cancelar'),
    path('pedidos/<int:pk>/pdf/', views.pedido_pdf, name='pedido_pdf'),
    path('pedidos/<int:pk>/enviar-email/', views.pedido_enviar_email, name='pedido_enviar_email'),
    path('pedidos/<int:pk>/whatsapp/', views.pedido_whatsapp, name='pedido_whatsapp'),
    
    # Histórico
    path('historico/<int:solicitacao_pk>/', views.historico_completo, name='historico_completo'),
    
    # Recebimentos de Compra
    path('recebimentos/', views.recebimento_list, name='recebimento_list'),
    path('recebimentos/entrada-direta/', views.entrada_direta_nf, name='entrada_direta_nf'),
    path('recebimentos/entrada-direta/buscar-produto/', views.produto_busca_ajax, name='produto_busca_ajax'),
    path('recebimentos/entrada-direta/salvar-vinculo/', views.salvar_vinculo_xml_ajax, name='salvar_vinculo_xml_ajax'),
    path('recebimentos/<int:pk>/', views.recebimento_detail, name='recebimento_detail'),
    path('recebimentos/novo/<int:pedido_id>/', views.recebimento_create, name='recebimento_create'),
    path('recebimentos/<int:pk>/conferir/', views.recebimento_conferir, name='recebimento_conferir'),
    path('recebimentos/<int:pk>/entrada-estoque/', views.recebimento_entrada_estoque, name='recebimento_entrada_estoque'),
    path('recebimentos/<int:pk>/avaliar-fornecedor/', views.avaliar_fornecedor, name='avaliar_fornecedor'),
    path('recebimentos/<int:pk>/manifestar/', views.recebimento_manifestar, name='recebimento_manifestar'),
    path('recebimentos/<int:pk>/devolucao/', views.devolucao_compra_create, name='devolucao_compra'),
    path('mde/', views.mde_list, name='mde_list'),
    path('recebimentos/<int:recebimento_pk>/faturar/', views_simples.faturar_recebimento, name='faturar_recebimento'),

    # Formas de Pagamento CRUD
    path('formas-pagamento/', forma_pagamento_list, name='forma_pagamento_list'),
    path('formas-pagamento/nova/', forma_pagamento_create, name='forma_pagamento_create'),
    path('formas-pagamento/<int:pk>/editar/', forma_pagamento_edit, name='forma_pagamento_edit'),
    path('formas-pagamento/<int:pk>/excluir/', forma_pagamento_delete, name='forma_pagamento_delete'),
    
    # API
    path('api/produto/<int:produto_id>/estoque/', views.get_produto_estoque, name='get_produto_estoque'),
    path('api/produto/<int:produto_id>/unidades/', views.get_produto_unidades, name='get_produto_unidades'),
    path('api/empresa/unidades/', views.get_empresa_unidades, name='get_empresa_unidades'),
    path('dashboard-compras/', dashboard_compras, name='dashboard_compras'),
    path('cotacoes/teste-template/',
         lambda request: __import__('compras.views_template_teste').views_template_teste.template_teste(request),
         name='cotacao_teste_template'),
    
    # ========================================
    # 📦 PLANEJAMENTO DE COMPRAS DE EMBALAGENS
    # ========================================
    path('planejamento-embalagem/', planejamento_embalagem_list, name='planejamento_embalagem_list'),
    path('planejamento-embalagem/novo/', planejamento_embalagem_create, name='planejamento_embalagem_create'),
    path('planejamento-embalagem/api/produto/<int:produto_id>/dados/', get_dados_planejamento_embalagem_por_produto, name='planejamento_embalagem_dados_produto'),
    path('planejamento-embalagem/<int:pk>/', planejamento_embalagem_detail, name='planejamento_embalagem_detail'),
    path('planejamento-embalagem/<int:pk>/editar/', planejamento_embalagem_update, name='planejamento_embalagem_update'),
    path('planejamento-embalagem/<int:pk>/aprovar/', planejamento_embalagem_aprovar, name='planejamento_embalagem_aprovar'),
    path('planejamento-embalagem/<int:pk>/revisar-precos/', planejamento_embalagem_revisar_precos, name='planejamento_embalagem_revisar_precos'),
    path('planejamento-embalagem/<int:pk>/gerar/', planejamento_embalagem_gerar, name='planejamento_embalagem_gerar'),

    # Relatórios
    path('relatorios/', views.relatorio_compras_simples, name='relatorio_compras_simples'),
    path('relatorios/pdf/', views.relatorio_compras_simples_pdf, name='relatorio_compras_simples_pdf'),
    path('relatorios/geral/', views.relatorio_compras_geral, name='relatorio_compras_geral'),
    path('relatorios/pedidos-pendentes/', views.relatorio_pedidos_pendentes, name='relatorio_pedidos_pendentes'),
    path('relatorios/compras/', views.relatorio_compras, name='relatorio_compras'),
]
