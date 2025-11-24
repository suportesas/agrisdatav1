from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from core import settings
from usuarios import views as user_views
from django.contrib.auth import views as auth_views


def root_redirect(request):
    """Redireciona a raiz do site"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('login')


urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),
    
    # Raiz do site
    path('', root_redirect, name='root_redirect'),
    
    # Login/Logout (fora do namespace para facilitar)
    path('login/', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    
    # Apps principais (COM namespace)
    path('dashboard/', include(('dashboard.urls', 'dashboard'))),
    path('empresas/', include(('empresas.urls', 'empresas'))),
    path('usuarios/', include(('usuarios.urls', 'usuarios'))),
    path('cadastros/', include(('cadastros.urls', 'cadastros'))),
    
    # Recuperação de senha
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset_form.html'
         ), 
         name='password_reset'),
    
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='usuarios/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='usuarios/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='usuarios/password_reset_complete.html'
         ), 
         name='password_reset_complete'),




 # ============================================
    # APPS AGRÍCOLAS (criar depois)
    # ============================================
    # path('fazendas/', include(('fazendas.urls', 'fazendas'))),
    # path('talhoes/', include(('talhoes.urls', 'talhoes'))),
    # path('produtos/', include(('produtos.urls', 'produtos'))),
    # path('plantio/', include(('plantio.urls', 'plantio'))),
    # path('colheita/', include(('colheita.urls', 'colheita'))),
    # path('estoque/', include(('estoque.urls', 'estoque'))),
    # path('vendas/', include(('vendas.urls', 'vendas'))),
    # path('clientes/', include(('clientes.urls', 'clientes'))),
    # path('fornecedores/', include(('fornecedores.urls', 'fornecedores'))),
    # path('portaria/', include(('portaria.urls', 'portaria'))),
    # path('logistica/', include(('logistica.urls', 'logistica'))),
    # path('financeiro/', include(('financeiro.urls', 'financeiro'))),
    
    # ============================================
    # API REST
    # ============================================
    path('api/', include([
        path('auth/', include('rest_framework.urls')),
        # path('v1/', include('api.urls')),  # Criar depois
    ])),

]

# ============================================
# SERVIR ARQUIVOS ESTÁTICOS E MEDIA (DESENVOLVIMENTO)
# ============================================
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar (instalar: pip install django-debug-toolbar)
    # import debug_toolbar
    # urlpatterns = [
    #     path('__debug__/', include(debug_toolbar.urls)),
    # ] + urlpatterns


# Handler de erros customizados (criar depois)
# handler404 = 'core.views.error_404'
# handler500 = 'core.views.error_500'
# handler403 = 'core.views.error_403'
# handler400 = 'core.views.error_400'