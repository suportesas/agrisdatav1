"""Views do módulo Estufas e Transplantio (RF-1200 a RF-1254)."""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import (
    AplicacaoEstufaForm,
    EstufaForm,
    LoteMudaForm,
    MonitoramentoEstufaForm,
    PerdaEstufaForm,
    ReplantioTalhaoForm,
    TransplantioForm,
)
from .models import (
    AplicacaoEstufa,
    Estufa,
    LoteMuda,
    MonitoramentoEstufa,
    PerdaEstufa,
    ReplantioTalhao,
    Transplantio,
)
from cadastros.models import Cultura, Fazenda, Safra, Talhao


# ============================================================
# GRUPO 1 — ESTUFA
# ============================================================

@login_required
def estufa_list(request):
    empresa = request.user.empresa
    estufas = Estufa.objects.filter(empresa=empresa).select_related('fazenda')

    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        estufas = estufas.filter(fazenda_id=fazenda_id)

    fazendas = Fazenda.objects.filter(empresa=empresa, ativa=True)

    paginator = Paginator(estufas.order_by('nome'), 20)
    page = request.GET.get('page', 1)
    try:
        estufas_page = paginator.page(page)
    except Exception:
        estufas_page = paginator.page(1)

    return render(request, 'cadastros/estufas/estufa_list.html', {
        'estufas': estufas_page,
        'fazendas': fazendas,
        'fazenda_selecionada': fazenda_id,
        'title': 'Estufas',
    })


@login_required
def estufa_create(request):
    if request.method == 'POST':
        form = EstufaForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.cadastrado_por = request.user
            obj.save()
            messages.success(request, f'Estufa "{obj.nome}" cadastrada com sucesso.')
            return redirect('estufas:estufa_detail', pk=obj.pk)
    else:
        form = EstufaForm(user=request.user)
    return render(request, 'cadastros/estufas/estufa_form.html', {
        'form': form,
        'title': 'Nova Estufa',
    })


@login_required
def estufa_detail(request, pk):
    obj = get_object_or_404(Estufa, pk=pk, empresa=request.user.empresa)
    lotes = obj.lotes.all().order_by('-data_semeadura')
    return render(request, 'cadastros/estufas/estufa_detail.html', {
        'obj': obj,
        'lotes': lotes,
        'title': f'Estufa — {obj.nome}',
    })


@login_required
def estufa_update(request, pk):
    obj = get_object_or_404(Estufa, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = EstufaForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estufa atualizada com sucesso.')
            return redirect('estufas:estufa_detail', pk=obj.pk)
    else:
        form = EstufaForm(instance=obj, user=request.user)
    return render(request, 'cadastros/estufas/estufa_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Estufa',
    })


@login_required
def estufa_delete(request, pk):
    obj = get_object_or_404(Estufa, pk=pk, empresa=request.user.empresa)
    lotes_ativos = obj.get_lotes_ativos()
    if request.method == 'POST':
        if lotes_ativos.exists():
            messages.error(request, 'Não é possível excluir: existem lotes ativos nesta estufa.')
            return redirect('estufas:estufa_detail', pk=obj.pk)
        obj.delete()
        messages.success(request, 'Estufa excluída.')
        return redirect('estufas:estufa_list')
    return render(request, 'cadastros/estufas/estufa_confirm_delete.html', {
        'obj': obj,
        'lotes_ativos': lotes_ativos,
    })


# ============================================================
# GRUPO 2 — LOTE DE MUDAS
# ============================================================

@login_required
def lote_muda_list(request):
    empresa = request.user.empresa
    qs = LoteMuda.objects.filter(empresa=empresa).select_related('estufa', 'cultura', 'estufa__fazenda')

    status = request.GET.get('status')
    estufa_id = request.GET.get('estufa')
    cultura_id = request.GET.get('cultura')

    if status:
        qs = qs.filter(status=status)
    if estufa_id:
        qs = qs.filter(estufa_id=estufa_id)
    if cultura_id:
        qs = qs.filter(cultura_id=cultura_id)

    estufas = Estufa.objects.filter(empresa=empresa, ativo=True)
    culturas = Cultura.objects.filter(empresa=empresa)

    # Contagem por status para exibir badges informativos
    contagem_status = dict(
        LoteMuda.objects.filter(empresa=empresa)
        .values_list('status')
        .annotate(total=Count('id'))
    )

    paginator = Paginator(qs.order_by('-data_semeadura'), 20)
    page = request.GET.get('page', 1)
    try:
        lotes_page = paginator.page(page)
    except Exception:
        lotes_page = paginator.page(1)

    return render(request, 'cadastros/estufas/lote_muda_list.html', {
        'lotes': lotes_page,
        'estufas': estufas,
        'culturas': culturas,
        'status_choices': LoteMuda.STATUS_CHOICES,
        'status_selecionado': status,
        'estufa_selecionada': estufa_id,
        'cultura_selecionada': cultura_id,
        'contagem_status': contagem_status,
        'title': 'Lotes de Mudas',
    })


@login_required
def lote_muda_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = LoteMudaForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.cadastrado_por = request.user
            if not obj.codigo_lote:
                obj.codigo_lote = LoteMuda.gerar_codigo_lote(empresa.pk)
            obj.save()
            messages.success(request, f'Lote {obj.codigo_lote} criado com sucesso.')
            return redirect('estufas:lote_muda_detail', pk=obj.pk)
    else:
        form = LoteMudaForm(user=request.user)
    return render(request, 'cadastros/estufas/lote_muda_form.html', {
        'form': form,
        'title': 'Novo Lote de Mudas',
    })


@login_required
def lote_muda_detail(request, pk):
    lote = get_object_or_404(LoteMuda, pk=pk, empresa=request.user.empresa)
    proximo_status = LoteMuda.STATUS_AVANCAR.get(lote.status)
    perda_form = PerdaEstufaForm(user=request.user)
    aplicacao_form = AplicacaoEstufaForm(user=request.user)
    monitoramento_form = MonitoramentoEstufaForm(user=request.user)
    return render(request, 'cadastros/estufas/lote_muda_detail.html', {
        'lote': lote,
        'proximo_status': proximo_status,
        'perda_form': perda_form,
        'aplicacao_form': aplicacao_form,
        'monitoramento_form': monitoramento_form,
        'title': f'Lote {lote.codigo_lote}',
    })


@login_required
def lote_muda_update(request, pk):
    lote = get_object_or_404(LoteMuda, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = LoteMudaForm(request.POST, instance=lote, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote atualizado com sucesso.')
            return redirect('estufas:lote_muda_detail', pk=lote.pk)
    else:
        form = LoteMudaForm(instance=lote, user=request.user)
    return render(request, 'cadastros/estufas/lote_muda_form.html', {
        'form': form,
        'obj': lote,
        'title': f'Editar Lote {lote.codigo_lote}',
    })


@login_required
@require_POST
def lote_muda_avancar_status(request, pk):
    lote = get_object_or_404(LoteMuda, pk=pk, empresa=request.user.empresa)
    proximo = LoteMuda.STATUS_AVANCAR.get(lote.status)
    if proximo:
        lote.status = proximo
        lote.save(update_fields=['status'])
        messages.success(request, f'Status do lote atualizado para "{lote.get_status_display()}".')
    else:
        messages.warning(request, 'O lote não pode avançar de status nesta etapa.')
    return redirect('estufas:lote_muda_detail', pk=pk)


# ============================================================
# GRUPO 3 — REGISTROS INLINE DO LOTE
# ============================================================

@login_required
@require_POST
def perda_estufa_create(request, lote_pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    form = PerdaEstufaForm(request.POST, user=request.user)
    if form.is_valid():
        perda = form.save(commit=False)
        perda.lote_muda = lote
        try:
            perda.full_clean()
            perda.save()
            messages.success(request, f'{perda.quantidade_perdida} mudas registradas como perda.')
        except Exception as e:
            messages.error(request, str(e))
    else:
        messages.error(request, 'Dados inválidos para registrar a perda.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


@login_required
@require_POST
def perda_estufa_delete(request, lote_pk, pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    perda = get_object_or_404(PerdaEstufa, pk=pk, lote_muda=lote)
    perda.delete()
    messages.success(request, 'Registro de perda removido.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


@login_required
@require_POST
def aplicacao_estufa_create(request, lote_pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    form = AplicacaoEstufaForm(request.POST, user=request.user)
    if form.is_valid():
        aplic = form.save(commit=False)
        aplic.lote_muda = lote
        # Auto-preenche custo unitário a partir do preço de custo do produto
        if not aplic.custo_unitario:
            preco_custo = getattr(aplic.produto, 'preco_custo', None)
            if preco_custo:
                aplic.custo_unitario = preco_custo
        aplic.save()
        messages.success(request, 'Aplicação registrada com sucesso.')
    else:
        messages.error(request, 'Dados inválidos para a aplicação.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


@login_required
@require_POST
def aplicacao_estufa_delete(request, lote_pk, pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    aplic = get_object_or_404(AplicacaoEstufa, pk=pk, lote_muda=lote)
    aplic.delete()
    messages.success(request, 'Aplicação removida.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


@login_required
@require_POST
def monitoramento_estufa_create(request, lote_pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    form = MonitoramentoEstufaForm(request.POST, user=request.user)
    if form.is_valid():
        mon = form.save(commit=False)
        mon.lote_muda = lote
        mon.save()
        messages.success(request, 'Monitoramento registrado.')
    else:
        messages.error(request, 'Dados inválidos para o monitoramento.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


@login_required
@require_POST
def monitoramento_estufa_delete(request, lote_pk, pk):
    lote = get_object_or_404(LoteMuda, pk=lote_pk, empresa=request.user.empresa)
    mon = get_object_or_404(MonitoramentoEstufa, pk=pk, lote_muda=lote)
    mon.delete()
    messages.success(request, 'Monitoramento removido.')
    return redirect('estufas:lote_muda_detail', pk=lote_pk)


# ============================================================
# GRUPO 4 — TRANSPLANTIO
# ============================================================

@login_required
def transplantio_list(request):
    empresa = request.user.empresa
    qs = Transplantio.objects.filter(empresa=empresa).select_related(
        'lote_muda', 'talhao', 'safra', 'responsavel',
    )

    if request.GET.get('lote'):
        qs = qs.filter(lote_muda_id=request.GET['lote'])
    if request.GET.get('talhao'):
        qs = qs.filter(talhao_id=request.GET['talhao'])
    if request.GET.get('safra'):
        qs = qs.filter(safra_id=request.GET['safra'])

    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True)
    safras = Safra.objects.filter(fazenda__empresa=empresa)

    paginator = Paginator(qs.order_by('-data_transplantio'), 20)
    page = request.GET.get('page', 1)
    try:
        transplantios_page = paginator.page(page)
    except Exception:
        transplantios_page = paginator.page(1)

    return render(request, 'cadastros/estufas/transplantio_list.html', {
        'transplantios': transplantios_page,
        'talhoes': talhoes,
        'safras': safras,
        'talhao_selecionado': request.GET.get('talhao'),
        'safra_selecionada': request.GET.get('safra'),
        'title': 'Transplantios',
    })


@login_required
def transplantio_create(request):
    empresa = request.user.empresa
    lotes_prontos = LoteMuda.objects.filter(empresa=empresa, status='PRONTO').select_related('cultura')

    if request.method == 'POST':
        form = TransplantioForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.cadastrado_por = request.user
            try:
                obj.full_clean()
                obj.save()
                messages.success(request, f'Transplantio registrado: {obj.quantidade_transplantada} mudas → {obj.talhao.nome}.')
                return redirect('estufas:transplantio_detail', pk=obj.pk)
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = TransplantioForm(user=request.user)

    return render(request, 'cadastros/estufas/transplantio_form.html', {
        'form': form,
        'lotes_prontos': lotes_prontos,
        'title': 'Novo Transplantio',
    })


@login_required
def transplantio_detail(request, pk):
    obj = get_object_or_404(Transplantio, pk=pk, empresa=request.user.empresa)
    return render(request, 'cadastros/estufas/transplantio_detail.html', {
        'obj': obj,
        'title': f'Transplantio — {obj.lote_muda.codigo_lote}',
    })


# ============================================================
# GRUPO 5 — REPLANTIO
# ============================================================

@login_required
def replantio_list(request):
    empresa = request.user.empresa
    qs = ReplantioTalhao.objects.filter(empresa=empresa).select_related('talhao', 'safra')

    if request.GET.get('talhao'):
        qs = qs.filter(talhao_id=request.GET['talhao'])
    if request.GET.get('safra'):
        qs = qs.filter(safra_id=request.GET['safra'])
    if request.GET.get('motivo'):
        qs = qs.filter(motivo_perda=request.GET['motivo'])

    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True)
    safras = Safra.objects.filter(fazenda__empresa=empresa)

    paginator = Paginator(qs.order_by('-data_replantio'), 20)
    page = request.GET.get('page', 1)
    try:
        replantios_page = paginator.page(page)
    except Exception:
        replantios_page = paginator.page(1)

    return render(request, 'cadastros/estufas/replantio_list.html', {
        'replantios': replantios_page,
        'talhoes': talhoes,
        'safras': safras,
        'motivo_choices': ReplantioTalhao.MOTIVO_CHOICES,
        'talhao_selecionado': request.GET.get('talhao'),
        'safra_selecionada': request.GET.get('safra'),
        'motivo_selecionado': request.GET.get('motivo'),
        'title': 'Replantios',
    })


@login_required
def replantio_create(request):
    if request.method == 'POST':
        form = ReplantioTalhaoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.cadastrado_por = request.user  # FIX: estava faltando
            obj.save()
            messages.success(request, f'Replantio de {obj.quantidade} mudas registrado.')
            return redirect('estufas:replantio_detail', pk=obj.pk)
    else:
        form = ReplantioTalhaoForm(user=request.user)
    return render(request, 'cadastros/estufas/replantio_form.html', {
        'form': form,
        'title': 'Novo Replantio',
    })


@login_required
def replantio_detail(request, pk):
    obj = get_object_or_404(ReplantioTalhao, pk=pk, empresa=request.user.empresa)
    return render(request, 'cadastros/estufas/replantio_detail.html', {
        'obj': obj,
        'title': f'Replantio — {obj.talhao.nome}',
    })


# ============================================================
# GRUPO 6 — DASHBOARD
# ============================================================

@login_required
def dashboard_estufas(request):
    empresa = request.user.empresa

    lotes_por_status = (
        LoteMuda.objects.filter(empresa=empresa)
        .values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )

    status_display = dict(LoteMuda.STATUS_CHOICES)
    status_labels_display = [status_display.get(item['status'], item['status']) for item in lotes_por_status]
    status_data = [item['total'] for item in lotes_por_status]

    ultimos_transplantios = Transplantio.objects.filter(empresa=empresa).select_related(
        'lote_muda', 'talhao',
    ).order_by('-data_transplantio')[:10]

    total_lotes = LoteMuda.objects.filter(empresa=empresa).count()
    lotes_prontos = LoteMuda.objects.filter(empresa=empresa, status='PRONTO').count()
    total_transplantados = Transplantio.objects.filter(empresa=empresa).aggregate(
        t=Sum('quantidade_transplantada'),
    )['t'] or 0

    return render(request, 'cadastros/estufas/dashboard_estufas.html', {
        'status_labels': json.dumps(status_labels_display),
        'status_data': json.dumps(status_data),
        'ultimos_transplantios': ultimos_transplantios,
        'total_lotes': total_lotes,
        'lotes_prontos': lotes_prontos,
        'total_transplantados': total_transplantados,
        'title': 'Dashboard — Estufas e Mudas',
    })
