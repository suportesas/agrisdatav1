from django.urls import path

from . import views

app_name = 'etiquetas_avulsas'

urlpatterns = [
    path('lotes/', views.lote_list, name='lote_list'),
    path('lotes/novo/', views.lote_create, name='lote_create'),
    path('lotes/<int:pk>/', views.lote_detail, name='lote_detail'),
    path('lotes/<int:pk>/imprimir/', views.lote_etiquetas_pdf, name='lote_etiquetas_pdf'),
    path('etiquetas/<int:pk>/pdf/', views.etiqueta_pdf_single, name='etiqueta_pdf_single'),
    path('etiquetas/<int:pk>/editar/', views.etiqueta_update, name='etiqueta_update'),
    path('etiquetas/<int:pk>/cancelar/', views.etiqueta_cancelar, name='etiqueta_cancelar'),
]
