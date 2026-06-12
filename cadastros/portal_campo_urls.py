"""URLs do Portal do Campo — montadas em /portal/campo/ no core/urls.py"""
from django.urls import path
from . import views_portal_campo

app_name = 'portal_campo'

urlpatterns = [
    path('login/', views_portal_campo.campo_login, name='login'),
    path('logout/', views_portal_campo.campo_logout, name='logout'),
    path('', views_portal_campo.campo_home, name='home'),
    path('os/<int:pk>/', views_portal_campo.campo_os_detail, name='os_detail'),
    path('os/<int:pk>/iniciar/', views_portal_campo.campo_os_iniciar, name='os_iniciar'),
    path('os/<int:pk>/executar/', views_portal_campo.campo_os_executar, name='os_executar'),
    path('os/<int:pk>/concluir/', views_portal_campo.campo_os_concluir, name='os_concluir'),
    # AJAX CRUD — itens da execução da OS
    path('os/<int:pk>/worker/add/',               views_portal_campo.ajax_add_worker,  name='ajax_add_worker'),
    path('os/<int:pk>/worker/<int:item_pk>/del/',  views_portal_campo.ajax_del_worker,  name='ajax_del_worker'),
    path('os/<int:pk>/maquina/add/',               views_portal_campo.ajax_add_maquina, name='ajax_add_maquina'),
    path('os/<int:pk>/maquina/<int:item_pk>/del/', views_portal_campo.ajax_del_maquina, name='ajax_del_maquina'),
    path('os/<int:pk>/insumo/add/',                views_portal_campo.ajax_add_insumo,  name='ajax_add_insumo'),
    path('os/<int:pk>/insumo/<int:item_pk>/del/',  views_portal_campo.ajax_del_insumo,  name='ajax_del_insumo'),

    path('push/subscribe/', views_portal_campo.campo_push_subscribe, name='push_subscribe'),
    path('sw.js', views_portal_campo.campo_sw_js, name='sw_js'),
    path('sync/', views_portal_campo.campo_sync_offline, name='sync_offline'),
]
