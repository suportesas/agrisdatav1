from django.contrib import messages
from django.conf import settings
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

    from decimal import Decimal
    from cadastros.models import EmprestimoProdutor
    total_entrada = Decimal('0')
    total_saida = Decimal('0')
    for emp in EmprestimoProdutor.objects.filter(empresa=request.user.empresa).select_related('produto'):
        preco = Decimal(getattr(emp.produto, 'preco_venda', 0) or 0)
        total_entrada += Decimal(emp.quantidade_emprestada or 0) * preco
        total_saida += Decimal(emp.quantidade_devolvida or 0) * preco

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
    total_entrada = Decimal('0')
    total_saida = Decimal('0')
    for emp in EmprestimoProdutor.objects.filter(produtor=produtor, empresa=request.user.empresa).select_related('produto'):
        preco = Decimal(getattr(emp.produto, 'preco_venda', 0) or 0)
        total_entrada += Decimal(emp.quantidade_emprestada or 0) * preco
        total_saida += Decimal(emp.quantidade_devolvida or 0) * preco
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
    """Cria (ou reativa) acesso portal do produtor com senha provisória obrigatória."""
    from django.core.mail import send_mail
    from django.urls import reverse
    from usuarios.models import Usuario
    import secrets

    produtor = get_object_or_404(Produtor, pk=pk, empresa=request.user.empresa)

    if not produtor.email and not produtor.telefone:
        messages.error(request, 'Cadastre e-mail ou telefone no produtor para criar acesso ao portal.')
        return redirect('cadastros:produtor_detail', pk=pk)

    senha_provisoria = secrets.token_urlsafe(10)
    portal_url = request.build_absolute_uri(reverse('portal_produtor:login'))
    nome_produtor = produtor.nome_fantasia or produtor.razao_social

    def _enviar_email_senha(email, username):
        try:
            send_mail(
                subject='Acesso ao Portal do Produtor',
                message=(
                    f'Olá, {nome_produtor}!\n\n'
                    f'Seu acesso ao Portal do Produtor foi criado/reativado.\n\n'
                    f'Usuário: {username}\n'
                    f'Senha provisória: {senha_provisoria}\n\n'
                    f'Acesse: {portal_url}\n\n'
                    f'Você será solicitado a trocar a senha no primeiro acesso.\n\n'
                    f'{produtor.empresa.nome}'
                ),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                recipient_list=[email],
                fail_silently=True,
            )
            return True
        except Exception:
            return False

    def _enviar_whatsapp(username):
        try:
            from twilio.rest import Client
            sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            if not all([sid, token, phone]):
                return False
            numero = re.sub(r'\D', '', produtor.telefone)
            if not numero.startswith('55'):
                numero = '55' + numero
            numero = '+' + numero
            Client(sid, token).messages.create(
                from_=f'whatsapp:{phone}',
                body=(
                    f'Olá, {nome_produtor}!\n\n'
                    f'Seu acesso ao Portal do Produtor foi criado/reativado.\n'
                    f'Usuário: {username}\nSenha provisória: {senha_provisoria}\n'
                    f'Acesse: {portal_url}\n\nTroque a senha no primeiro acesso.'
                ),
                to=f'whatsapp:{numero}',
            )
            return True
        except Exception:
            return False

    # ---- Reenvio: produtor já tem usuário ----
    if produtor.portal_user_id:
        user_portal = produtor.portal_user
        user_portal.set_password(senha_provisoria)
        user_portal.must_change_password = True
        user_portal.is_active = True
        user_portal.save(update_fields=['password', 'must_change_password', 'is_active'])

        if not produtor.portal_enabled:
            produtor.portal_enabled = True
            produtor.save(update_fields=['portal_enabled'])

        enviado = False
        if produtor.email:
            enviado = _enviar_email_senha(user_portal.email, user_portal.username)
        if produtor.telefone:
            _enviar_whatsapp(user_portal.username)

        msg = f'Nova senha provisória gerada: {senha_provisoria}'
        if enviado:
            msg += f' (e-mail enviado para {user_portal.email})'
        messages.success(request, f'Acesso reativado. {msg}')
        return redirect('cadastros:produtor_detail', pk=pk)

    # ---- Primeiro acesso: cria o usuário ----
    doc = re.sub(r'\D', '', produtor.cnpj_cpf or '')
    base_username = f'prod_{doc or pk}'
    username = base_username
    counter = 1
    while Usuario.objects.filter(username=username).exists():
        username = f'{base_username}_{counter}'
        counter += 1

    nome_display = (produtor.nome_fantasia or produtor.razao_social or '')[:30]
    user_portal = Usuario.objects.create_user(
        username=username,
        email=produtor.email or '',
        password=senha_provisoria,
        first_name=nome_display,
        empresa=produtor.empresa,
        tipo='PROD',
        is_active=True,
        must_change_password=True,
    )

    produtor.portal_user = user_portal
    produtor.portal_enabled = True
    produtor.save(update_fields=['portal_user', 'portal_enabled'])

    enviado = False
    if produtor.email:
        enviado = _enviar_email_senha(user_portal.email, user_portal.username)
    if produtor.telefone:
        _enviar_whatsapp(user_portal.username)

    msg = f'Usuário: {user_portal.username} | Senha provisória: {senha_provisoria}'
    if enviado:
        msg += f' (e-mail enviado para {produtor.email})'
    messages.success(request, f'Acesso ao portal criado! {msg}')
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
