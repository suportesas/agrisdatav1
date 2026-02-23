from django.urls import path
from . import views

app_name = 'metricas'

urlpatterns = [
    # Dashboard Executivo
    path('', views.dashboard_executivo, name='dashboard_executivo'),
    
    # Consumo de Recursos
    path('consumo/', views.consumo_recursos_list, name='consumo_lista'),
    path('consumo/<int:empresa_id>/', views.consumo_empresa_detail, name='consumo_detail'),
    
    # Alertas
    path('alertas/', views.alertas_list, name='alertas_lista'),
]
