from django.contrib import messages
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

import re
from django.views.decorators.http import require_POST

from .forms_produtor import ProdutorForm
from .models import Produtor


@login_required
def produtor_list(request):
    busca = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip()

    produtores = Produtor.objects.filter(empresa=request.user.empresa)

    if busca:
        produtores = produtores.filter(
            Q(razao_social__icontains=busca)
            | Q(nome_fantasia__icontains=busca)
            | Q(cnpj_cpf__icontains=busca)
            | Q(cidade__icontains=busca)
        )

    if status in {'ATIVO', 'INATIVO'}:
        produtores = produtores.filter(status=status)

    paginator = Paginator(produtores.order_by('razao_social'), 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Cálculo dos totais de empréstimos dos produtores da página
    from decimal import Decimal
    from cadastros.models import EmprestimoProdutor
    from django.db import models
    produtor_ids = [p.id for p in page_obj.object_list]
    total_entrada = Decimal('0')
    total_saida = Decimal('0')
    if produtor_ids:
        agregados = (
            EmprestimoProdutor.objects
            .filter(produtor_id__in=produtor_ids, empresa=request.user.empresa)
            .aggregate(
                entrada=models.Sum('quantidade_emprestada'),
                saida=models.Sum('quantidade_devolvida')
            )
        )
        total_entrada = agregados['entrada'] or Decimal('0')
        total_saida = agregados['saida'] or Decimal('0')

    return render(
        request,
        'cadastros/produtor/produtor_list.html',
        {
            'page_obj': page_obj,
            'q': busca,
            'status': status,
            'emprestimo_total_entrada': total_entrada,
            'emprestimo_total_saida': total_saida,
            'emprestimo_total_saldo': total_entrada - total_saida,
        },
    )


@login_required
def produtor_detail(request, pk):
    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)
    from decimal import Decimal
    from cadastros.models import EmprestimoProdutor
    from django.db import models
    agregados = (
        EmprestimoProdutor.objects
        .filter(produtor=produtor, empresa=request.user.empresa)
        .aggregate(
            entrada=models.Sum('quantidade_emprestada'),
            saida=models.Sum('quantidade_devolvida')
        )
    )
    total_entrada = agregados['entrada'] or Decimal('0')
    total_saida = agregados['saida'] or Decimal('0')
    return render(request, 'cadastros/produtor/produtor_detail.html', {
        'produtor': produtor,
        'emprestimo_total_entrada': total_entrada,
        'emprestimo_total_saida': total_saida,
        'emprestimo_total_saldo': total_entrada - total_saida,
    })


@login_required
def produtor_create(request):
    if request.method == 'POST':
        form = ProdutorForm(request.POST)
        if form.is_valid():
            produtor = form.save(commit=False)
            produtor.empresa = request.user.empresa
            produtor.cadastrado_por = request.user
            produtor.save()
            messages.success(request, 'Produtor cadastrado com sucesso.')
            return redirect('cadastros:produtor_list')
    else:
        form = ProdutorForm()

    return render(
        request,
        'cadastros/produtor/produtor_form.html',
        {
            'form': form,
            'action': 'Cadastrar',
        },
    )


@login_required
def produtor_update(request, pk):
    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        form = ProdutorForm(request.POST, instance=produtor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produtor atualizado com sucesso.')
            return redirect('cadastros:produtor_list')
    else:
        form = ProdutorForm(instance=produtor)

    return render(
        request,
        'cadastros/produtor/produtor_form.html',
        {
            'form': form,
            'action': 'Editar',
            'produtor': produtor,
        },
    )


@login_required
def produtor_delete(request, pk):
    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        produtor.status = 'INATIVO'
        produtor.save(update_fields=['status', 'data_atualizacao'])
        messages.success(request, 'Produtor inativado com sucesso.')
        return redirect('cadastros:produtor_list')

    return render(request, 'cadastros/produtor/produtor_confirm_delete.html', {'produtor': produtor})


@login_required
def produtor_criar_acesso_portal(request, pk):
    """Cria usuário de portal para o produtor e envia e-mail de primeiro acesso."""
    from usuarios.models import Usuario

    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)


    import secrets
    from cadastros.emprestimo_utils import registrar_interacao_emprestimo
    senha_provisoria = None
    whatsapp_enviado = False

    # settings já está importado no topo do arquivo, não importar localmente!
    site_domain = getattr(settings, 'SITE_DOMAIN', '') or request.get_host()
    use_https = getattr(settings, 'SITE_HTTPS', False) or request.is_secure()

    def _enviar_reset(email):
        form = PasswordResetForm(data={'email': email})
        if form.is_valid():
            form.save(
                request=request,
                domain_override=site_domain,
                use_https=use_https,
                from_email=None,
                email_template_name='usuarios/password_reset_email.html',
                subject_template_name='usuarios/password_reset_subject.txt',
            )
            return True
        return False

    if produtor.portal_user_id:
        user_portal = produtor.portal_user
        if not user_portal.is_active:
            user_portal.is_active = True
            user_portal.save(update_fields=['is_active'])
        if produtor.email:
            _enviar_reset(user_portal.email)
            messages.success(request, f'Convite de acesso reenviado para {user_portal.email}.')
        elif produtor.telefone:
            senha_provisoria = secrets.token_urlsafe(8)
            user_portal.set_password(senha_provisoria)
            user_portal.save(update_fields=['password'])
            # Enviar WhatsApp
            from django.urls import reverse
            numero = re.sub(r'\D', '', produtor.telefone)
            if not numero.startswith('55'):
                numero = '55' + numero
            numero = '+' + numero
            # Agora existe rota de login do portal_produtor
            portal_url = request.build_absolute_uri(reverse('portal_produtor:login'))
            mensagem = (
                f'Olá, {produtor.nome_fantasia or produtor.razao_social}!\n\n'
                f'Seu acesso ao Portal do Produtor foi criado.\n'
                f'Usuário: {user_portal.username}\nSenha provisória: {senha_provisoria}\n'
                f'Acesse: {portal_url}\n\nTroque a senha no primeiro acesso.'
            )
            try:
                from twilio.rest import Client
                twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
                twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
                twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
                if all([twilio_account_sid, twilio_auth_token, twilio_phone]):
                    client = Client(twilio_account_sid, twilio_auth_token)
                    client.messages.create(
                        from_=f'whatsapp:{twilio_phone}',
                        body=mensagem,
                        to=f'whatsapp:{numero}',
                    )
                    whatsapp_enviado = True
            except Exception:
                whatsapp_enviado = False
            messages.success(request, f'Acesso reativado. Senha provisória: {senha_provisoria} (também enviada por WhatsApp se possível).')
        else:
            messages.warning(request, 'Produtor sem e-mail ou telefone para envio automático. Cadastre um contato.')
        # Só registra interação se houver objeto de empréstimo
        # registrar_interacao_emprestimo espera um objeto com .empresa
        # Aqui não há empréstimo, então apenas ignore
        return redirect('cadastros:produtor_detail', pk=pk)

    doc = re.sub(r'\D', '', produtor.cnpj_cpf or '')
    base_username = f'prod_{doc or pk}'
    username = base_username
    counter = 1
    while Usuario.objects.filter(username=username).exists():
        username = f'{base_username}_{counter}'
        counter += 1

    nome_display = (produtor.nome_fantasia or produtor.razao_social or '')[:30]

    if produtor.email:
        user_portal = Usuario.objects.create_user(
            username=username,
            email=produtor.email,
            password=None,
            first_name=nome_display,
            empresa=produtor.empresa,
            tipo='PROD',
            is_active=True,
        )
        user_portal.set_unusable_password()
        user_portal.save(update_fields=['password'])
    elif produtor.telefone:
        senha_provisoria = secrets.token_urlsafe(8)
        user_portal = Usuario.objects.create_user(
            username=username,
            email='',
            password=senha_provisoria,
            first_name=nome_display,
            empresa=produtor.empresa,
            tipo='PROD',
            is_active=True,
        )
        # Enviar WhatsApp
        from django.urls import reverse
        numero = re.sub(r'\D', '', produtor.telefone)
        if not numero.startswith('55'):
            numero = '55' + numero
        numero = '+' + numero
        portal_url = request.build_absolute_uri(reverse('portal_produtor:login'))
        mensagem = (
            f'Olá, {produtor.nome_fantasia or produtor.razao_social}!\n\n'
            f'Seu acesso ao Portal do Produtor foi criado.\n'
            f'Usuário: {user_portal.username}\nSenha provisória: {senha_provisoria}\n'
            f'Acesse: {portal_url}\n\nTroque a senha no primeiro acesso.'
        )
        try:
            from twilio.rest import Client
            twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            if all([twilio_account_sid, twilio_auth_token, twilio_phone]):
                client = Client(twilio_account_sid, twilio_auth_token)
                client.messages.create(
                    from_=f'whatsapp:{twilio_phone}',
                    body=mensagem,
                    to=f'whatsapp:{numero}',
                )
                whatsapp_enviado = True
        except Exception:
            whatsapp_enviado = False
    else:
        messages.error(request, 'Cadastre e-mail ou telefone no produtor para criar acesso ao portal.')
        return redirect('cadastros:produtor_detail', pk=pk)


    produtor.portal_user = user_portal
    produtor.portal_enabled = True
    produtor.save(update_fields=['portal_user', 'portal_enabled'])

    if produtor.email:
        if _enviar_reset(user_portal.email):
            messages.success(request, f'Acesso ao portal criado e e-mail enviado para {user_portal.email}.')
        else:
            messages.warning(request, 'Acesso criado, mas não foi possível enviar o e-mail de primeiro acesso.')
    elif produtor.telefone:
        messages.success(request, f'Acesso ao portal criado. Senha provisória: {senha_provisoria} (também enviada por WhatsApp se possível).')
    else:
        messages.warning(request, 'Acesso criado, mas não foi possível enviar senha automática. Cadastre e-mail ou telefone.')

    registrar_interacao_emprestimo(None, 'NOTIFICACAO_INTERNA', f'Acesso portal criado para produtor {produtor}.', usuario=request.user, sucesso=True)
    return redirect('cadastros:produtor_detail', pk=pk)


@login_required
@require_POST
def produtor_bloquear_portal(request, pk):
    """Bloqueia ou desbloqueia o acesso ao portal do produtor."""
    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)
    if produtor.portal_user_id:
        user_portal = produtor.portal_user
        user_portal.is_active = not user_portal.is_active
        user_portal.save(update_fields=['is_active'])
        acao = 'desbloqueado' if user_portal.is_active else 'bloqueado'
        messages.success(request, f'Acesso ao portal {acao}.')
    return redirect('cadastros:produtor_detail', pk=pk)
