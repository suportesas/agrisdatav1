"""
URLs do módulo Motorista
Rotas CRUD completas para motoristas e documentos
"""

from django.urls import path
from . import views_motorista

app_name = 'cadastros'

urlpatterns = [
    # Motoristas
    path('motoristas/', views_motorista.motorista_list, name='motorista_list'),
    path('motoristas/criar/', views_motorista.motorista_create, name='motorista_create'),
    path('motoristas/<int:pk>/', views_motorista.motorista_detail, name='motorista_detail'),
    path('motoristas/<int:pk>/editar/', views_motorista.motorista_update, name='motorista_update'),
    path('motoristas/<int:pk>/deletar/', views_motorista.motorista_delete, name='motorista_delete'),
    
    # Documentos do Motorista
    path('motoristas/<int:motorista_pk>/documentos/criar/', views_motorista.motorista_documento_create, name='motorista_documento_create'),
    path('motoristas/<int:motorista_pk>/documentos/<int:documento_pk>/deletar/', views_motorista.motorista_documento_delete, name='motorista_documento_delete'),
    
    # API
    path('api/buscar-cep-motorista/', views_motorista.buscar_cep_motorista, name='buscar_cep_motorista'),
]
