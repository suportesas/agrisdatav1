"""
Views para gerenciamento de Lotes de Produção — RF-109 e RF-110.
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone

from .models import LoteProducao


@login_required
def lote_list(request):
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    lotes = LoteProducao.objects.filter(empresa=empresa).select_related(
        'talhao', 'safra', 'cultura', 'etapa_colheita', 'criado_por'
    )

    q = request.GET.get('q', '').strip()
    if q:
        lotes = lotes.filter(
            Q(numero_lote__icontains=q) |
            Q(codigo_rastreamento__icontains=q) |
            Q(talhao__nome__icontains=q) |
            Q(safra__nome__icontains=q)
        )

    safra_id = request.GET.get('safra')
    if safra_id:
        lotes = lotes.filter(safra_id=safra_id)

    status = request.GET.get('status')
    if status:
        lotes = lotes.filter(status=status)

    from cadastros.models import Safra
    safras = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')

    lotes = lotes.order_by('-criado_em')
    paginator = Paginator(lotes, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'operacoes_campo/lote_producao/lote_list.html', {
        'lotes': page_obj,
        'safras': safras,
        'status_choices': LoteProducao.STATUS_CHOICES,
        'total': paginator.count,
    })


@login_required
def lote_detail(request, pk):
    empresa = request.user.empresa
    lote = get_object_or_404(
        LoteProducao.objects.select_related(
            'talhao', 'safra', 'cultura', 'etapa_colheita', 'criado_por', 'recebido_por'
        ),
        pk=pk, empresa=empresa,
    )

    viagens = []
    if lote.etapa_colheita_id:
        viagens = lote.etapa_colheita.viagens.select_related('carrocao').order_by('data_registro')

    ordens_embalagem = lote.ordens_embalagem.select_related('tipo_embalagem', 'responsavel').all()

    pallets = []
    for ordem in ordens_embalagem:
        pallets.extend(list(ordem.pallets.all()))

    return render(request, 'operacoes_campo/lote_producao/lote_detail.html', {
        'lote': lote,
        'viagens': viagens,
        'ordens_embalagem': ordens_embalagem,
        'pallets': pallets,
    })


@login_required
def lote_recepcao_packing(request, pk):
    """Recebe o lote no packing house e cria OrdemEmbalagem vinculada (RF-110)."""
    empresa = request.user.empresa
    lote = get_object_or_404(LoteProducao, pk=pk, empresa=empresa)

    if lote.status not in ('COLHIDO',):
        messages.warning(request, f'Lote {lote.numero_lote} já está com status "{lote.get_status_display()}".')
        return redirect('operacoes_campo:lote_detail', pk=pk)

    from embalagem.models import OrdemEmbalagem
    from estoque.models import Armazem

    armazens = Armazem.objects.filter(empresa=empresa, ativo=True).order_by('nome')

    if request.method == 'POST':
        armazem_id = request.POST.get('armazem_destino')
        quantidade_kg = request.POST.get('quantidade_kg', lote.peso_total_colhido_kg)
        observacoes = request.POST.get('observacoes', '')

        if not armazem_id:
            messages.error(request, 'Selecione o armazém de destino.')
        else:
            from django.db import transaction
            from estoque.models import Armazem
            with transaction.atomic():
                lote.status = 'RECEBIDO_PACKING'
                lote.data_recepcao_packing = timezone.now()
                lote.recebido_por = request.user
                lote.save(update_fields=['status', 'data_recepcao_packing', 'recebido_por'])

                try:
                    armazem = Armazem.objects.get(pk=armazem_id, empresa=empresa)
                    OrdemEmbalagem.objects.create(
                        empresa=empresa,
                        armazem_destino=armazem,
                        safra=lote.safra,
                        lote_producao=lote,
                        quantidade_entrada_kg=quantidade_kg,
                        status='ABERTA',
                        criado_por=request.user,
                    )
                except Exception as e:
                    messages.warning(request, f'Lote recebido, mas erro ao criar ordem de embalagem: {e}')

            messages.success(request, f'Lote {lote.numero_lote} recebido no packing com sucesso!')
            return redirect('operacoes_campo:lote_detail', pk=pk)

    return render(request, 'operacoes_campo/lote_producao/lote_recepcao_form.html', {
        'lote': lote,
        'armazens': armazens,
    })
