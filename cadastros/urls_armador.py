"""
URLs para Armador e Navio
Para adicionar em cadastros/urls.py
"""

from django.urls import path
from .views_armador import (
    # Armador
    armador_list, armador_detail, armador_create, armador_update, armador_delete,
    
    # Armador Endereço
    armador_endereco_create, armador_endereco_update, armador_endereco_delete,
    
    # Armador Contato
    armador_contato_create, armador_contato_update, armador_contato_delete,
    
    # Armador Banco
    armador_banco_create, armador_banco_update, armador_banco_delete,
    
    # Navio
    navio_list, navio_detail, navio_create, navio_update, navio_delete,
)

urlpatterns = [
    # ============================================
    # ARMADOR - CRUD
    # ============================================
    
    # Armador List/Create
    path('armadores/', armador_list, name='armador_list'),
    path('armadores/create/', armador_create, name='armador_create'),
    
    # Armador Detail/Update/Delete
    path('armadores/<int:pk>/', armador_detail, name='armador_detail'),
    path('armadores/<int:pk>/edit/', armador_update, name='armador_update'),
    path('armadores/<int:pk>/delete/', armador_delete, name='armador_delete'),
    
    # ============================================
    # ARMADOR ENDEREÇO
    # ============================================
    
    path('armadores/<int:armador_pk>/endereco/create/', 
         armador_endereco_create, name='armador_endereco_create'),
    path('armadores/<int:armador_pk>/endereco/<int:pk>/edit/', 
         armador_endereco_update, name='armador_endereco_update'),
    path('armadores/<int:armador_pk>/endereco/<int:pk>/delete/', 
         armador_endereco_delete, name='armador_endereco_delete'),
    
    # ============================================
    # ARMADOR CONTATO
    # ============================================
    
    path('armadores/<int:armador_pk>/contato/create/', 
         armador_contato_create, name='armador_contato_create'),
    path('armadores/<int:armador_pk>/contato/<int:pk>/edit/', 
         armador_contato_update, name='armador_contato_update'),
    path('armadores/<int:armador_pk>/contato/<int:pk>/delete/', 
         armador_contato_delete, name='armador_contato_delete'),
    
    # ============================================
    # ARMADOR DADO BANCÁRIO
    # ============================================
    
    path('armadores/<int:armador_pk>/banco/create/', 
         armador_banco_create, name='armador_banco_create'),
    path('armadores/<int:armador_pk>/banco/<int:pk>/edit/', 
         armador_banco_update, name='armador_banco_update'),
    path('armadores/<int:armador_pk>/banco/<int:pk>/delete/', 
         armador_banco_delete, name='armador_banco_delete'),
    
    # ============================================
    # NAVIO - CRUD
    # ============================================
    
    # Navio List/Create
    path('navios/', navio_list, name='navio_list'),
    path('navios/create/', navio_create, name='navio_create'),
    
    # Navio Detail/Update/Delete
    path('navios/<int:pk>/', navio_detail, name='navio_detail'),
    path('navios/<int:pk>/edit/', navio_update, name='navio_update'),
    path('navios/<int:pk>/delete/', navio_delete, name='navio_delete'),
]
