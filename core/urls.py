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
from core.views_public import (landing_page, recursos_page, sobre_page, planos_page, 
                               faq_page, contato_page, recursos_avancados_page, page_not_found)


def root_redirect(request):
    """Redireciona a raiz do site dependendo da autenticação"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    return redirect('landing_page')


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
    # LANDING PAGE
    # ============================================
    path('landing/', landing_page, name='landing_page'),
    path('recursos/', recursos_page, name='recursos_page'),
    path('sobre/', sobre_page, name='sobre_page'),
    path('planos/', planos_page, name='planos_page'),
    path('faq/', faq_page, name='faq_page'),
    path('contato/', contato_page, name='contato_page'),
    path('recursos-avancados/', recursos_avancados_page, name='recursos_avancados_page'),
    
    # ============================================
    # RAIZ DO SITE
    # ============================================
    path('', root_redirect, name='root_redirect'),
    
    # ============================================
    # AUTENTICAÇÃO (sem namespace para facilitar)
    # ============================================
    path('login/', user_views.login_view, name='login'),
    path('logout/', user_views.logout_view, name='logout'),
    path('auth/', include(('usuarios.supabase_auth.urls', 'supabase_auth'))),
    
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
    path('portal/produtor/', include(('cadastros.portal_produtor_urls', 'portal_produtor'))),
    path('portal/motorista/', include(('frota.portal_motorista_urls', 'portal_motorista'))),
    path('portal/campo/', include(('cadastros.portal_campo_urls', 'portal_campo'))),
    path('financeiro/', include(('financeiro.urls', 'financeiro'))),
    path('plano-contas/', include(('plano_contas.urls', 'plano_contas'))),
    path('bancario/', include(('bancario.urls', 'bancario'))),
    path('adiantamentos/', include(('adiantamentos.urls', 'adiantamentos'))),
    path('energia/', include(('energia.urls', 'energia'))),
    path('exportacao/', include(('exportacao.urls', 'exportacao'))),
    path('faturamento/', include(('faturamento.urls', 'faturamento'))),
    path('vendas/', include(('vendas.urls', 'vendas'))),
    path('portal/cliente/', include(('portal.urls', 'portal_cliente'))),
    path('embalagem/', include(('embalagem.urls', 'embalagem'))),
    path('frota/', include(('frota.urls', 'frota'))),
    path('mip/', include(('mip.urls', 'mip'))),
    path('emprestimos/', include(('emprestimos.urls', 'emprestimos'))),
    path('estufas/', include(('estufas.urls', 'estufas'))),
    path('rh/', include(('rh.urls', 'rh'))),
    path('campo/', include(('operacoes_campo.urls', 'operacoes_campo'))),
    path('drawback/', include(('drawback.urls', 'drawback'))),

    # ============================================
    # API REST
    # ============================================
    path('api/', include([
        path('auth/', include('rest_framework.urls')),
    ])),
    
    # ============================================
    # CATCH-ALL 404 (DEVE SER O ÚLTIMO)
    # ============================================
    path('<path:unknown_path>/', page_not_found, name='page_not_found'),
]

# ============================================
# HANDLER 404
# ============================================
handler404 = 'core.views_public.page_not_found'

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