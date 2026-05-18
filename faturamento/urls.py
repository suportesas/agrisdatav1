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
    path('notas-fiscais/<int:pk>/cancelar/', views.nota_fiscal_cancelar, name='nota_fiscal_cancelar'),
    path('notas-fiscais/<int:pk>/pdf/', views.nota_fiscal_pdf, name='nota_fiscal_pdf'),

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

    # AJAX
    path('ajax/produto/<int:pk>/', views.ajax_produto_detail, name='ajax_produto_detail'),
    path('ajax/booking/<int:pk>/', views.ajax_booking_preview, name='ajax_booking_preview'),
    path('ajax/cotacao-bcb/', views.ajax_cotacao_bcb, name='ajax_cotacao_bcb'),
]
