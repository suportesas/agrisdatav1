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
]
