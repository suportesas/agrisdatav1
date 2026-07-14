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
from django.db.models import Count, Q
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta
from django.core.cache import cache
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.conf import settings
from django.views.decorators.http import require_POST
import logging
import hashlib
import secrets

from .models import (
    TipoUsuario,
    Usuario,
    LoginRegistro,
    PerfilUsuario,
    LoginAnomalia,
    AlertaSeguranca,
    TrocaSenhaEmergencial,
    get_codigos_tipos_admin_empresa,
)
from .forms import (
    UsuarioCreateForm, UsuarioUpdateForm, LoginForm,
    AlterarSenhaForm, PerfilUsuarioForm, TipoUsuarioForm
)
from .utils_login import (
    get_client_ip, get_user_agent, detectar_anomalias_login,
    notificar_anomalia, criar_alerta, atualizar_grafico_acesso,
    obter_estatisticas_acesso
)

from .models_supabase import SupabaseUsuarioSync

logger = logging.getLogger(__name__)


def _get_supabase_auth():
    try:
        from core.supabase_config import supabase_auth
        return supabase_auth
    except Exception:
        return None


def _sync_usuario_para_supabase(usuario, senha_plana):
    """Sincroniza usuario recem-criado com Supabase Auth e registra bridge local."""
    supabase_auth = _get_supabase_auth()
    if supabase_auth is None:
        return False, 'Supabase indisponível neste ambiente (pacote/configuração ausente).'

    if not usuario.email:
        return False, 'Usuário sem e-mail; não foi possível sincronizar no Supabase.'

    if not senha_plana:
        return False, 'Senha não disponível para sincronização no Supabase.'

    metadata = {
        'username': usuario.username,
        'empresa_id': usuario.empresa.id if usuario.empresa else None,
        'tipo': usuario.tipo,
        'django_user_id': usuario.id,
    }

    response = supabase_auth.admin_create_user(
        email=usuario.email,
        password=senha_plana,
        user_metadata=metadata,
        email_confirm=False,
    )

    if 'error' in response:
        return False, str(response['error'])

    supabase_uid = response['user'].id
    sync_record, _ = SupabaseUsuarioSync.objects.get_or_create(
        usuario=usuario,
        defaults={
            'supabase_uid': supabase_uid,
            'sincronizado': True,
            'erro_sincronizacao': '',
        },
    )

    if sync_record.supabase_uid != supabase_uid or not sync_record.sincronizado:
        sync_record.supabase_uid = supabase_uid
        sync_record.sincronizado = True
        sync_record.erro_sincronizacao = ''
        sync_record.save(update_fields=['supabase_uid', 'sincronizado', 'erro_sincronizacao', 'ultima_sincronizacao'])

    return True, supabase_uid


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def is_admin(user):
    """Verifica se usuário é admin ou staff"""
    return user.is_superuser or user.is_staff or (hasattr(user, 'is_admin_empresa') and user.is_admin_empresa())


def hash_token_seguro(token: str) -> str:
    """Gera hash SHA-256 para não persistir token puro em banco."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


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
            request.session.set_expiry(0)
            
            # Registra o login para auditoria
            login_record = LoginRegistro.objects.create(
                usuario=user,
                empresa=user.empresa if user.empresa else None,
                ip_address=ip,
                user_agent=get_user_agent(request),
                sucesso=True
            )
            
            # 🔍 Detecta anomalias e cria alertas
            if user.empresa:
                anomalias = detectar_anomalias_login(
                    user, 
                    user.empresa,
                    ip,
                    get_user_agent(request)
                )
                
                # Notificar proprietário sobre anomalias
                for anomalia in anomalias:
                    notificar_anomalia(anomalia)
                
                # Atualizar gráfico de acesso
                atualizar_grafico_acesso(user.empresa)
            
            # Mensagem de boas-vindas
            nome = user.get_full_name() or user.username
            messages.success(request, f'✅ Bem-vindo(a), {nome}!')
            
            # Redireciona
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # Portal do fornecedor: acesso isolado com grupo minimo.
            try:
                fornecedor = user.fornecedor_profile
            except Exception:
                fornecedor = None

            if fornecedor and fornecedor.portal_enabled:
                group, _ = Group.objects.get_or_create(name='FORNECEDOR')
                if not user.groups.filter(pk=group.pk).exists():
                    user.groups.add(group)
                return redirect('portal_fornecedor:dashboard')

            try:
                produtor = user.produtor_profile
            except Exception:
                produtor = None

            if produtor and produtor.portal_enabled:
                group, _ = Group.objects.get_or_create(name='PRODUTOR')
                if not user.groups.filter(pk=group.pk).exists():
                    user.groups.add(group)
                return redirect('portal_produtor:dashboard')

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
def usuario_list(request):
    """
    Lista todos os usuários com filtros e busca
    Usuários comuns veem apenas usuários da sua empresa
    Superusuários veem todos
    """
    usuarios = Usuario.objects.select_related('empresa').prefetch_related('roles').all()
    empresas = []
    empresa_id = request.GET.get('empresa_id', '').strip()
    empresa_filtro_obj = None
    view_mode = request.GET.get('view', 'lista').strip()
    if view_mode not in ['lista', 'empresa']:
        view_mode = 'lista'

    if view_mode == 'empresa' and not request.user.is_superuser:
        view_mode = 'lista'
    
    # Filtro por empresa se não for superusuário
    if not request.user.is_superuser:
        if request.user.empresa:
            usuarios = usuarios.filter(empresa=request.user.empresa)
        else:
            usuarios = Usuario.objects.none()
    else:
        # Superusuário pode filtrar por empresa específica
        from empresas.models import Empresa
        empresas = Empresa.objects.order_by('nome')
        if empresa_id:
            try:
                empresa_id_int = int(empresa_id)
            except (TypeError, ValueError):
                empresa_id_int = None

            if empresa_id_int:
                empresa_filtro_obj = empresas.filter(id=empresa_id_int).first()
                if empresa_filtro_obj:
                    usuarios = usuarios.filter(empresa_id=empresa_id_int)

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

    # Paginação com controle de registros por página
    per_page = request.GET.get('per_page', '25')
    try:
        per_page = int(per_page)
        if per_page not in [10, 20, 25, 50, 100]:
            per_page = 25
    except (ValueError, TypeError):
        per_page = 25
    
    page_obj = None
    grouped_empresas = []

    if view_mode == 'empresa':
        usuarios_grouped_qs = usuarios.order_by('empresa__nome', 'username')
        grupos_por_empresa = {}
        sem_empresa = []
        limite_por_grupo = 200

        for usuario in usuarios_grouped_qs:
            if usuario.empresa_id:
                if usuario.empresa_id not in grupos_por_empresa:
                    grupos_por_empresa[usuario.empresa_id] = {
                        'empresa': usuario.empresa,
                        'usuarios': [],
                        'total': 0,
                    }
                grupo = grupos_por_empresa[usuario.empresa_id]
                grupo['total'] += 1
                if grupo['total'] <= limite_por_grupo:
                    grupo['usuarios'].append(usuario)
            else:
                sem_empresa.append(usuario)

        grouped_empresas = sorted(
            grupos_por_empresa.values(),
            key=lambda item: (item['empresa'].nome or '').lower()
        )
        for grupo in grouped_empresas:
            grupo['restantes'] = grupo['total'] - len(grupo['usuarios'])
        if sem_empresa:
            grouped_empresas.append({
                'empresa': None,
                'usuarios': sem_empresa[:limite_por_grupo],
                'total': len(sem_empresa),
                'restantes': max(0, len(sem_empresa) - limite_por_grupo),
            })
    else:
        paginator = Paginator(usuarios, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

    # Resposta AJAX para atualização parcial
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        partial_template = 'usuarios/_usuario_grouped_table.html' if view_mode == 'empresa' else 'usuarios/_usuario_table.html'
        html = render_to_string(
            partial_template,
            {
                'page_obj': page_obj,
                'user': request.user,
                'empresa_filtro_obj': empresa_filtro_obj,
                'grouped_empresas': grouped_empresas,
                'view_mode': view_mode,
            },
            request=request
        )
        return JsonResponse({'html': html})

    context = {
        'page_obj': page_obj,
        'total': usuarios.count(),
        'tipos': TipoUsuario.objects.filter(ativo=True).order_by('ordem', 'nome'),
        'empresas': empresas,
        'empresa_filtro_obj': empresa_filtro_obj,
        'grouped_empresas': grouped_empresas,
        'view_mode': view_mode,
        'title': 'Usuários'
    }
    return render(request, 'usuarios/usuario_list.html', context)


@login_required
def usuario_create(request):
    """
    Cria novo usuário
    Apenas administradores podem criar usuários
    Superusuário pode escolher qualquer empresa
    Usuário comum só pode criar na sua empresa
    """
    # Verifica se usuário é administrador
    if not is_admin(request.user):
        messages.error(request, '❌ Apenas administradores podem criar novos usuários.')
        return redirect('usuarios:usuario_list')
    
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
            senha_plana = form.cleaned_data.get('password1')
            usuario = form.save(commit=False)
            
            # Se não for superusuário, força empresa do usuário logado
            if not request.user.is_superuser:
                usuario.empresa = request.user.empresa
            
            usuario.save()
            
            # Cria perfil do usuário
            PerfilUsuario.objects.get_or_create(usuario=usuario)

            # Sincroniza automaticamente no Supabase Auth
            sync_ok, sync_info = _sync_usuario_para_supabase(usuario, senha_plana)
            if sync_ok:
                logger.info('SYNC_USER_CREATE_SUPABASE_OK user_id=%s supabase_uid=%s', usuario.id, sync_info)
            else:
                logger.error('SYNC_USER_CREATE_SUPABASE_FAIL user_id=%s erro=%s', usuario.id, sync_info)
                messages.warning(
                    request,
                    '⚠️ Usuário criado no sistema local, mas falhou a sincronização com Supabase. '
                    'Você pode sincronizar depois pelo comando de sincronização.'
                )
            
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
def usuario_update(request, pk):
    """
    Atualiza usuário existente
    Apenas administradores podem editar usuários
    Valida se usuário tem permissão para editar
    """
    # Verifica se usuário é administrador
    if not is_admin(request.user):
        messages.error(request, '❌ Apenas administradores podem editar usuários.')
        return redirect('usuarios:usuario_list')
    
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
            # Surface validation errors to aid debugging
            try:
                errors_text = '\n'.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            except Exception:
                errors_text = str(form.errors)
            messages.error(request, f'❌ Erros no formulário: {errors_text}')
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
def usuario_delete(request, pk):
    """
    Exclui usuário (com confirmação)
    Apenas administradores podem excluir usuários
    Não permite excluir o próprio usuário logado
    """
    # Verifica se usuário é administrador
    if not is_admin(request.user):
        messages.error(request, '❌ Apenas administradores podem excluir usuários.')
        return redirect('usuarios:usuario_list')
    
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
        email_alvo = usuario.email
        username_alvo = usuario.username
        ip_execucao = get_client_ip(request)
        empresa_evento = usuario.empresa or request.user.empresa

        audit_data = {
            'acao': 'exclusao_usuario',
            'executor_id': request.user.id,
            'executor_username': request.user.username,
            'alvo_id': usuario.id,
            'alvo_username': usuario.username,
            'alvo_email': usuario.email,
            'ip': ip_execucao,
        }

        logger.warning(
            'AUDIT_USER_DELETE_ATTEMPT executor=%s alvo=%s ip=%s',
            request.user.username,
            usuario.username,
            ip_execucao,
        )

        # Se o usuário estiver sincronizado, remove primeiro do Supabase Auth
        # para evitar inconsistência entre bancos.
        supabase_uid = None
        try:
            supabase_uid = usuario.supabase_sync.supabase_uid
        except Exception:
            supabase_uid = None

        if supabase_uid:
            audit_data['supabase_uid'] = supabase_uid
            try:
                from core.supabase_config import supabase_auth

                response = supabase_auth.admin_delete_user(supabase_uid)
                if 'error' in response:
                    erro = str(response['error'])
                    erro_lower = erro.lower()

                    # Se já não existir no Supabase, seguimos com exclusão local.
                    if 'not found' not in erro_lower and 'does not exist' not in erro_lower:
                        logger.error(
                            'AUDIT_USER_DELETE_FAILED_SUPABASE executor=%s alvo=%s uid=%s erro=%s',
                            request.user.username,
                            usuario.username,
                            supabase_uid,
                            erro,
                        )
                        try:
                            if empresa_evento:
                                criar_alerta(
                                    usuario=request.user,
                                    empresa=empresa_evento,
                                    titulo='Falha ao excluir usuário no Supabase',
                                    descricao=(
                                        f'O superadmin/admin {request.user.username} tentou excluir '
                                        f'o usuário {usuario.username}, mas houve falha no Supabase.'
                                    ),
                                    nivel='ALTO',
                                    dados_adicionais={**audit_data, 'erro': erro},
                                )
                        except Exception:
                            pass
                        messages.error(
                            request,
                            f'❌ Falha ao excluir usuário no Supabase: {erro}. Exclusão local cancelada.'
                        )
                        return redirect('usuarios:usuario_list')

                    messages.warning(
                        request,
                        '⚠️ Usuário não encontrado no Supabase. Seguindo com exclusão local.'
                    )
                    logger.warning(
                        'AUDIT_USER_DELETE_SUPABASE_NOT_FOUND executor=%s alvo=%s uid=%s',
                        request.user.username,
                        usuario.username,
                        supabase_uid,
                    )
            except Exception as e:
                logger.exception(
                    'AUDIT_USER_DELETE_EXCEPTION_SUPABASE executor=%s alvo=%s uid=%s',
                    request.user.username,
                    usuario.username,
                    supabase_uid,
                )
                try:
                    if empresa_evento:
                        criar_alerta(
                            usuario=request.user,
                            empresa=empresa_evento,
                            titulo='Erro técnico ao excluir usuário no Supabase',
                            descricao=(
                                f'Erro técnico durante tentativa de exclusão do usuário {usuario.username} '
                                'no Supabase.'
                            ),
                            nivel='CRITICO',
                            dados_adicionais={**audit_data, 'erro': str(e)},
                        )
                except Exception:
                    pass
                messages.error(
                    request,
                    f'❌ Erro ao comunicar com Supabase: {str(e)}. Exclusão local cancelada.'
                )
                return redirect('usuarios:usuario_list')

        usuario.delete()
        logger.warning(
            'AUDIT_USER_DELETE_SUCCESS executor=%s alvo=%s ip=%s',
            request.user.username,
            audit_data.get('alvo_username'),
            ip_execucao,
        )

        # Notificação por e-mail para o usuário afetado e admins da empresa.
        try:
            destinatarios = set()
            if email_alvo:
                destinatarios.add(email_alvo)

            if empresa_evento:
                admins_empresa = empresa_evento.usuarios.filter(
                    is_active=True
                ).filter(
                    Q(tipo__in=get_codigos_tipos_admin_empresa()) | Q(is_superuser=True)
                ).exclude(email='').values_list('email', flat=True)
                destinatarios.update(admins_empresa)

            if destinatarios:
                empresa_nome = empresa_evento.nome if empresa_evento else 'Sistema'
                assunto = f"{settings.EMAIL_SUBJECT_PREFIX}Alerta de segurança: usuário excluído"
                data_evento = timezone.now()
                mensagem = (
                    f"Uma exclusão de usuário foi realizada no sistema.\n\n"
                    f"Empresa: {empresa_nome}\n"
                    f"Usuário excluído: {username_alvo}\n"
                    f"Executado por: {request.user.username}\n"
                    f"IP: {ip_execucao}\n"
                    f"Data/Hora: {data_evento.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                    f"Se esta ação não foi autorizada, entre em contato imediatamente com o suporte."
                )

                html_message = render_to_string(
                    'emails/usuario_excluido_alerta.html',
                    {
                        'empresa_nome': empresa_nome,
                        'usuario_excluido': username_alvo,
                        'executor': request.user.username,
                        'ip': ip_execucao,
                        'data_evento': data_evento,
                    }
                )

                send_mail(
                    subject=assunto,
                    message=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=list(destinatarios),
                    html_message=html_message,
                    fail_silently=True,
                )
        except Exception:
            logger.exception(
                'AUDIT_USER_DELETE_EMAIL_NOTIFY_FAIL executor=%s alvo=%s',
                request.user.username,
                username_alvo,
            )

        try:
            if empresa_evento:
                criar_alerta(
                    usuario=request.user,
                    empresa=empresa_evento,
                    titulo='Usuário excluído por administrador',
                    descricao=(
                        f'O usuário {audit_data.get("alvo_username")} foi excluído por '
                        f'{request.user.username}.'
                    ),
                    nivel='MEDIO',
                    dados_adicionais=audit_data,
                )
        except Exception:
            pass
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


@login_required
def tipo_usuario_list(request):
    """Lista os tipos de usuário configurados no sistema."""
    if not request.user.is_superuser:
        messages.error(request, '❌ Apenas superusuários podem gerenciar tipos de usuário.')
        return redirect('usuarios:usuario_list')

    tipos = list(TipoUsuario.objects.all().order_by('ordem', 'nome'))
    uso_por_codigo = {
        item['tipo']: item['total']
        for item in Usuario.objects.values('tipo').annotate(total=Count('id'))
    }
    tipos_com_uso = [
        {
            'tipo': tipo,
            'uso_total': uso_por_codigo.get(tipo.codigo, 0),
        }
        for tipo in tipos
    ]

    context = {
        'tipos': tipos_com_uso,
        'total_tipos': len(tipos),
        'tipos_ativos': sum(1 for tipo in tipos if tipo.ativo),
        'tipos_protegidos': sum(1 for tipo in tipos if tipo.protegido),
        'title': 'Tipos de Usuário',
    }
    return render(request, 'usuarios/tipo_usuario_list.html', context)


@login_required
def tipo_usuario_create(request):
    """Cria um novo tipo de usuário."""
    if not request.user.is_superuser:
        messages.error(request, '❌ Apenas superusuários podem criar tipos de usuário.')
        return redirect('usuarios:usuario_list')

    if request.method == 'POST':
        form = TipoUsuarioForm(request.POST)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'✅ Tipo de usuário "{tipo.nome}" criado com sucesso!')
            return redirect('usuarios:tipo_usuario_list')
    else:
        form = TipoUsuarioForm(initial={'ativo': True})

    return render(request, 'usuarios/tipo_usuario_form.html', {
        'form': form,
        'action': 'Criar',
        'title': 'Novo Tipo de Usuário',
    })


@login_required
@require_POST
def tipo_usuario_quick_create(request):
    """Criação rápida de tipo de usuário via modal na tela de usuário."""
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sem permissão para criar tipo de usuário.'}, status=403)

    form = TipoUsuarioForm(request.POST)
    if form.is_valid():
        tipo = form.save()
        return JsonResponse({
            'ok': True,
            'tipo': {
                'codigo': tipo.codigo,
                'nome': tipo.nome,
            }
        })

    return JsonResponse({
        'ok': False,
        'errors': form.errors.get_json_data(),
    }, status=400)


@login_required
def tipo_usuario_update(request, pk):
    """Edita um tipo de usuário existente."""
    if not request.user.is_superuser:
        messages.error(request, '❌ Apenas superusuários podem editar tipos de usuário.')
        return redirect('usuarios:usuario_list')

    tipo = get_object_or_404(TipoUsuario, pk=pk)

    if request.method == 'POST':
        form = TipoUsuarioForm(request.POST, instance=tipo)
        if form.is_valid():
            tipo = form.save()
            messages.success(request, f'✅ Tipo de usuário "{tipo.nome}" atualizado com sucesso!')
            return redirect('usuarios:tipo_usuario_list')
    else:
        form = TipoUsuarioForm(instance=tipo)

    return render(request, 'usuarios/tipo_usuario_form.html', {
        'form': form,
        'tipo_usuario': tipo,
        'action': 'Editar',
        'title': f'Editar Tipo - {tipo.nome}',
    })


@login_required
def tipo_usuario_delete(request, pk):
    """Exclui tipo de usuário que não esteja protegido nem em uso."""
    if not request.user.is_superuser:
        messages.error(request, '❌ Apenas superusuários podem excluir tipos de usuário.')
        return redirect('usuarios:usuario_list')

    tipo = get_object_or_404(TipoUsuario, pk=pk)
    total_usuarios = Usuario.objects.filter(tipo=tipo.codigo).count()

    if tipo.protegido:
        messages.error(request, '❌ Tipos padrão protegidos não podem ser excluídos.')
        return redirect('usuarios:tipo_usuario_list')

    if total_usuarios > 0:
        messages.error(request, '❌ Este tipo está em uso e não pode ser excluído.')
        return redirect('usuarios:tipo_usuario_list')

    if request.method == 'POST':
        nome = tipo.nome
        tipo.delete()
        messages.success(request, f'🗑️ Tipo de usuário "{nome}" excluído com sucesso!')
        return redirect('usuarios:tipo_usuario_list')

    return render(request, 'usuarios/tipo_usuario_confirm_delete.html', {
        'tipo_usuario': tipo,
        'total_usuarios': total_usuarios,
        'title': f'Excluir Tipo - {tipo.nome}',
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def usuario_troca_senha_emergencial(request, pk):
    """
    Superadmin pode forçar troca de senha de um usuário com opção de rollback.
    O rollback restaura a hash anterior no Django via link único por token.
    """
    usuario = get_object_or_404(Usuario, pk=pk)

    if usuario.id == request.user.id:
        messages.error(request, '❌ Não é permitido aplicar troca emergencial na sua própria conta.')
        return redirect('usuarios:usuario_list')

    if request.method == 'POST':
        nova_senha = (request.POST.get('nova_senha') or '').strip()
        confirmar_senha = (request.POST.get('confirmar_senha') or '').strip()
        motivo = (request.POST.get('motivo') or '').strip()

        if not nova_senha or len(nova_senha) < 8:
            messages.error(request, '❌ A nova senha deve ter pelo menos 8 caracteres.')
            return redirect('usuarios:usuario_troca_senha_emergencial', pk=usuario.id)

        if nova_senha != confirmar_senha:
            messages.error(request, '❌ A confirmação de senha não confere.')
            return redirect('usuarios:usuario_troca_senha_emergencial', pk=usuario.id)

        # Valida que existe empresa para registrar a troca
        empresa_evento = usuario.empresa or request.user.empresa
        if not empresa_evento:
            messages.error(
                request,
                '❌ Não foi possível completar a troca emergencial: usuário sem empresa vinculada. '
                'Verifique o cadastro do usuário alvo ou do superadmin executor.'
            )
            return redirect('usuarios:usuario_troca_senha_emergencial', pk=usuario.id)

        ip_execucao = get_client_ip(request)
        user_agent_execucao = get_user_agent(request)
        token_raw = secrets.token_urlsafe(32)
        token_hash = hash_token_seguro(token_raw)
        expira_em = timezone.now() + timedelta(hours=24)

        supabase_uid = None
        try:
            supabase_uid = usuario.supabase_sync.supabase_uid
        except Exception:
            supabase_uid = None

        try:
            with transaction.atomic():
                senha_anterior_hash = usuario.password
                usuario.set_password(nova_senha)
                usuario.save(update_fields=['password'])

                if supabase_uid:
                    from core.supabase_config import supabase_auth
                    sync_response = supabase_auth.admin_update_user_password(
                        user_id=supabase_uid,
                        password=nova_senha,
                    )
                    if 'error' in sync_response:
                        raise ValueError(
                            f"Falha ao atualizar senha no Supabase: {sync_response['error']}"
                        )

                troca = TrocaSenhaEmergencial.objects.create(
                    usuario_alvo=usuario,
                    executado_por=request.user,
                    empresa=empresa_evento,
                    senha_anterior_hash=senha_anterior_hash,
                    token_cancelamento_hash=token_hash,
                    motivo=motivo,
                    expira_em=expira_em,
                    ip_execucao=ip_execucao,
                    user_agent_execucao=user_agent_execucao,
                )
        except Exception as exc:
            logger.exception(
                'AUDIT_EMERGENCY_PASSWORD_CHANGE_FAIL executor=%s alvo=%s',
                request.user.username,
                usuario.username,
            )
            messages.error(request, f'❌ Não foi possível concluir a troca emergencial: {str(exc)}')
            return redirect('usuarios:usuario_troca_senha_emergencial', pk=usuario.id)

        cancel_url = request.build_absolute_uri(
            reverse('usuarios:cancelar_troca_senha_emergencial', args=[token_raw])
        )

        try:
            destinatarios = set()
            if usuario.email:
                destinatarios.add(usuario.email)

            if empresa_evento:
                admins_empresa = empresa_evento.usuarios.filter(
                    is_active=True
                ).filter(
                    Q(tipo__in=get_codigos_tipos_admin_empresa()) | Q(is_superuser=True)
                ).exclude(email='').values_list('email', flat=True)
                destinatarios.update(admins_empresa)

            if destinatarios:
                assunto = f"{getattr(settings, 'EMAIL_SUBJECT_PREFIX', '')}Alerta: senha alterada em modo emergencial"
                data_evento = timezone.now()
                mensagem = (
                    f"Uma troca emergencial de senha foi executada.\n\n"
                    f"Empresa: {empresa_evento.nome if empresa_evento else 'Sistema'}\n"
                    f"Usuário afetado: {usuario.username}\n"
                    f"Executado por: {request.user.username}\n"
                    f"IP: {ip_execucao}\n"
                    f"Data/Hora: {data_evento.strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"Motivo: {motivo or 'Não informado'}\n\n"
                    f"Se esta ação não foi autorizada, cancele em até 24h: {cancel_url}"
                )

                html_message = render_to_string(
                    'emails/troca_senha_emergencial_alerta.html',
                    {
                        'empresa_nome': empresa_evento.nome if empresa_evento else 'Sistema',
                        'usuario_alvo': usuario,
                        'executor': request.user,
                        'ip': ip_execucao,
                        'data_evento': data_evento,
                        'motivo': motivo,
                        'cancel_url': cancel_url,
                        'expira_em': expira_em,
                    }
                )

                send_mail(
                    subject=assunto,
                    message=mensagem,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=list(destinatarios),
                    html_message=html_message,
                    fail_silently=True,
                )
        except Exception:
            logger.exception(
                'AUDIT_EMERGENCY_PASSWORD_CHANGE_EMAIL_FAIL executor=%s alvo=%s',
                request.user.username,
                usuario.username,
            )

        try:
            if troca.empresa:
                criar_alerta(
                    usuario=request.user,
                    empresa=troca.empresa,
                    titulo='Troca emergencial de senha executada',
                    descricao=(
                        f'Superadmin {request.user.username} alterou a senha de {usuario.username} '
                        'em modo emergencial.'
                    ),
                    nivel='ALTO',
                    dados_adicionais={
                        'acao': 'troca_senha_emergencial',
                        'troca_id': troca.id,
                        'usuario_alvo_id': usuario.id,
                        'usuario_alvo_username': usuario.username,
                        'executor_id': request.user.id,
                        'executor_username': request.user.username,
                        'ip_execucao': ip_execucao,
                        'motivo': motivo,
                        'expira_em': expira_em.isoformat(),
                    }
                )
        except Exception:
            logger.exception(
                'AUDIT_EMERGENCY_PASSWORD_CHANGE_ALERT_FAIL executor=%s alvo=%s',
                request.user.username,
                usuario.username,
            )

        messages.success(
            request,
            '✅ Troca emergencial aplicada com sucesso. O e-mail de segurança com link de cancelamento foi enviado.'
        )
        return redirect('usuarios:usuario_list')

    context = {
        'usuario_alvo': usuario,
        'title': f'Troca Emergencial de Senha - {usuario.username}',
    }
    return render(request, 'usuarios/usuario_senha_emergencial.html', context)


def cancelar_troca_senha_emergencial(request, token):
    """
    Cancela troca emergencial via token e restaura a senha anterior no Django.
    """
    token_hash = hash_token_seguro(token)
    troca = TrocaSenhaEmergencial.objects.select_related(
        'usuario_alvo',
        'empresa',
        'executado_por',
    ).filter(
        token_cancelamento_hash=token_hash
    ).first()

    if not troca:
        return render(
            request,
            'usuarios/cancelar_senha_emergencial.html',
            {
                'title': 'Cancelar Troca Emergencial',
                'token_invalido': True,
            },
            status=404,
        )

    if troca.status == 'ATIVA' and troca.is_expirada():
        troca.status = 'EXPIRADA'
        troca.save(update_fields=['status'])

    if troca.status != 'ATIVA':
        return render(
            request,
            'usuarios/cancelar_senha_emergencial.html',
            {
                'title': 'Cancelar Troca Emergencial',
                'troca': troca,
                'nao_disponivel': True,
            }
        )

    if request.method == 'POST':
        try:
            with transaction.atomic():
                usuario = troca.usuario_alvo
                usuario.password = troca.senha_anterior_hash
                usuario.save(update_fields=['password'])

                troca.status = 'CANCELADA'
                troca.data_cancelamento = timezone.now()
                troca.ip_cancelamento = get_client_ip(request)
                troca.user_agent_cancelamento = get_user_agent(request)
                troca.save(update_fields=[
                    'status',
                    'data_cancelamento',
                    'ip_cancelamento',
                    'user_agent_cancelamento',
                ])
        except Exception:
            logger.exception('AUDIT_EMERGENCY_PASSWORD_ROLLBACK_FAIL troca_id=%s', troca.id)
            return render(
                request,
                'usuarios/cancelar_senha_emergencial.html',
                {
                    'title': 'Cancelar Troca Emergencial',
                    'troca': troca,
                    'erro_cancelamento': True,
                },
                status=500,
            )

        supabase_msg = ''
        try:
            supabase_uid = None
            try:
                supabase_uid = troca.usuario_alvo.supabase_sync.supabase_uid
            except Exception:
                supabase_uid = None

            # Não é possível restaurar senha anterior no Supabase a partir de hash.
            # Para reduzir risco, dispara e-mail oficial de reset no Supabase.
            if supabase_uid and troca.usuario_alvo.email:
                from core.supabase_config import supabase_auth
                reset_response = supabase_auth.reset_password(troca.usuario_alvo.email)
                if 'error' in reset_response:
                    supabase_msg = 'Falha ao acionar reset no Supabase. Contate o suporte.'
                else:
                    supabase_msg = 'Foi enviado um e-mail de redefinição no Supabase para sincronizar a senha externa.'
        except Exception:
            logger.exception('AUDIT_EMERGENCY_PASSWORD_ROLLBACK_SUPABASE_FAIL troca_id=%s', troca.id)

        try:
            if troca.empresa:
                criar_alerta(
                    usuario=troca.usuario_alvo,
                    empresa=troca.empresa,
                    titulo='Troca emergencial de senha cancelada',
                    descricao=(
                        f'A troca emergencial de senha do usuário {troca.usuario_alvo.username} '
                        'foi cancelada com rollback da senha anterior.'
                    ),
                    nivel='MEDIO',
                    dados_adicionais={
                        'acao': 'cancelamento_troca_senha_emergencial',
                        'troca_id': troca.id,
                        'usuario_alvo_id': troca.usuario_alvo.id,
                        'executor_original_id': troca.executado_por_id,
                        'ip_cancelamento': troca.ip_cancelamento,
                    }
                )
        except Exception:
            logger.exception('AUDIT_EMERGENCY_PASSWORD_ROLLBACK_ALERT_FAIL troca_id=%s', troca.id)

        return render(
            request,
            'usuarios/cancelar_senha_emergencial.html',
            {
                'title': 'Cancelar Troca Emergencial',
                'troca': troca,
                'cancelamento_sucesso': True,
                'supabase_msg': supabase_msg,
            }
        )

    return render(
        request,
        'usuarios/cancelar_senha_emergencial.html',
        {
            'title': 'Cancelar Troca Emergencial',
            'troca': troca,
        }
    )


# ============================================
# REGISTROS DE LOGIN (AUDITORIA)
# ============================================

@login_required
@user_passes_test(is_admin)
def login_registros(request):
    """
    Exibe histórico de logins com gráficos, anomalias e alertas
    Filtrado por empresa se não for superusuário
    """
    registros = LoginRegistro.objects.select_related('usuario', 'empresa').all()
    
    # Determinar empresa a filtrar
    empresa_filtro = None
    if not request.user.is_superuser:
        if request.user.empresa:
            registros = registros.filter(empresa=request.user.empresa)
            empresa_filtro = request.user.empresa
        else:
            registros = LoginRegistro.objects.none()
    else:
        # Superusuário pode filtrar
        empresa_id = request.GET.get('empresa', '')
        if empresa_id:
            registros = registros.filter(empresa_id=empresa_id)
            empresa_filtro = get_object_or_404('empresas.Empresa', id=empresa_id) if empresa_id.isdigit() else None
    
    # Filtro por usuário
    usuario_id = request.GET.get('usuario', '')
    if usuario_id:
        registros = registros.filter(usuario_id=usuario_id)
    
    # Filtro por período
    periodo = request.GET.get('periodo', 'semana')
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
    
    # Estatísticas básicas
    total_logins = registros.count()
    logins_sucesso = registros.filter(sucesso=True).count()
    logins_falha = registros.filter(sucesso=False).count()
    taxa_sucesso = round((logins_sucesso / total_logins * 100), 2) if total_logins > 0 else 0
    
    # 📊 Obter estatísticas e gráficos
    dados_graficos = None
    if empresa_filtro:
        dados_graficos = obter_estatisticas_acesso(empresa_filtro, dias=30)
    
    # 🚨 Obter anomalias recentes
    anomalias_recentes = LoginAnomalia.objects.select_related('usuario').filter(
        confirmada=False  # Apenas não confirmadas
    ).order_by('-data_deteccao')[:10]
    
    if not request.user.is_superuser and empresa_filtro:
        anomalias_recentes = anomalias_recentes.filter(usuario__empresa=empresa_filtro)
    
    # 🔔 Obter alertas recentes
    alertas_recentes = AlertaSeguranca.objects.select_related('usuario').filter(
        status__in=['NOVO', 'EM_INVESTIGACAO']
    ).order_by('-data_criacao')[:10]
    
    if not request.user.is_superuser and empresa_filtro:
        alertas_recentes = alertas_recentes.filter(empresa=empresa_filtro)
    
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
        'taxa_sucesso': taxa_sucesso,
        'anomalias_recentes': anomalias_recentes,
        'alertas_recentes': alertas_recentes,
        'dados_graficos': dados_graficos,
        'title': 'Registros de Login',
        'empresa_filtro': empresa_filtro,
    }
    
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


@login_required
@user_passes_test(lambda u: u.is_superuser or u.perfil == 'ADMIN')
def configuracao_sistema(request):
    """
    Configurações globais do sistema por empresa
    """
    from core.models import ConfiguracaoSistema
    
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    if request.method == 'POST':
        # Atualizar configurações
        config.modo_compras = request.POST.get('modo_compras', config.modo_compras)
        config.modo_estoque = request.POST.get('modo_estoque', config.modo_estoque)
        
        # Compras
        config.exigir_aprovacao_solicitacao = request.POST.get('exigir_aprovacao_solicitacao') == 'on'
        config.exigir_cotacao_obrigatoria = request.POST.get('exigir_cotacao_obrigatoria') == 'on'
        config.permitir_recebimento_sem_pedido = request.POST.get('permitir_recebimento_sem_pedido') == 'on'
        config.entrada_estoque_automatica = request.POST.get('entrada_estoque_automatica') == 'on'
        
        # Estoque
        config.controle_lote_obrigatorio = request.POST.get('controle_lote_obrigatorio') == 'on'
        config.gerar_lote_automatico = request.POST.get('gerar_lote_automatico') == 'on'
        config.permitir_estoque_negativo = request.POST.get('permitir_estoque_negativo') == 'on'
        config.validade_obrigatoria = request.POST.get('validade_obrigatoria') == 'on'
        config.rastreamento_completo = request.POST.get('rastreamento_completo') == 'on'
        config.exigir_numero_serie = request.POST.get('exigir_numero_serie') == 'on'
        config.exigir_motivo_movimentacao = request.POST.get('exigir_motivo_movimentacao') == 'on'
        config.ajuste_estoque_requer_aprovacao = request.POST.get('ajuste_estoque_requer_aprovacao') == 'on'
        
        # Produtos
        config.ncm_obrigatorio = request.POST.get('ncm_obrigatorio') == 'on'
        config.preco_custo_obrigatorio = request.POST.get('preco_custo_obrigatorio') == 'on'
        
        # Notificações
        config.notificar_estoque_minimo = request.POST.get('notificar_estoque_minimo') == 'on'
        config.notificar_solicitacao_pendente = request.POST.get('notificar_solicitacao_pendente') == 'on'
        
        config.atualizado_por = request.user
        config.save()
        
        messages.success(request, '✅ Configurações atualizadas com sucesso!')
        next_url = request.POST.get('next') or request.GET.get('next') or 'configuracao_sistema'
        return redirect(next_url)
    
    context = {
        'config': config,
        'title': 'Configurações do Sistema'
    }
    
    return render(request, 'core/configuracao_sistema.html', context)
