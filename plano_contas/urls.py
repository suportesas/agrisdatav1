from django.urls import path
from . import views

app_name = 'plano_contas'

urlpatterns = [
    # ContaContabil
    path('', views.conta_list, name='conta_list'),
    path('arvore/', views.conta_arvore, name='conta_arvore'),
    path('nova/', views.conta_create, name='conta_create'),
    path('<int:pk>/', views.conta_detail, name='conta_detail'),
    path('<int:pk>/editar/', views.conta_edit, name='conta_edit'),
    path('<int:pk>/toggle/', views.conta_toggle_ativo, name='conta_toggle'),
    path('autocomplete/', views.conta_autocomplete, name='conta_autocomplete'),
    path('balancete/', views.balancete, name='balancete'),

    # CentroCusto
    path('centros/', views.centro_list, name='centro_list'),
    path('centros/novo/', views.centro_create, name='centro_create'),
    path('centros/<int:pk>/', views.centro_detail, name='centro_detail'),
    path('centros/<int:pk>/editar/', views.centro_edit, name='centro_edit'),
    path('centros/<int:pk>/toggle/', views.centro_toggle_ativo, name='centro_toggle'),
    path('centros/autocomplete/', views.centro_autocomplete, name='centro_autocomplete'),
]
