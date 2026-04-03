"""
URLs principais do ERP Agrícola SaaS
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from usuarios import views as user_views
from compras import views as compras_views


def root_redirect(request):
    """Redireciona a raiz do site dependendo da autenticação"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('login')


# Customização do Admin
admin.site.site_header = "ERP Agrícola - Administração"
admin.site.site_title = "ERP Agrícola Admin"
admin.site.index_title = "Painel de Administração"


urlpatterns = [
    # ============================================
    # ADMIN DJANGO
    # ============================================
    path('admin/', admin.site.urls),
    
    # ============================================
    # RAIZ DO SITE
    # ============================================
    path('', root_redirect, name='root_redirect'),
    
    # ============================================
    # AUTENTICAÇÃO (sem namespace para facilitar)
    # ============================================
    path('login/', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    
    # ============================================
    # RECUPERAÇÃO DE SENHA
    # ============================================
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='usuarios/password_reset_form.html',
             email_template_name='usuarios/password_reset_email.html',
             subject_template_name='usuarios/password_reset_subject.txt',
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
    # ATALHOS GLOBAIS
    # ============================================
    path('compras/recebimentos/entrada-direta/', compras_views.entrada_direta_nf, name='entrada_direta_nf'),
    
    # ============================================
    # CONFIGURAÇÕES DO SISTEMA
    # ============================================
    path('configuracoes/', include([
        path('sistema/', user_views.configuracao_sistema, name='configuracao_sistema'),
    ])),

    # ============================================
    # APPS PRINCIPAIS (COM NAMESPACE)
    # ============================================
    path('dashboard/', include(('dashboard.urls', 'dashboard'))),
    path('dashboard-executivo/', include(('metricas.urls', 'metricas'))),
    path('empresas/', include(('empresas.urls', 'empresas'))),
    path('usuarios/', include(('usuarios.urls', 'usuarios'))),
    path('cadastros/', include(('cadastros.urls', 'cadastros'))),
    path('patrimonio/', include(('patrimonio.urls', 'patrimonio'))),
    path('produtos/', include(('produtos.urls', 'produtos'))),
    path('estoque/', include(('estoque.urls', 'estoque'))),
    path('compras/', include(('compras.urls', 'compras'))),
    path('portal/fornecedor/', include(('compras.portal_fornecedor_urls', 'portal_fornecedor'))),
    path('financeiro/', include(('financeiro.urls', 'financeiro'))),
    
    # ============================================
    # API REST
    # ============================================
    path('api/', include([
        path('auth/', include('rest_framework.urls')),
    ])),
]

# ============================================
# SERVIR ARQUIVOS ESTÁTICOS E MEDIA (DESENVOLVIMENTO)
# ============================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Endpoint para coleta de logs do console (apenas em DEBUG, usado por testes E2E)
    try:
        from core import e2e_views
        urlpatterns += [ path('__e2e_log__', e2e_views.e2e_log) ]
    except Exception:
        # Segurança: não atrapalha se o handler não estiver presente
        pass