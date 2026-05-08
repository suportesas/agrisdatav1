"""URLs do Portal do Motorista — montadas em /portal/motorista/ no core/urls.py"""
from django.urls import path
from . import views_portal_motorista

app_name = 'portal_motorista'

urlpatterns = [
    path('login/', views_portal_motorista.motorista_login, name='login'),
    path('logout/', views_portal_motorista.motorista_logout, name='logout'),
    path('', views_portal_motorista.motorista_home, name='home'),
    path('abastecer/', views_portal_motorista.motorista_abastecimento_novo, name='abastecimento_novo'),
    path('historico/', views_portal_motorista.motorista_historico, name='historico'),
    path('manutencoes/', views_portal_motorista.motorista_manutencao_list, name='manutencao_list'),
    path('solicitar-manutencao/', views_portal_motorista.motorista_solicitar_manutencao, name='solicitar_manutencao'),
    path('manutencao/<int:pk>/concluir/', views_portal_motorista.motorista_manutencao_concluir, name='manutencao_concluir'),
    path('ordens-coleta/', views_portal_motorista.motorista_ordens_coleta, name='ordens_coleta'),
    path('ordens-coleta/<int:pk>/', views_portal_motorista.motorista_ordem_coleta_detail, name='ordem_coleta_detail'),
    path('ordens-coleta/<int:pk>/imprimir/', views_portal_motorista.motorista_ordem_coleta_print, name='ordem_coleta_print'),
    path('ordens-coleta/<int:pk>/carta-temperatura/', views_portal_motorista.motorista_carta_temperatura, name='ordem_coleta_carta_temperatura'),
    path('ordens-coleta/<int:pk>/confirmar/', views_portal_motorista.motorista_confirmar_coleta, name='ordem_coleta_confirmar'),
    path('ordens-coleta/<int:pk>/finalizar/', views_portal_motorista.motorista_finalizar_coleta, name='ordem_coleta_finalizar'),
    path('ordens-coleta/<int:pk>/fotos/', views_portal_motorista.motorista_ordem_coleta_fotos, name='ordem_coleta_fotos'),
]
