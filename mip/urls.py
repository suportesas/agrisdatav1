from django.urls import path
from . import views

app_name = 'mip'

urlpatterns = [
    # Estágios de Desenvolvimento
    path('estagios/', views.estagio_list, name='estagio_list'),
    path('estagios/novo/', views.estagio_create, name='estagio_create'),
    path('estagios/<int:pk>/editar/', views.estagio_update, name='estagio_update'),
    path('estagios/<int:pk>/excluir/', views.estagio_delete, name='estagio_delete'),
    path('estagios/cadastro-lote/', views.estagio_cadastro_em_lote, name='estagio_cadastro_em_lote'),

    # Monitoramentos MIP
    path('monitoramento/', views.monitoramento_mip_list, name='monitoramento_mip_list'),
    path('monitoramento/novo/', views.monitoramento_mip_create, name='monitoramento_mip_create'),
    path('monitoramento/<int:pk>/', views.monitoramento_mip_detail, name='monitoramento_mip_detail'),
    path('monitoramento/<int:pk>/pdf/', views.monitoramento_mip_pdf, name='monitoramento_mip_pdf'),
    path('monitoramento/<int:pk>/adicionar-praga/', views.monitoramento_mip_add_praga, name='monitoramento_mip_add_praga'),
    path('monitoramento/praga/<int:pk>/', views.monitoramento_mip_praga_detail, name='monitoramento_mip_praga_detail'),
    path('monitoramento/praga/<int:pk>/editar/', views.monitoramento_mip_praga_edit, name='monitoramento_mip_praga_edit'),
    path('monitoramento/praga/<int:pk>/excluir/', views.monitoramento_mip_praga_delete, name='monitoramento_mip_praga_delete'),
    path('monitoramento/praga/<int:pk>/adicionar-ponto/', views.monitoramento_mip_add_ponto, name='monitoramento_mip_add_ponto'),

    # AJAX endpoints
    path('ajax/estagios-praga/', views.ajax_get_estagios_praga, name='ajax_get_estagios_praga'),
    path('ajax/pragas-cultura/', views.ajax_get_pragas_cultura, name='ajax_get_pragas_cultura'),
    path('ajax/calcular-incidencia/', views.ajax_calcular_incidencia, name='ajax_calcular_incidencia'),
    path('ajax/adicionar-estagio/', views.ajax_adicionar_estagio, name='ajax_adicionar_estagio'),
    path('ajax/carregar-estagios/', views.ajax_carregar_estagios, name='ajax_carregar_estagios'),
    path('ajax/deletar-estagio/<int:pk>/', views.ajax_deletar_estagio, name='ajax_deletar_estagio'),
    path('ajax/buscar-talhoes/', views.ajax_buscar_talhoes, name='ajax_buscar_talhoes'),
    path('ajax/talhao-info/<int:talhao_id>/', views.ajax_talhao_info, name='ajax_talhao_info'),
]
