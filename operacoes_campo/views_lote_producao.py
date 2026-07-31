"""
Views para gerenciamento de Lotes de Produção — RF-109 e RF-110.
"""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from core.pagination import paginate
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone

from .models import LoteProducao, ViagemColheita


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
    page_obj, per_page, per_page_options = paginate(request, lotes)

    return render(request, 'operacoes_campo/lote_producao/lote_list.html', {
        'lotes': page_obj,
        'safras': safras,
        'status_choices': LoteProducao.STATUS_CHOICES,
        'total': page_obj.paginator.count,
        'per_page': per_page,
        'per_page_options': per_page_options,
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
        viagens = ViagemColheita.objects.filter(
            carrocao__frota__etapa=lote.etapa_colheita
        ).select_related('carrocao').order_by('data_registro')

    ordens_embalagem = lote.ordens_embalagem.select_related('responsavel').prefetch_related('tipos_embalagem').all()

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

    from embalagem.models import OrdemEmbalagem, TipoEmbalagem
    from estoque.models import Armazem, Lote, MovimentacaoEstoque
    from produtos.models import Produto

    armazens = Armazem.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    produtos = Produto.objects.filter(categoria__empresa=empresa, ativo=True).order_by('nome')
    tipos_embalagem = TipoEmbalagem.objects.filter(empresa=empresa, ativo=True).order_by('nome')

    if request.method == 'POST':
        armazem_id = request.POST.get('armazem_destino')
        produto_id = request.POST.get('produto')
        tipo_embalagem_ids = request.POST.getlist('tipo_embalagem')
        observacoes = request.POST.get('observacoes', '')

        from decimal import Decimal, InvalidOperation
        try:
            quantidade_kg = Decimal(request.POST.get('quantidade_kg') or lote.peso_total_colhido_kg)
        except InvalidOperation:
            quantidade_kg = None

        if not armazem_id:
            messages.error(request, 'Selecione o armazém de destino.')
        elif not produto_id:
            messages.error(request, 'Selecione o produto a granel colhido.')
        elif not tipo_embalagem_ids:
            messages.error(request, 'Selecione ao menos um tipo de embalagem que poderá ser usado nesta ordem.')
        elif not quantidade_kg or quantidade_kg <= 0:
            messages.error(request, 'Informe uma quantidade recebida (kg) válida.')
        else:
            from django.db import transaction
            try:
                with transaction.atomic():
                    armazem = Armazem.objects.get(pk=armazem_id, empresa=empresa)
                    produto = Produto.objects.get(pk=produto_id, categoria__empresa=empresa)
                    tipos_selecionados = list(TipoEmbalagem.objects.filter(pk__in=tipo_embalagem_ids, empresa=empresa))

                    lote.status = 'RECEBIDO_PACKING'
                    lote.data_recepcao_packing = timezone.now()
                    lote.recebido_por = request.user
                    lote.save(update_fields=['status', 'data_recepcao_packing', 'recebido_por'])

                    lote_estoque = Lote.objects.create(
                        empresa=empresa,
                        produto=produto,
                        armazem=armazem,
                        numero_lote=f"COLHEITA-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                        data_fabricacao=lote.data_colheita_inicio or timezone.now().date(),
                        quantidade_inicial=quantidade_kg,
                        quantidade_atual=quantidade_kg,
                        unidade_medida=produto.unidade_medida,
                        status='DISPONIVEL',
                        observacoes=f'Recepção do lote de colheita {lote.numero_lote} ({lote.codigo_rastreamento}).',
                        cadastrado_por=request.user,
                    )
                    MovimentacaoEstoque.objects.create(
                        empresa=empresa,
                        produto=produto,
                        lote=lote_estoque,
                        tipo='ENTRADA',
                        origem='PRODUCAO',
                        quantidade=quantidade_kg,
                        documento=lote_estoque.numero_lote,
                        observacao=f'Colheita {lote.numero_lote} — talhão {lote.talhao.nome} — recebido no packing.',
                        status='EXECUTADO',
                        cadastrado_por=request.user,
                        executado_por=request.user,
                        data_execucao=timezone.now(),
                    )

                    ordem = OrdemEmbalagem.objects.create(
                        empresa=empresa,
                        numero=OrdemEmbalagem._gerar_numero(empresa),
                        armazem_destino=armazem,
                        safra=lote.safra,
                        lote_producao=lote,
                        lote_origem=lote_estoque,
                        quantidade_entrada_kg=quantidade_kg,
                        status='ABERTA',
                        criado_por=request.user,
                    )
                    ordem.tipos_embalagem.set(tipos_selecionados)
            except Exception as e:
                messages.error(request, f'Erro ao receber o lote no packing: {e}')
            else:
                messages.success(request, f'Lote {lote.numero_lote} recebido no packing com sucesso!')
                return redirect('operacoes_campo:lote_detail', pk=pk)

    return render(request, 'operacoes_campo/lote_producao/lote_recepcao_form.html', {
        'lote': lote,
        'armazens': armazens,
        'produtos': produtos,
        'tipos_embalagem': tipos_embalagem,
    })
