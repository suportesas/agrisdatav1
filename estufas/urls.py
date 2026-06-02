from django.urls import path
from . import views

app_name = 'estufas'

urlpatterns = [
    # Estufas
    path('', views.estufa_list, name='estufa_list'),
    path('nova/', views.estufa_create, name='estufa_create'),
    path('<int:pk>/', views.estufa_detail, name='estufa_detail'),
    path('<int:pk>/editar/', views.estufa_update, name='estufa_update'),
    path('<int:pk>/excluir/', views.estufa_delete, name='estufa_delete'),
    path('dashboard/', views.dashboard_estufas, name='dashboard_estufas'),

    # Lotes de Mudas
    path('lotes/', views.lote_muda_list, name='lote_muda_list'),
    path('lotes/novo/', views.lote_muda_create, name='lote_muda_create'),
    path('lotes/<int:pk>/', views.lote_muda_detail, name='lote_muda_detail'),
    path('lotes/<int:pk>/editar/', views.lote_muda_update, name='lote_muda_update'),
    path('lotes/<int:pk>/avancar-status/', views.lote_muda_avancar_status, name='lote_muda_avancar_status'),

    # Inline — perdas
    path('lotes/<int:lote_pk>/perdas/nova/', views.perda_estufa_create, name='perda_estufa_create'),
    path('lotes/<int:lote_pk>/perdas/<int:pk>/excluir/', views.perda_estufa_delete, name='perda_estufa_delete'),

    # Inline — aplicações
    path('lotes/<int:lote_pk>/aplicacoes/nova/', views.aplicacao_estufa_create, name='aplicacao_estufa_create'),
    path('lotes/<int:lote_pk>/aplicacoes/<int:pk>/excluir/', views.aplicacao_estufa_delete, name='aplicacao_estufa_delete'),

    # Inline — monitoramentos
    path('lotes/<int:lote_pk>/monitoramentos/novo/', views.monitoramento_estufa_create, name='monitoramento_estufa_create'),
    path('lotes/<int:lote_pk>/monitoramentos/<int:pk>/excluir/', views.monitoramento_estufa_delete, name='monitoramento_estufa_delete'),

    # Transplantios
    path('transplantios/', views.transplantio_list, name='transplantio_list'),
    path('transplantios/novo/', views.transplantio_create, name='transplantio_create'),
    path('transplantios/<int:pk>/', views.transplantio_detail, name='transplantio_detail'),

    # Replantios
    path('replantios/', views.replantio_list, name='replantio_list'),
    path('replantios/novo/', views.replantio_create, name='replantio_create'),
    path('replantios/<int:pk>/', views.replantio_detail, name='replantio_detail'),
]
