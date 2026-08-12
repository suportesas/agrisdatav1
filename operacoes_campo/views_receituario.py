"""
Views para o Receituário Agronômico — documento técnico que autoriza a
aplicação de um defensivo contra uma praga específica, ligado a um item de
insumo da OS (que já carrega produto+praga). Não bloqueia o fluxo da OS:
serve como registro de apoio/compliance, com fluxo de aprovação próprio.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.exceptions import ValidationError
from decimal import Decimal

from core.pagination import paginate
from .models import OrdemServico, OrdemServicoInsumo, Receituario, cultura_atual_talhao
from .forms import ReceituarioForm


def _pode_decidir_receituario(user):
    """Quem pode aprovar/rejeitar um receituário — mesmo critério de
    `requisicao_aprovar` (cadastros/views_requisicao.py)."""
    return bool(
        user.is_superuser
        or (hasattr(user, 'is_admin_empresa') and user.is_admin_empresa())
        or getattr(user, 'tipo', None) in ('ADMIN', 'GERENTE')
    )


def _defensivo_recomendado(produto, cultura, praga):
    """Busca o registro de ProdutoDefensivoCultura para o par produto+cultura+praga
    exato de um item de insumo, para servir de base (snapshot) ao Receituário.
    Mesma fonte de dados usada por `views_os.ajax_recomendacao_defensivo`, mas
    para um produto específico em vez de ranquear várias opções."""
    from produtos.models import ProdutoDefensivoCultura
    if not (produto and cultura and praga):
        return None
    return ProdutoDefensivoCultura.objects.filter(
        produto=produto, cultura=cultura, praga=praga,
    ).select_related('unidade_dosagem').first()


@login_required
def receituario_create(request, pk, insumo_pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    insumo = get_object_or_404(OrdemServicoInsumo, pk=insumo_pk, os=os_obj, empresa=empresa)

    if not insumo.praga_id:
        messages.error(request, 'Defina a praga/doença alvo no insumo antes de emitir um receituário.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    ativo = insumo.receituarios.filter(status__in=['RASCUNHO', 'APROVADO']).first()
    if ativo:
        messages.info(request, f'Este insumo já tem o receituário {ativo.numero} ({ativo.get_status_display()}).')
        return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=ativo.pk)

    cultura = cultura_atual_talhao(os_obj.talhao, os_obj.safra)
    if not cultura:
        messages.error(request, 'Não foi possível identificar a cultura desta OS (defina a cultura na safra do talhão).')
        return redirect('operacoes_campo:os_detail', pk=pk)

    dc = _defensivo_recomendado(insumo.produto, cultura, insumo.praga)

    if request.method == 'POST':
        form = ReceituarioForm(request.POST, empresa=empresa)
        if form.is_valid():
            receituario = form.save(commit=False)
            receituario.empresa = empresa
            receituario.os = os_obj
            receituario.insumo = insumo
            receituario.cultura = cultura
            receituario.praga = insumo.praga
            receituario.produto = insumo.produto
            if dc:
                receituario.carencia_dias = dc.carencia
                receituario.quantidade_maxima_aplicacoes = dc.quantidade_maxima_aplicacoes
                receituario.intervalo_reaplicacao_dias = dc.intervalo_reaplicacao
                receituario.efetividade_pct = dc.efetividade_pct
                receituario.custo_relativo = dc.custo_relativo
            receituario.created_by = request.user
            receituario.save()
            for alerta in receituario.alertas_faixa:
                messages.warning(request, alerta)
            messages.success(request, f'Receituário {receituario.numero} criado como rascunho.')
            return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario.pk)
    else:
        initial = {}
        if dc:
            initial['dosagem_aplicar'] = ((dc.dosagem_minima + dc.dosagem_maxima) / 2).quantize(Decimal('0.001'))
            initial['unidade_dosagem'] = dc.unidade_dosagem_id
            initial['volume_calda'] = ((dc.volume_calda_minimo + dc.volume_calda_maximo) / 2).quantize(Decimal('0.01'))
        form = ReceituarioForm(empresa=empresa, initial=initial)

    return render(request, 'cadastros/receituario/form.html', {
        'os': os_obj,
        'insumo': insumo,
        'cultura': cultura,
        'recomendacao': dc,
        'form': form,
        'titulo': f'Emitir Receituário — {os_obj.numero}',
    })


@login_required
def receituario_detail(request, pk, receituario_pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    receituario = get_object_or_404(
        Receituario.objects.select_related(
            'produto', 'praga', 'cultura', 'unidade_dosagem', 'responsavel_tecnico',
            'aprovado_por', 'created_by', 'os', 'os__talhao',
        ),
        pk=receituario_pk, os=os_obj, empresa=empresa,
    )
    return render(request, 'cadastros/receituario/detail.html', {
        'os': os_obj,
        'receituario': receituario,
        'pode_decidir': _pode_decidir_receituario(request.user),
    })


@login_required
def receituario_edit(request, pk, receituario_pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    receituario = get_object_or_404(Receituario, pk=receituario_pk, os=os_obj, empresa=empresa)

    if receituario.status != 'RASCUNHO':
        messages.error(request, 'Apenas receituários em rascunho podem ser editados.')
        return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)

    dc = _defensivo_recomendado(receituario.produto, receituario.cultura, receituario.praga)

    if request.method == 'POST':
        form = ReceituarioForm(request.POST, instance=receituario, empresa=empresa)
        if form.is_valid():
            form.save()
            for alerta in receituario.alertas_faixa:
                messages.warning(request, alerta)
            messages.success(request, f'Receituário {receituario.numero} atualizado.')
            return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)
    else:
        form = ReceituarioForm(instance=receituario, empresa=empresa)

    return render(request, 'cadastros/receituario/form.html', {
        'os': os_obj,
        'insumo': receituario.insumo,
        'cultura': receituario.cultura,
        'recomendacao': dc,
        'form': form,
        'receituario': receituario,
        'titulo': f'Editar Receituário {receituario.numero}',
    })


@login_required
def receituario_aprovar(request, pk, receituario_pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    receituario = get_object_or_404(Receituario, pk=receituario_pk, os=os_obj, empresa=empresa)

    if not _pode_decidir_receituario(request.user):
        messages.error(request, 'Você não tem permissão para aprovar receituários.')
        return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)

    if request.method == 'POST':
        try:
            receituario.aprovar(request.user)
            messages.success(request, f'Receituário {receituario.numero} aprovado.')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)


@login_required
def receituario_rejeitar(request, pk, receituario_pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    receituario = get_object_or_404(Receituario, pk=receituario_pk, os=os_obj, empresa=empresa)

    if not _pode_decidir_receituario(request.user):
        messages.error(request, 'Você não tem permissão para rejeitar receituários.')
        return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)

    if request.method == 'POST':
        motivo = request.POST.get('motivo_rejeicao', '').strip()
        if not motivo:
            messages.error(request, 'Informe o motivo da rejeição.')
            return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)
        try:
            receituario.rejeitar(request.user, motivo)
            messages.warning(request, f'Receituário {receituario.numero} rejeitado.')
        except ValidationError as e:
            messages.error(request, str(e))
    return redirect('operacoes_campo:receituario_detail', pk=pk, receituario_pk=receituario_pk)


@login_required
def receituario_list(request):
    empresa = request.user.empresa
    qs = Receituario.objects.filter(empresa=empresa).select_related(
        'os', 'produto', 'praga', 'cultura', 'responsavel_tecnico'
    ).order_by('-created_at')

    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    if search:
        qs = qs.filter(
            Q(numero__icontains=search)
            | Q(produto__nome__icontains=search)
            | Q(praga__nome_comum__icontains=search)
            | Q(os__numero__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)

    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'cadastros/receituario/list.html', {
        'receituarios': page_obj,
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'status_choices': Receituario.STATUS_CHOICES,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })
