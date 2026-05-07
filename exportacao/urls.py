from django.urls import path
from . import views

app_name = 'exportacao'

urlpatterns = [
    path('solicitacoes/', views.solicitacao_booking_list, name='solicitacao_booking_list'),
    path('solicitacoes/nova/', views.solicitacao_booking_create, name='solicitacao_booking_create'),
    path('solicitacoes/<int:pk>/', views.solicitacao_booking_detail, name='solicitacao_booking_detail'),
    path('solicitacoes/<int:pk>/editar/', views.solicitacao_booking_update, name='solicitacao_booking_update'),
    path('solicitacoes/<int:pk>/pdf/', views.solicitacao_booking_pdf, name='solicitacao_booking_pdf'),

    path('bookings/', views.booking_list, name='booking_list'),
    path('bookings/novo/', views.booking_create, name='booking_create'),
    path('bookings/<int:pk>/', views.booking_detail, name='booking_detail'),
    path('bookings/<int:pk>/editar/', views.booking_update, name='booking_update'),

    path('bookings/<int:booking_pk>/containers/', views.container_list, name='booking_container_list'),
    path('containers/', views.container_list, name='container_list'),
    path('bookings/<int:booking_pk>/containers/novo/', views.container_create, name='booking_container_create'),
    path('containers/<int:pk>/editar/', views.container_update, name='container_update'),

    path('ordens-coleta/', views.ordem_coleta_list, name='ordem_coleta_list'),
    path('ordens-coleta/nova/', views.ordem_coleta_create, name='ordem_coleta_create'),
    path('ordens-coleta/<int:pk>/editar/', views.ordem_coleta_update, name='ordem_coleta_update'),

    path('ajax/cultura/<int:pk>/exportacao/', views.ajax_cultura_exportacao, name='ajax_cultura_exportacao'),
    path('ajax/solicitacao/<int:pk>/preview/', views.ajax_solicitacao_preview, name='ajax_solicitacao_preview'),
]
