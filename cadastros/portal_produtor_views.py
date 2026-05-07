import base64
import json
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db.models import Count, Q, Sum
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .emprestimo_utils import (
    criar_mensagem_emprestimo,
    marcar_mensagens_emprestimo_como_lidas,
    registrar_interacao_emprestimo,
)
from .models import EmprestimoMensagemAnexo, EmprestimoMovimento, EmprestimoProdutor, Produtor


# ---------------------------------------------------------------------------
# Decorador: autenticação + troca de senha obrigatória
# ---------------------------------------------------------------------------

def portal_login_required(view_func):
    """login_required + redirecionamento obrigatório para troca de senha provisória."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal_produtor:login')
        if getattr(request.user, 'must_change_password', False):
            messages.warning(request, 'Você deve alterar sua senha provisória antes de continuar.')
            return redirect('portal_produtor:trocar_senha')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_produtor_do_usuario(user):
    try:
        produtor = user.produtor_profile
    except Produtor.DoesNotExist:
        return None

    if not produtor.portal_enabled:
        return None

    if not user.empresa or produtor.empresa_id != user.empresa_id:
        return None

    return produtor


def _produtor_portal_guard(request):
    produtor = _get_produtor_do_usuario(request.user)
    if not produtor:
        raise PermissionDenied('Acesso permitido apenas para produtor com portal habilitado.')

    group, _ = Group.objects.get_or_create(name='PRODUTOR')
    if not request.user.groups.filter(pk=group.pk).exists():
        request.user.groups.add(group)

    return produtor


# ---------------------------------------------------------------------------
# Login / Troca de senha
# ---------------------------------------------------------------------------

def portal_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if getattr(user, 'must_change_password', False):
                messages.warning(request, 'Sua senha é provisória. Defina uma nova senha para continuar.')
                return redirect('portal_produtor:trocar_senha')
            return redirect('portal_produtor:dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'portal_produtor/login.html')


@login_required(login_url='portal_produtor:login')
def trocar_senha_produtor(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save(update_fields=['must_change_password'])
            update_session_auth_hash(request, user)
            messages.success(request, 'Senha alterada com sucesso! Bem-vindo ao portal.')
            return redirect('portal_produtor:dashboard')
    else:
        form = PasswordChangeForm(request.user)
    obrigatorio = getattr(request.user, 'must_change_password', False)
    return render(request, 'portal_produtor/trocar_senha.html', {'form': form, 'obrigatorio': obrigatorio})


# ---------------------------------------------------------------------------
# Views do portal
# ---------------------------------------------------------------------------

@portal_login_required
def dashboard(request):
    produtor = _produtor_portal_guard(request)
    emprestimos_qs = EmprestimoProdutor.objects.filter(
        empresa=request.user.empresa,
        produtor=produtor,
    ).annotate(
        unread_mensagens_produtor_count=Count(
            'mensagens',
            filter=Q(mensagens__perfil_autor='INTERNO', mensagens__lido_produtor_em__isnull=True),
        )
    )

    emprestimos_recentes_qs = emprestimos_qs.select_related('produto', 'unidade_medida', 'requisicao').order_by('-data_emprestimo')
    seen = set()
    emprestimos_recentes = []
    for emp in emprestimos_recentes_qs:
        key = (emp.requisicao_id, emp.produto_id, emp.unidade_medida_id)
        if key not in seen:
            seen.add(key)
            emprestimos_recentes.append(emp)
        if len(emprestimos_recentes) >= 5:
            break

    pendentes_assinatura = emprestimos_qs.filter(
        assinatura_liberador_datahora__isnull=False,
        assinatura_produtor_datahora__isnull=True,
    ).count()

    total_valor_aberto = Decimal('0.00')
    for emp in emprestimos_qs.select_related('produto'):
        preco = getattr(emp.produto, 'preco_venda', None)
        if preco is not None:
            total_valor_aberto += (emp.saldo_pendente or 0) * preco

    totais = emprestimos_qs.aggregate(total_saldo=Sum('saldo_pendente'))
    total_mensagens_nao_lidas = emprestimos_qs.aggregate(total=Sum('unread_mensagens_produtor_count')).get('total') or 0

    return render(request, 'portal_produtor/dashboard.html', {
        'produtor': produtor,
        'emprestimos_recentes': emprestimos_recentes,
        'pendentes_assinatura': pendentes_assinatura,
        'total_emprestimos': emprestimos_qs.count(),
        'total_saldo': totais.get('total_saldo'),
        'total_valor_aberto': total_valor_aberto,
        'total_mensagens_nao_lidas': total_mensagens_nao_lidas,
    })


@portal_login_required
def emprestimos_list(request):
    produtor = _produtor_portal_guard(request)
    emprestimos_qs = EmprestimoProdutor.objects.filter(
        empresa=request.user.empresa,
        produtor=produtor,
    ).select_related('produto', 'unidade_medida', 'requisicao').annotate(
        unread_mensagens_produtor_count=Count(
            'mensagens',
            filter=Q(mensagens__perfil_autor='INTERNO', mensagens__lido_produtor_em__isnull=True),
        )
    ).order_by('-data_emprestimo', '-id')

    status = request.GET.get('status')
    produto_id = request.GET.get('produto')
    apenas_promessa = request.GET.get('apenas_promessa')
    apenas_mensagens_nao_lidas = request.GET.get('apenas_mensagens_nao_lidas')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if status:
        emprestimos_qs = emprestimos_qs.filter(status=status)
    if produto_id:
        emprestimos_qs = emprestimos_qs.filter(produto_id=produto_id)
    if apenas_promessa:
        emprestimos_qs = emprestimos_qs.filter(
            Q(status='PROMESSA') |
            (Q(data_promessa_devolucao__isnull=False) & Q(saldo_pendente__gt=0))
        )
    if apenas_mensagens_nao_lidas:
        emprestimos_qs = emprestimos_qs.filter(mensagens__perfil_autor='INTERNO', mensagens__lido_produtor_em__isnull=True)
    if data_inicio:
        emprestimos_qs = emprestimos_qs.filter(data_emprestimo__date__gte=data_inicio)
    if data_fim:
        emprestimos_qs = emprestimos_qs.filter(data_emprestimo__date__lte=data_fim)

    agrupados = {}
    for emp in emprestimos_qs:
        req_id = emp.requisicao_id or f"emp-{emp.pk}"
        preco_venda = float(getattr(emp.produto, 'preco_venda', 0) or 0)
        valor_emprestado = float(emp.quantidade_emprestada or 0) * preco_venda
        valor_devolvido = float(emp.quantidade_devolvida or 0) * preco_venda
        valor_saldo = float(emp.saldo_pendente or 0) * preco_venda
        if req_id not in agrupados:
            agrupados[req_id] = {
                'data_emprestimo': emp.data_emprestimo,
                'numero_requisicao': emp.requisicao.numero if emp.requisicao else '-',
                'status': emp.status,
                'data_promessa_devolucao': emp.data_promessa_devolucao,
                'emprestimos': [],
                'total_emprestado': 0,
                'total_devolvido': 0,
                'saldo_pendente': 0,
                'unread_mensagens_produtor': 0,
            }
        agrupados[req_id]['emprestimos'].append({
            'obj': emp,
            'valor_emprestado': valor_emprestado,
            'valor_devolvido': valor_devolvido,
            'valor_saldo': valor_saldo,
            'preco_venda': preco_venda,
            'valor_total_produto': float(emp.quantidade_emprestada or 0) * preco_venda,
        })
        agrupados[req_id]['total_emprestado'] += valor_emprestado
        agrupados[req_id]['total_devolvido'] += valor_devolvido
        agrupados[req_id]['saldo_pendente'] += valor_saldo
        agrupados[req_id]['unread_mensagens_produtor'] += getattr(emp, 'unread_mensagens_produtor_count', 0)

    agrupados_lista = sorted(agrupados.values(), key=lambda x: (x['data_emprestimo'], x['numero_requisicao']), reverse=True)

    total_emprestado = sum(g['total_emprestado'] for g in agrupados_lista)
    total_devolvido = sum(g['total_devolvido'] for g in agrupados_lista)
    total_saldo = sum(g['saldo_pendente'] for g in agrupados_lista)

    return render(request, 'portal_produtor/emprestimos_list.html', {
        'produtor': produtor,
        'emprestimos_agrupados': agrupados_lista,
        'totais': {'total_emprestado': total_emprestado, 'total_devolvido': total_devolvido, 'total_saldo': total_saldo},
        'today': date.today(),
        'status': status,
        'produto_id': produto_id,
        'apenas_promessa': apenas_promessa,
        'apenas_mensagens_nao_lidas': apenas_mensagens_nao_lidas,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })


@portal_login_required
def emprestimo_detail(request, pk):
    produtor = _produtor_portal_guard(request)
    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produto', 'unidade_medida', 'requisicao', 'produtor'),
        pk=pk,
        empresa=request.user.empresa,
        produtor=produtor,
    )

    emprestimos_produtos_qs = EmprestimoProdutor.objects.filter(
        requisicao=emprestimo.requisicao,
        produtor=produtor,
        empresa=request.user.empresa,
    ).select_related('produto', 'unidade_medida')
    seen = set()
    emprestimos_produtos = []
    for emp in emprestimos_produtos_qs:
        key = (emp.produto_id, emp.unidade_medida_id)
        if key not in seen:
            seen.add(key)
            emprestimos_produtos.append(emp)

    for emp in emprestimos_produtos:
        marcar_mensagens_emprestimo_como_lidas(emp, 'PRODUTOR')

    movimentos = (
        EmprestimoMovimento.objects
        .filter(empresa=request.user.empresa, emprestimo=emprestimo)
        .select_related('criado_por')
        .order_by('-data_movimento', '-id')
    )
    mensagens = emprestimo.mensagens.select_related('autor').prefetch_related('anexos').all()
    interacoes = emprestimo.interacoes.select_related('usuario').all()[:20]

    return render(request, 'portal_produtor/emprestimo_detail.html', {
        'produtor': produtor,
        'emprestimo': emprestimo,
        'emprestimos_produtos': emprestimos_produtos,
        'movimentos': movimentos,
        'mensagens_emprestimo': mensagens,
        'interacoes_emprestimo': interacoes,
    })


@portal_login_required
def emprestimo_assinar(request, pk):
    produtor = _produtor_portal_guard(request)
    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produto', 'unidade_medida', 'requisicao', 'produtor'),
        pk=pk,
        empresa=request.user.empresa,
        produtor=produtor,
    )

    if not (emprestimo.requisicao and emprestimo.requisicao.assinatura_liberacao_interna_datahora):
        messages.error(request, 'A assinatura interna da liberação ainda não foi concluída.')
        return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)

    if emprestimo.possui_assinatura_produtor:
        messages.warning(request, 'Este empréstimo já foi assinado no portal do produtor.')
        return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)

    if request.method == 'POST':
        assinatura_data = (request.POST.get('assinatura_data') or '').strip()
        assinatura_nome = (request.POST.get('assinatura_produtor_nome') or '').strip()
        assinatura_upload = request.FILES.get('assinatura_upload')
        modo = request.POST.get('modo_assinatura', 'desenho')

        if not assinatura_nome:
            assinatura_nome = request.user.get_full_name() or produtor.razao_social

        if modo == 'upload' and not assinatura_upload:
            messages.error(request, 'Selecione um arquivo de imagem para a assinatura.')
            return render(request, 'portal_produtor/emprestimo_assinar.html', {'produtor': produtor, 'emprestimo': emprestimo})

        if modo == 'desenho' and not assinatura_data:
            messages.error(request, 'Desenhe a assinatura antes de confirmar.')
            return render(request, 'portal_produtor/emprestimo_assinar.html', {'produtor': produtor, 'emprestimo': emprestimo})

        try:
            if modo == 'upload':
                filename = f'assinatura_produtor_{emprestimo.pk}_{uuid4().hex[:8]}.png'
                emprestimo.assinatura_produtor_imagem.save(filename, assinatura_upload, save=False)
            else:
                if ',' in assinatura_data:
                    _, assinatura_b64 = assinatura_data.split(',', 1)
                else:
                    assinatura_b64 = assinatura_data
                assinatura_bin = base64.b64decode(assinatura_b64)
                filename = f'assinatura_produtor_{emprestimo.pk}_{uuid4().hex[:8]}.png'
                emprestimo.assinatura_produtor_imagem.save(filename, ContentFile(assinatura_bin), save=False)

            emprestimo.assinatura_produtor_usuario = request.user
            emprestimo.assinatura_produtor_nome = assinatura_nome
            emprestimo.assinatura_produtor_datahora = timezone.now()
            emprestimo.save(update_fields=[
                'assinatura_produtor_usuario',
                'assinatura_produtor_imagem',
                'assinatura_produtor_nome',
                'assinatura_produtor_datahora',
                'atualizado_em',
            ])

            if emprestimo.requisicao_id:
                req = emprestimo.requisicao
                req.assinatura_produtor_usuario = request.user
                req.assinatura_produtor_nome = assinatura_nome
                req.assinatura_produtor_datahora = timezone.now()
                req.assinatura_produtor_imagem = emprestimo.assinatura_produtor_imagem.name
                req.save(update_fields=[
                    'assinatura_produtor_usuario',
                    'assinatura_produtor_nome',
                    'assinatura_produtor_datahora',
                    'assinatura_produtor_imagem',
                ])

            EmprestimoMovimento.objects.create(
                empresa=request.user.empresa,
                emprestimo=emprestimo,
                tipo_movimento='ASSINATURA_PRODUTOR',
                quantidade=0,
                saldo_resultante=emprestimo.saldo_pendente,
                data_movimento=timezone.now(),
                documento_referencia=emprestimo.requisicao.numero if emprestimo.requisicao_id else f'EMP-{emprestimo.pk}',
                observacoes=f'Confirmação de recebimento assinada por {assinatura_nome} no portal do produtor.',
                criado_por=request.user,
            )

            messages.success(request, 'Assinatura do produtor registrada com sucesso.')
            return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)
        except Exception:
            messages.error(request, 'Não foi possível processar a assinatura do produtor.')

    return render(request, 'portal_produtor/emprestimo_assinar.html', {
        'produtor': produtor,
        'emprestimo': emprestimo,
    })


@portal_login_required
def emprestimo_mensagem_create(request, pk):
    produtor = _produtor_portal_guard(request)
    emprestimo = get_object_or_404(EmprestimoProdutor, pk=pk, empresa=request.user.empresa, produtor=produtor)
    if request.method != 'POST':
        return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)

    texto_mensagem = (request.POST.get('mensagem') or '').strip()
    arquivos = request.FILES.getlist('anexos')
    if not texto_mensagem and not arquivos:
        messages.error(request, 'Informe uma mensagem ou anexe pelo menos um arquivo.')
        return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)

    criar_mensagem_emprestimo(emprestimo, request.user, 'PRODUTOR', texto_mensagem or 'Mensagem com anexo.', arquivos)
    messages.success(request, 'Mensagem enviada para a equipe interna.')
    return redirect('portal_produtor:emprestimo_detail', pk=emprestimo.pk)


@portal_login_required
def emprestimo_imprimir(request, pk):
    produtor = _produtor_portal_guard(request)
    emprestimo = get_object_or_404(
        EmprestimoProdutor.objects.select_related('produto', 'unidade_medida', 'requisicao', 'produtor'),
        pk=pk, empresa=request.user.empresa, produtor=produtor,
    )

    if emprestimo.requisicao_id:
        emprestimos_produtos_qs = EmprestimoProdutor.objects.filter(
            empresa=request.user.empresa,
            requisicao_id=emprestimo.requisicao_id,
            produtor=produtor,
        ).select_related('produto', 'unidade_medida', 'requisicao')
        seen = set()
        emprestimos_produtos = []
        for emp in emprestimos_produtos_qs:
            key = (emp.produto_id, emp.unidade_medida_id)
            if key not in seen:
                seen.add(key)
                emprestimos_produtos.append(emp)
    else:
        emprestimos_produtos = [emprestimo]

    movimentos = (
        EmprestimoMovimento.objects
        .filter(empresa=request.user.empresa, emprestimo=emprestimo)
        .select_related('criado_por')
        .order_by('data_movimento', 'id')
    )
    mensagens = emprestimo.mensagens.select_related('autor').all()

    from decimal import Decimal
    total_valor = sum(
        Decimal(emp.quantidade_emprestada or 0) * Decimal(getattr(emp.produto, 'preco_venda', 0) or 0)
        for emp in emprestimos_produtos
    )

    return render(request, 'portal_produtor/emprestimo_print.html', {
        'produtor': produtor,
        'emprestimo': emprestimo,
        'emprestimos_produtos': emprestimos_produtos,
        'movimentos': movimentos,
        'mensagens_emprestimo': mensagens,
        'empresa': request.user.empresa,
        'total_valor': total_valor,
    })


@portal_login_required
def emprestimo_mensagem_anexo_download(request, anexo_id):
    produtor = _produtor_portal_guard(request)
    anexo = get_object_or_404(
        EmprestimoMensagemAnexo.objects.select_related('mensagem__emprestimo__produtor'),
        pk=anexo_id,
        mensagem__empresa=request.user.empresa,
        mensagem__emprestimo__produtor=produtor,
    )
    emprestimo = anexo.mensagem.emprestimo
    registrar_interacao_emprestimo(
        emprestimo,
        'DOWNLOAD_ANEXO',
        f'Produtor baixou o anexo: {anexo.nome_original or anexo.arquivo.name}',
        usuario=request.user,
        sucesso=True,
    )
    return FileResponse(anexo.arquivo.open('rb'), as_attachment=True, filename=anexo.nome_original or None)


@portal_login_required
def devolucoes_programadas(request):
    produtor = _produtor_portal_guard(request)
    hoje = date.today()
    proximos_dias = hoje + timedelta(days=3)

    emprestimos_qs = EmprestimoProdutor.objects.filter(
        empresa=request.user.empresa,
        produtor=produtor,
    )
    devolucoes_pendentes = emprestimos_qs.filter(
        status__in=['PROMESSA', 'NORMAL', 'PARCIAL'],
        saldo_pendente__gt=0,
        data_promessa_devolucao__isnull=False,
        data_promessa_devolucao__gte=hoje,
    ).order_by('data_promessa_devolucao')
    devolucoes_alerta = devolucoes_pendentes.filter(data_promessa_devolucao__lte=proximos_dias)

    return render(request, 'portal_produtor/devolucoes_programadas.html', {
        'produtor': produtor,
        'devolucoes_pendentes': devolucoes_pendentes,
        'devolucoes_alerta': devolucoes_alerta,
        'hoje': hoje,
    })


@portal_login_required
def perfil_produtor(request):
    return render(request, 'portal_produtor/perfil.html')


# ---------------------------------------------------------------------------
# AJAX
# ---------------------------------------------------------------------------

@login_required
@require_POST
def emprestimo_aceite_ajax(request):
    data = json.loads(request.body.decode('utf-8'))
    pk = data.get('pk')
    aceite = data.get('aceite')
    if pk is None or aceite is None:
        return JsonResponse({'success': False, 'error': 'Dados incompletos.'}, status=400)
    try:
        emp = EmprestimoProdutor.objects.get(pk=pk, produtor=request.user.produtor_profile, empresa=request.user.empresa)
    except EmprestimoProdutor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Empréstimo não encontrado.'}, status=404)
    if emp.aceite_produtor and emp.aceite_editavel is False:
        return JsonResponse({'success': False, 'error': 'Aceite já confirmado e bloqueado.'}, status=403)
    if aceite:
        emp.aceite_produtor = True
        emp.aceite_produtor_data = timezone.now()
        emp.aceite_produtor_usuario = request.user
        emp.aceite_editavel = False
    else:
        return JsonResponse({'success': False, 'error': 'Reversão de aceite só pela empresa.'}, status=403)
    emp.save()
    return JsonResponse({'success': True, 'aceite': emp.aceite_produtor, 'data': emp.aceite_produtor_data})
