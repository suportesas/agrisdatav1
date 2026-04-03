"""
URLs para o módulo de Compras
"""
from django.urls import path
from . import views
from .views_cotacao import (
    cotacao_list, cotacao_create_step1, cotacao_create_step2,
    cotacao_detail, proposta_create, proposta_selecionar, historico_precos,
    historico_precos_list
)
from .views_dashboard import dashboard_compras
from . import views_simples

app_name = 'compras'

urlpatterns = [
    # ========================================
    # 🚀 MODO SIMPLES - Compras Rápidas
    # ========================================
    path('compra-rapida/', views_simples.compra_rapida, name='compra_rapida'),
    path('pedidos/<int:pk>/editar/', views_simples.pedido_edit, name='pedido_edit'),
    path('recebimento-rapido/', views_simples.recebimento_rapido, name='recebimento_rapido'),
    path('recebimento-rapido/<int:pedido_pk>/', views_simples.recebimento_rapido, name='recebimento_rapido_pedido'),
    path('escolher-modo/', views_simples.escolher_modo_compra, name='escolher_modo_compra'),
    
    # ========================================
    # 📋 MODO FORMAL - Fluxo Completo
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
    
    # Pedidos de Compra
    path('pedidos/', views.pedido_list, name='pedido_list'),
    path('pedidos/<int:pk>/', views.pedido_detail, name='pedido_detail'),
    path('pedidos/gerar/<int:cotacao_pk>/', views.pedido_gerar, name='pedido_gerar'),
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
    path('recebimentos/<int:recebimento_pk>/faturar/', views_simples.faturar_recebimento, name='faturar_recebimento'),
    
    # Cotações Inteligentes (busca automática de fornecedores)
    path('cotacoes-inteligentes/', cotacao_list, name='cotacao_inteligente_list'),
    path('cotacoes-inteligentes/nova/passo-1/', cotacao_create_step1, name='cotacao_create_step1'),
    path('cotacoes-inteligentes/nova/passo-2/', cotacao_create_step2, name='cotacao_create_step2'),
    path('cotacoes-inteligentes/<int:pk>/', cotacao_detail, name='cotacao_inteligente_detail'),
    path('cotacoes-inteligentes/<int:cotacao_pk>/item/<int:item_pk>/proposta/', proposta_create, name='proposta_inteligente_create'),
    path('cotacoes-inteligentes/proposta/<int:proposta_pk>/selecionar/', proposta_selecionar, name='proposta_inteligente_selecionar'),
    path('produtos/<int:produto_pk>/historico-precos/', historico_precos, name='historico_precos'),
    path('historico-precos/', historico_precos_list, name='historico_precos_list'),
    
    # API
    path('api/produto/<int:produto_id>/estoque/', views.get_produto_estoque, name='get_produto_estoque'),
    path('api/produto/<int:produto_id>/unidades/', views.get_produto_unidades, name='get_produto_unidades'),
    path('api/empresa/unidades/', views.get_empresa_unidades, name='get_empresa_unidades'),
    path('dashboard-compras/', dashboard_compras, name='dashboard_compras'),
    path('cotacoes/teste-template/',
         lambda request: __import__('compras.views_template_teste').views_template_teste.template_teste(request),
         name='cotacao_teste_template'),
    
    # Relatórios
    path('relatorios/', views.relatorio_compras_simples, name='relatorio_compras_simples'),
    path('relatorios/pdf/', views.relatorio_compras_simples_pdf, name='relatorio_compras_simples_pdf'),
    path('relatorios/geral/', views.relatorio_compras_geral, name='relatorio_compras_geral'),
    path('relatorios/pedidos-pendentes/', views.relatorio_pedidos_pendentes, name='relatorio_pedidos_pendentes'),
    path('relatorios/compras/', views.relatorio_compras, name='relatorio_compras'),
]
