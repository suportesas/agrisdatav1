from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import EtiquetaAvulsaEditForm, LoteEtiquetaAvulsaForm
from .models import EtiquetaAvulsa, LoteEtiquetaAvulsa
from .pdf import render_etiqueta_avulsa_pdf
from .services import criar_lote_com_etiquetas


def _get_empresa(request):
    return request.user.empresa


@login_required
def lote_create(request):
    empresa = _get_empresa(request)
    if request.method == 'POST':
        form = LoteEtiquetaAvulsaForm(request.POST, empresa=empresa)
        if form.is_valid():
            lote = form.save(commit=False)
            lote.origem = 'UI'
            lote.criado_por = request.user
            criar_lote_com_etiquetas(lote, empresa)
            messages.success(request, f'Lote {lote.numero_lote} criado com {lote.total_pallets} etiqueta(s).')
            return redirect('etiquetas_avulsas:lote_detail', pk=lote.pk)
    else:
        form = LoteEtiquetaAvulsaForm(empresa=empresa)
    return render(request, 'etiquetas_avulsas/lote/form.html', {
        'form': form, 'title': 'Nova Etiqueta de Pallet Avulso',
    })


@login_required
def lote_detail(request, pk):
    empresa = _get_empresa(request)
    lote = get_object_or_404(LoteEtiquetaAvulsa, pk=pk, empresa=empresa)
    etiquetas = lote.etiquetas.filter(ativo=True).order_by('numero_sequencial')
    return render(request, 'etiquetas_avulsas/lote/detail.html', {
        'lote': lote,
        'etiquetas': etiquetas,
    })


@login_required
def lote_list(request):
    empresa = _get_empresa(request)
    qs = LoteEtiquetaAvulsa.objects.filter(empresa=empresa)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(numero_lote__icontains=q)
    paginator = Paginator(qs.order_by('-criado_em'), 25)
    return render(request, 'etiquetas_avulsas/lote/list.html', {
        'page_obj': paginator.get_page(request.GET.get('page')),
        'q': q,
    })


@login_required
@require_POST
def lote_etiquetas_pdf(request, pk):
    empresa = _get_empresa(request)
    lote = get_object_or_404(LoteEtiquetaAvulsa, pk=pk, empresa=empresa)
    ids = request.POST.getlist('etiqueta_ids')
    etiquetas = list(
        lote.etiquetas.filter(ativo=True, pk__in=ids).exclude(status='CANCELADA').order_by('numero_sequencial'))
    if not etiquetas:
        messages.warning(request, 'Selecione ao menos uma etiqueta para imprimir.')
        return redirect('etiquetas_avulsas:lote_detail', pk=pk)

    pdf = render_etiqueta_avulsa_pdf(etiquetas)
    EtiquetaAvulsa.objects.filter(pk__in=[e.pk for e in etiquetas]).update(
        status='IMPRESSA', impressa_em=timezone.now())
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiquetas-{lote.numero_lote}.pdf"'
    return resp


@login_required
def etiqueta_pdf_single(request, pk):
    empresa = _get_empresa(request)
    etiqueta = get_object_or_404(EtiquetaAvulsa, pk=pk, empresa=empresa)
    pdf = render_etiqueta_avulsa_pdf([etiqueta])
    etiqueta.status = 'IMPRESSA'
    etiqueta.impressa_em = timezone.now()
    etiqueta.save(update_fields=['status', 'impressa_em'])
    resp = HttpResponse(pdf, content_type='application/pdf')
    resp['Content-Disposition'] = f'inline; filename="etiqueta-{etiqueta.codigo_pallet}.pdf"'
    return resp


@login_required
def etiqueta_update(request, pk):
    empresa = _get_empresa(request)
    etiqueta = get_object_or_404(EtiquetaAvulsa, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = EtiquetaAvulsaEditForm(request.POST, instance=etiqueta)
        if form.is_valid():
            form.save()
            messages.success(request, f'Pallet {etiqueta.codigo_pallet} atualizado.')
            return redirect('etiquetas_avulsas:lote_detail', pk=etiqueta.lote_id)
    else:
        form = EtiquetaAvulsaEditForm(instance=etiqueta)
    return render(request, 'etiquetas_avulsas/etiqueta_form.html', {
        'form': form, 'etiqueta': etiqueta,
    })


@login_required
@require_POST
def etiqueta_cancelar(request, pk):
    empresa = _get_empresa(request)
    etiqueta = get_object_or_404(EtiquetaAvulsa, pk=pk, empresa=empresa)
    etiqueta.status = 'CANCELADA'
    etiqueta.save(update_fields=['status'])
    messages.success(request, f'Pallet {etiqueta.codigo_pallet} cancelado.')
    return redirect('etiquetas_avulsas:lote_detail', pk=etiqueta.lote_id)
