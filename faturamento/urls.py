from django.urls import path
from . import views

app_name = 'faturamento'

urlpatterns = [
    # Dashboard
    path('', views.faturamento_dashboard, name='dashboard'),

    # Nota Fiscal (Mercado Interno)
    path('notas-fiscais/', views.nota_fiscal_list, name='nota_fiscal_list'),
    path('notas-fiscais/nova/', views.nota_fiscal_create, name='nota_fiscal_create'),
    path('notas-fiscais/<int:pk>/', views.nota_fiscal_detail, name='nota_fiscal_detail'),
    path('notas-fiscais/<int:pk>/editar/', views.nota_fiscal_update, name='nota_fiscal_update'),
    path('notas-fiscais/<int:pk>/emitir/', views.nota_fiscal_emitir, name='nota_fiscal_emitir'),
    path('notas-fiscais/<int:pk>/emitir/ajax/', views.nota_fiscal_emitir_ajax, name='nota_fiscal_emitir_ajax'),
    path('notas-fiscais/<int:pk>/cancelar/', views.nota_fiscal_cancelar, name='nota_fiscal_cancelar'),
    path('notas-fiscais/<int:pk>/consultar/', views.nota_fiscal_consultar, name='nota_fiscal_consultar'),
    path('notas-fiscais/<int:pk>/pdf/', views.nota_fiscal_pdf, name='nota_fiscal_pdf'),
    path('notas-fiscais/<int:pk>/danfe/', views.nota_fiscal_danfe, name='nota_fiscal_danfe'),

    # Invoice de Exportação
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/nova/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/editar/', views.invoice_update, name='invoice_update'),
    path('invoices/<int:pk>/emitir/', views.invoice_emitir, name='invoice_emitir'),
    path('invoices/<int:pk>/cancelar/', views.invoice_cancelar, name='invoice_cancelar'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),

    # Packing List
    path('packing-lists/', views.packing_list_list, name='packing_list_list'),
    path('packing-lists/nova/', views.packing_list_create, name='packing_list_create'),
    path('packing-lists/<int:pk>/', views.packing_list_detail, name='packing_list_detail'),
    path('packing-lists/<int:pk>/editar/', views.packing_list_update, name='packing_list_update'),
    path('packing-lists/<int:pk>/emitir/', views.packing_list_emitir, name='packing_list_emitir'),
    path('packing-lists/<int:pk>/pdf/', views.packing_list_pdf, name='packing_list_pdf'),

    # Configuração
    path('configuracao/', views.configuracao_fiscal, name='configuracao'),
    path('configuracao/certificado/', views.certificado_upload, name='certificado_upload'),

    # Webhook IntegraNota
    path('webhook/integranotas/', views.integranotas_webhook, name='integranotas_webhook'),

    # Teste de token IntegraNotas (AJAX)
    path('configuracao/testar-token/', views.integranotas_test_token, name='integranotas_test_token'),

    # CT-e
    path('cte/', views.cte_list, name='cte_list'),
    path('cte/novo/', views.cte_create, name='cte_create'),
    path('cte/<int:pk>/', views.cte_detail, name='cte_detail'),
    path('cte/<int:pk>/editar/', views.cte_update, name='cte_update'),
    path('cte/<int:pk>/emitir/', views.cte_emitir, name='cte_emitir'),
    path('cte/<int:pk>/cancelar/', views.cte_cancelar, name='cte_cancelar'),
    path('cte/<int:pk>/dacte/', views.cte_dacte, name='cte_dacte'),

    # MDF-e
    path('mdfe/', views.mdfe_list, name='mdfe_list'),
    path('mdfe/novo/', views.mdfe_create, name='mdfe_create'),
    path('mdfe/<int:pk>/', views.mdfe_detail, name='mdfe_detail'),
    path('mdfe/<int:pk>/editar/', views.mdfe_update, name='mdfe_update'),
    path('mdfe/<int:pk>/emitir/', views.mdfe_emitir, name='mdfe_emitir'),
    path('mdfe/<int:pk>/encerrar/', views.mdfe_encerrar, name='mdfe_encerrar'),
    path('mdfe/<int:pk>/cancelar/', views.mdfe_cancelar, name='mdfe_cancelar'),
    path('mdfe/<int:pk>/damdfe/', views.mdfe_damdfe, name='mdfe_damdfe'),

    # Documentação IntegraNotas
    path('docs/integranotas/', views.docs_integranotas, name='docs_integranotas'),

    # Histórico de Cotações BCB
    path('cotacoes-bcb/', views.cotacoes_bcb_list, name='cotacoes_bcb_list'),
    path('cotacoes-bcb/buscar-hoje/', views.cotacoes_bcb_buscar_hoje, name='cotacoes_bcb_buscar_hoje'),

    # AJAX
    path('ajax/produto/<int:pk>/', views.ajax_produto_detail, name='ajax_produto_detail'),
    path('ajax/booking/<int:pk>/', views.ajax_booking_preview, name='ajax_booking_preview'),
    path('ajax/cotacao-bcb/', views.ajax_cotacao_bcb, name='ajax_cotacao_bcb'),
]
