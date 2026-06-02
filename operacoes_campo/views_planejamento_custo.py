"""Views do módulo Planejamento de Custo por Safra/Cultura."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum
from decimal import Decimal

from .models import PlanejamentoCustoSafra, PlanejamentoCustoItem, CustoTalhao, EtapaColheita
from cadastros.models import Safra, Talhao
from operacoes_campo.forms import PlanejamentoCustoSafraForm, PlanejamentoCustoItemForm


@login_required
def planejamento_custo_list(request):
    empresa = request.user.empresa
    plans = PlanejamentoCustoSafra.objects.filter(empresa=empresa).select_related('cultura', 'safra', 'talhao')
    return render(request, 'cadastros/planejamento_custo/planejamento_custo_list.html', {
        'plans': plans,
        'title': 'Planejamento de Custo',
    })


@login_required
def planejamento_custo_create(request):
    empresa = request.user.empresa
    safra_pre = None

    if request.method == 'POST':
        form = PlanejamentoCustoSafraForm(request.POST, user=request.user)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.empresa = empresa
            plan.criado_por = request.user
            plan.save()
            messages.success(request, f'Planejamento "{plan.nome}" criado com sucesso.')
            return redirect('operacoes_campo:planejamento_custo_detail', pk=plan.pk)
        safra_id = request.POST.get('safra') or request.GET.get('safra_id')
        if safra_id:
            try:
                safra_pre = Safra.objects.get(pk=safra_id, fazenda__empresa=empresa)
            except Safra.DoesNotExist:
                pass
    else:
        initial = {}
        safra_id = request.GET.get('safra_id')
        if safra_id:
            try:
                safra_pre = Safra.objects.select_related('cultura').get(
                    pk=safra_id, fazenda__empresa=empresa
                )
                area_ha = None
                try:
                    area_ha = safra_pre.plano.planned_area
                except Exception:
                    pass
                if not area_ha:
                    area_ha = safra_pre.talhoes.aggregate(
                        total=Sum('area_hac')
                    )['total']
                initial = {
                    'cultura': safra_pre.cultura.pk if safra_pre.cultura else None,
                    'safra': safra_pre.pk,
                    'area_ha': area_ha,
                    'nome': f"Planejamento {safra_pre.cultura.nome if safra_pre.cultura else ''} {safra_pre.ano or ''}".strip(),
                }
            except Safra.DoesNotExist:
                pass
        form = PlanejamentoCustoSafraForm(user=request.user, initial=initial)

    return render(request, 'cadastros/planejamento_custo/planejamento_custo_form.html', {
        'form': form,
        'title': 'Novo Planejamento de Custo',
        'safra_pre': safra_pre,
    })


@login_required
def planejamento_custo_detail(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    item_form = PlanejamentoCustoItemForm(user=request.user, initial={'area_ha': plan.area_ha})

    # Dados reais de custo para comparação
    custo_real = {'total': Decimal('0'), 'mao_obra': Decimal('0'), 'maquinario': Decimal('0'),
                  'insumos': Decimal('0'), 'servico': Decimal('0')}
    if plan.safra or plan.talhao:
        qs = CustoTalhao.objects.filter(empresa=empresa)
        if plan.safra:
            qs = qs.filter(safra=plan.safra)
        if plan.talhao:
            qs = qs.filter(talhao=plan.talhao)
        agg = qs.aggregate(
            mo=Sum('custo_mao_obra'), maq=Sum('custo_maquinario'),
            ins=Sum('custo_insumos'), svc=Sum('custo_servico_externo'),
        )
        custo_real['mao_obra'] = agg['mo'] or Decimal('0')
        custo_real['maquinario'] = agg['maq'] or Decimal('0')
        custo_real['insumos'] = agg['ins'] or Decimal('0')
        custo_real['servico'] = agg['svc'] or Decimal('0')
        custo_real['total'] = sum(custo_real[k] for k in ('mao_obra', 'maquinario', 'insumos', 'servico'))

    # Planejado por categoria
    itens = plan.itens.select_related('produto', 'unidade_medida').all()
    planejado_total = plan.custo_total_planejado

    variacao = custo_real['total'] - planejado_total if planejado_total > 0 else None
    variacao_pct = (variacao / planejado_total * 100).quantize(Decimal('0.1')) if planejado_total > 0 and variacao is not None else None

    return render(request, 'cadastros/planejamento_custo/planejamento_custo_detail.html', {
        'plan': plan,
        'itens': itens,
        'item_form': item_form,
        'custo_real': custo_real,
        'planejado_total': planejado_total,
        'variacao': variacao,
        'variacao_pct': variacao_pct,
        'title': plan.nome,
    })


@login_required
def planejamento_custo_item_add(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = PlanejamentoCustoItemForm(request.POST, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.planejamento = plan
            item.save()
            messages.success(request, 'Item adicionado.')
        else:
            messages.error(request, 'Erro ao adicionar item: ' + str(form.errors))
    return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)


@login_required
def planejamento_custo_item_delete(request, pk, item_pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    item = get_object_or_404(PlanejamentoCustoItem, pk=item_pk, planejamento=plan)
    item.delete()
    messages.success(request, 'Item removido.')
    return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)


@login_required
def planejamento_custo_delete(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    if request.method == 'POST':
        nome = plan.nome
        plan.delete()
        messages.success(request, f'Planejamento "{nome}" excluído.')
        return redirect('operacoes_campo:planejamento_custo_list')
    return render(request, 'cadastros/planejamento_custo/planejamento_custo_confirm_delete.html', {
        'plan': plan, 'title': f'Excluir {plan.nome}',
    })


@login_required
def ajax_preco_produto(request):
    """GET ?produto_id=X — retorna preco_custo, unidade_medida_id, sigla."""
    produto_id = request.GET.get('produto_id')
    if not produto_id:
        return JsonResponse({'error': 'produto_id required'}, status=400)
    try:
        from produtos.models import Produto
        produto = Produto.objects.select_related('unidade_medida').get(
            pk=produto_id, empresa=request.user.empresa
        )
        return JsonResponse({
            'preco_custo': str(produto.preco_custo or '0'),
            'unidade_medida_id': produto.unidade_medida_id,
            'unidade_medida_sigla': produto.unidade_medida.sigla if produto.unidade_medida else '',
        })
    except Exception:
        return JsonResponse({'error': 'not found'}, status=404)

@login_required
def ajax_safras_por_cultura(request):
    cultura_id = request.GET.get('cultura_id')
    empresa = request.user.empresa
    safras = []
    if cultura_id:
        safras = Safra.objects.filter(
            fazenda__empresa=empresa,
            cultura_id=cultura_id
        ).order_by('-ano', 'nome')
    return JsonResponse({
        'safras': [{'id': s.pk, 'nome': str(s)} for s in safras]
    })


@login_required
def ajax_talhoes_por_safra(request):
    safra_id = request.GET.get('safra_id')
    empresa = request.user.empresa
    talhoes = []
    if safra_id:
        talhoes = Talhao.objects.filter(
            empresa=empresa,
            ativo=True,
            safras__id=safra_id
        ).distinct().order_by('nome')
    return JsonResponse({
        'talhoes': [
            {'id': t.pk, 'nome': str(t), 'area_hac': str(t.area_hac)} for t in talhoes
        ]
    })