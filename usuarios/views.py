"""
Views do app usuarios - CÓDIGO CORRIGIDO
Gerenciamento de usuários, autenticação e auditoria
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import login, logout, update_session_auth_hash
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache

from .models import Usuario, LoginRegistro, PerfilUsuario
from .forms import (
    UsuarioCreateForm, UsuarioUpdateForm, LoginForm,
    AlterarSenhaForm, PerfilUsuarioForm
)


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def is_admin(user):
    """Verifica se usuário é admin ou staff"""
    return user.is_superuser or user.is_staff or (hasattr(user, 'tipo') and user.tipo == 'ADMIN')


def get_client_ip(request):
    """Obtém o IP real do cliente considerando proxies"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Obtém o user agent do navegador"""
    return request.META.get('HTTP_USER_AGENT', '')[:500]


# ============================================
# AUTENTICAÇÃO
# ============================================

def login_view(request):
    """
    View de login customizada com validação de empresa
    Registra o login no banco de dados para auditoria
    Proteção contra força bruta com rate limiting
    """
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    # ✅ PROTEÇÃO CONTRA FORÇA BRUTA
    ip = get_client_ip(request)
    cache_key = f'login_attempts_{ip}'
    tentativas = cache.get(cache_key, 0)
    
    # Bloqueia após 5 tentativas por 15 minutos
    if tentativas >= 5:
        messages.error(
            request, 
            '🔒 Muitas tentativas de login. Tente novamente em 15 minutos.'
        )
        return render(request, 'usuarios/login.html', {
            'form': LoginForm(),
            'bloqueado': True
        })

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            
            # ✅ VALIDAÇÕES DE EMPRESA
            
            # 1. Verifica se usuário tem empresa (exceto superusuário)
            if not user.is_superuser and not user.empresa:
                messages.error(
                    request,
                    '⚠️ Seu usuário não está vinculado a nenhuma empresa. '
                    'Entre em contato com o administrador.'
                )
                # Registra tentativa
                LoginRegistro.objects.create(
                    usuario=user,
                    empresa=None,
                    ip_address=ip,
                    user_agent=get_user_agent(request),
                    sucesso=False
                )
                return redirect('login')
            
            # 2. Verifica se empresa está bloqueada
            if user.empresa and user.empresa.bloqueada:
                mensagem = f'🔒 A empresa {user.empresa.nome} está bloqueada.'
                if user.empresa.motivo_bloqueio:
                    mensagem += f' Motivo: {user.empresa.motivo_bloqueio}'
                mensagem += ' Entre em contato com o suporte.'
                
                LoginRegistro.objects.create(
                    usuario=user,
                    empresa=user.empresa,
                    ip_address=ip,
                    user_agent=get_user_agent(request),
                    sucesso=False
                )
                
                messages.error(request, mensagem)
                return redirect('login')
            
            # 3. Verifica se empresa está inativa
            if user.empresa and not user.empresa.ativa:
                messages.error(
                    request,
                    f'⚠️ A empresa {user.empresa.nome} está inativa. '
                    'Entre em contato com o suporte.'
                )
                LoginRegistro.objects.create(
                    usuario=user,
                    empresa=user.empresa,
                    ip_address=ip,
                    user_agent=get_user_agent(request),
                    sucesso=False
                )
                return redirect('login')
            
            # 4. Verifica se plano expirou
            if user.empresa and user.empresa.data_expiracao:
                hoje = timezone.now().date()
                if hoje > user.empresa.data_expiracao:
                    messages.error(
                        request,
                        f'⏰ O plano da empresa {user.empresa.nome} expirou em '
                        f'{user.empresa.data_expiracao.strftime("%d/%m/%Y")}. '
                        'Renove sua assinatura para continuar.'
                    )
                    LoginRegistro.objects.create(
                        usuario=user,
                        empresa=user.empresa,
                        ip_address=ip,
                        user_agent=get_user_agent(request),
                        sucesso=False
                    )
                    return redirect('login')
            
            # ✅ LOGIN BEM-SUCEDIDO
            
            # Limpa tentativas de login após sucesso
            cache.delete(cache_key)
            
            # Faz login
            login(request, user)
            
            # Registra o login para auditoria
            LoginRegistro.objects.create(
                usuario=user,
                empresa=user.empresa if user.empresa else None,
                ip_address=ip,
                user_agent=get_user_agent(request),
                sucesso=True
            )
            
            # Mensagem de boas-vindas
            nome = user.get_full_name() or user.username
            messages.success(request, f'✅ Bem-vindo(a), {nome}!')
            
            # Redireciona
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:index')
        
        else:
            # ✅ LOGIN FALHOU - Incrementa tentativas
            tentativas += 1
            cache.set(cache_key, tentativas, 900)  # 15 minutos
            
            restantes = 5 - tentativas
            if restantes > 0:
                messages.error(
                    request, 
                    f'❌ Usuário ou senha incorretos. '
                    f'Você tem mais {restantes} tentativa(s).'
                )
            else:
                messages.error(
                    request,
                    '🔒 Conta bloqueada temporariamente por excesso de tentativas.'
                )
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'title': 'Login - ERP Agrícola'
    }
    return render(request, 'usuarios/login.html', context)


@login_required
def logout_view(request):
    """View de logout"""
    username = request.user.get_full_name() or request.user.username
    logout(request)
    messages.info(request, f"👋 Até logo, {username}! Sessão encerrada com sucesso.")
    return redirect('login')


# ============================================
# CRUD DE USUÁRIOS
# ============================================

@login_required
@user_passes_test(is_admin)
def usuario_list(request):
    """
    Lista todos os usuários com filtros e busca
    Usuários comuns veem apenas usuários da sua empresa
    Superusuários veem todos
    """
    usuarios = Usuario.objects.select_related('empresa').all()
    
    # Filtro por empresa se não for superusuário
    if not request.user.is_superuser:
        if request.user.empresa:
            usuarios = usuarios.filter(empresa=request.user.empresa)
        else:
            usuarios = Usuario.objects.none()

    # Busca por texto
    q = request.GET.get('q', '').strip()
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(telefone__icontains=q) |
            Q(cpf__icontains=q)
        )
    
    # Filtro por tipo
    tipo = request.GET.get('tipo', '')
    if tipo:
        usuarios = usuarios.filter(tipo=tipo)
    
    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'ativos':
        usuarios = usuarios.filter(is_active=True)
    elif status == 'inativos':
        usuarios = usuarios.filter(is_active=False)

    # Ordenação
    ordem = request.GET.get('ordem', 'username')
    if ordem:
        usuarios = usuarios.order_by(ordem)

    # Paginação
    paginator = Paginator(usuarios, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Resposta AJAX para atualização parcial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string(
            'usuarios/_usuario_table.html',
            {'page_obj': page_obj},
            request=request
        )
        return JsonResponse({'html': html})

    context = {
        'page_obj': page_obj,
        'total': usuarios.count(),
        'tipos': Usuario.TIPO_USUARIO,
        'title': 'Usuários'
    }
    return render(request, 'usuarios/usuario_list.html', context)


@login_required
@user_passes_test(is_admin)
def usuario_create(request):
    """
    Cria novo usuário
    Superusuário pode escolher qualquer empresa
    Usuário comum só pode criar na sua empresa
    """
    # ✅ Verifica se empresa pode adicionar mais usuários
    if not request.user.is_superuser:
        if request.user.empresa and not request.user.empresa.pode_adicionar_usuario():
            messages.error(
                request,
                f'❌ Limite de usuários atingido! '
                f'Seu plano permite até {request.user.empresa.limite_usuarios} usuários. '
                f'Faça upgrade para adicionar mais.'
            )
            return redirect('usuarios:usuario_list')
    
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            usuario = form.save(commit=False)
            
            # Se não for superusuário, força empresa do usuário logado
            if not request.user.is_superuser:
                usuario.empresa = request.user.empresa
            
            usuario.save()
            
            # Cria perfil do usuário
            PerfilUsuario.objects.get_or_create(usuario=usuario)
            
            messages.success(
                request,
                f'✅ Usuário {usuario.get_full_name()} criado com sucesso!'
            )
            return redirect('usuarios:usuario_list')
    else:
        form = UsuarioCreateForm(user=request.user)
    
    context = {
        'form': form,
        'action': 'Criar',
        'title': 'Novo Usuário'
    }
    return render(request, 'usuarios/usuario_form.html', context)


@login_required
@user_passes_test(is_admin)
def usuario_update(request, pk):
    """
    Atualiza usuário existente
    Valida se usuário tem permissão para editar
    """
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Valida permissão: apenas superusuário ou usuário da mesma empresa
    if not request.user.is_superuser:
        if not request.user.empresa or usuario.empresa != request.user.empresa:
            messages.error(request, '❌ Você não tem permissão para editar este usuário.')
            return redirect('usuarios:usuario_list')
    
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, request.FILES, instance=usuario, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f'✅ Usuário {usuario.get_full_name()} atualizado com sucesso!'
            )
            return redirect('usuarios:usuario_list')
    else:
        form = UsuarioUpdateForm(instance=usuario, user=request.user)
    
    context = {
        'form': form,
        'usuario': usuario,
        'action': 'Editar',
        'title': f'Editar Usuário - {usuario.get_full_name()}'
    }
    return render(request, 'usuarios/usuario_form.html', context)


@login_required
@user_passes_test(is_admin)
def usuario_delete(request, pk):
    """
    Exclui usuário (com confirmação)
    Não permite excluir o próprio usuário logado
    """
    usuario = get_object_or_404(Usuario, pk=pk)
    
    # Valida permissão
    if not request.user.is_superuser:
        if not request.user.empresa or usuario.empresa != request.user.empresa:
            messages.error(request, '❌ Você não tem permissão para excluir este usuário.')
            return redirect('usuarios:usuario_list')
    
    # Não permite excluir a si mesmo
    if usuario.id == request.user.id:
        messages.error(request, '❌ Você não pode excluir seu próprio usuário!')
        return redirect('usuarios:usuario_list')
    
    if request.method == 'POST':
        nome = usuario.get_full_name()
        usuario.delete()
        messages.success(request, f'🗑️ Usuário {nome} excluído com sucesso!')
        return redirect('usuarios:usuario_list')
    
    context = {
        'usuario': usuario,
        'title': f'Excluir Usuário - {usuario.get_full_name()}'
    }
    return render(request, 'usuarios/usuario_confirm_delete.html', context)


# ============================================
# PERFIL DO USUÁRIO
# ============================================

@login_required
def meu_perfil(request):
    """Visualiza e edita perfil do usuário logado"""
    usuario = request.user
    
    # Garante que perfil existe
    perfil, created = PerfilUsuario.objects.get_or_create(usuario=usuario)
    
    if request.method == 'POST':
        form_usuario = UsuarioUpdateForm(request.POST, request.FILES, instance=usuario, user=usuario)
        form_perfil = PerfilUsuarioForm(request.POST, instance=perfil)
        
        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            form_perfil.save()
            messages.success(request, '✅ Perfil atualizado com sucesso!')
            return redirect('usuarios:meu_perfil')
    else:
        form_usuario = UsuarioUpdateForm(instance=usuario, user=usuario)
        form_perfil = PerfilUsuarioForm(instance=perfil)
    
    context = {
        'form_usuario': form_usuario,
        'form_perfil': form_perfil,
        'title': 'Meu Perfil'
    }
    return render(request, 'usuarios/meu_perfil.html', context)


@login_required
def alterar_senha(request):
    """Permite usuário alterar sua própria senha"""
    if request.method == 'POST':
        form = AlterarSenhaForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Atualiza sessão para não deslogar
            update_session_auth_hash(request, request.user)
            messages.success(request, '✅ Senha alterada com sucesso!')
            return redirect('usuarios:meu_perfil')
    else:
        form = AlterarSenhaForm(request.user)
    
    context = {
        'form': form,
        'title': 'Alterar Senha'
    }
    return render(request, 'usuarios/alterar_senha.html', context)


# ============================================
# REGISTROS DE LOGIN (AUDITORIA)
# ============================================

@login_required
@user_passes_test(is_admin)
def login_registros(request):
    """
    Exibe histórico de logins no sistema
    Filtrado por empresa se não for superusuário
    """
    registros = LoginRegistro.objects.select_related('usuario', 'empresa').all()
    
    # Filtro por empresa
    if not request.user.is_superuser:
        if request.user.empresa:
            registros = registros.filter(empresa=request.user.empresa)
        else:
            registros = LoginRegistro.objects.none()
    
    # Filtro por empresa (para superusuário)
    empresa_id = request.GET.get('empresa', '')
    if empresa_id:
        registros = registros.filter(empresa_id=empresa_id)
    
    # Filtro por usuário
    usuario_id = request.GET.get('usuario', '')
    if usuario_id:
        registros = registros.filter(usuario_id=usuario_id)
    
    # Filtro por período
    periodo = request.GET.get('periodo', '')
    hoje = timezone.now().date()
    
    if periodo == 'hoje':
        registros = registros.filter(data_login__date=hoje)
    elif periodo == 'semana':
        inicio_semana = hoje - timedelta(days=7)
        registros = registros.filter(data_login__date__gte=inicio_semana)
    elif periodo == 'mes':
        inicio_mes = hoje - timedelta(days=30)
        registros = registros.filter(data_login__date__gte=inicio_mes)
    
    # Filtro por data customizada
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    if data_inicio:
        registros = registros.filter(data_login__date__gte=data_inicio)
    if data_fim:
        registros = registros.filter(data_login__date__lte=data_fim)
    
    # Filtro por sucesso
    sucesso = request.GET.get('sucesso', '')
    if sucesso == 'sim':
        registros = registros.filter(sucesso=True)
    elif sucesso == 'nao':
        registros = registros.filter(sucesso=False)
    
    # Estatísticas
    total_logins = registros.count()
    logins_sucesso = registros.filter(sucesso=True).count()
    logins_falha = registros.filter(sucesso=False).count()
    
    # Paginação
    paginator = Paginator(registros, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para os filtros
    from empresas.models import Empresa
    empresas = Empresa.objects.all() if request.user.is_superuser else []
    usuarios = Usuario.objects.filter(empresa=request.user.empresa) if not request.user.is_superuser else Usuario.objects.all()
    
    context = {
        'page_obj': page_obj,
        'empresas': empresas,
        'usuarios': usuarios,
        'total_logins': total_logins,
        'logins_sucesso': logins_sucesso,
        'logins_falha': logins_falha,
        'title': 'Registros de Login'
    }
    
    return render(request, 'usuarios/login_registros.html', context)

