from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'portal_cliente'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='portal/login.html',
        next_page='/portal/cliente/',
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/portal/cliente/login/'), name='logout'),
    path('', views.portal_dashboard, name='dashboard'),
    path('financeiro/', views.portal_financeiro_list, name='financeiro_list'),
    path('financeiro/<int:pk>/', views.portal_financeiro_detail, name='financeiro_detail'),
    path('documentos/', views.portal_documentos_list, name='documentos_list'),
]
