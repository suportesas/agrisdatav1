"""Views do módulo Planejamento de Custo por Safra/Cultura."""

from collections import defaultdict
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum

from .models import (
    PlanejamentoCustoSafra, PlanejamentoCustoItem,
    PlanejamentoCustoItemIndireto, FormacaoPreco,
    CustoTalhao, EtapaColheita,
)
from cadastros.models import Safra, Talhao
from operacoes_campo.forms import (
    PlanejamentoCustoSafraForm, PlanejamentoCustoItemForm,
    PlanejamentoCustoItemIndiretoForm, FormacaoPrecoForm,
)

FASE_ORDER = ['PREPARO_SOLO', 'PLANTIO', 'TRATOS_CULTURAIS', 'COLHEITA', 'POS_COLHEITA', 'GERAL']

TIPO_INDIRETO_COLOR = {
    'EMBALAGEM': 'primary',
    'COMISSAO': 'warning',
    'ENERGIA': 'danger',
    'FRETE': 'info',
    'OUTROS': 'secondary',
}


def _get_cotacoes():
    """Retorna as cotações USD e EUR mais recentes do BCB."""
    try:
        from faturamento.models import CotacaoBCB
        cotacao_usd = CotacaoBCB.objects.filter(moeda='USD').order_by('-data').first()
        cotacao_eur = CotacaoBCB.objects.filter(moeda='EUR').order_by('-data').first()
        return {
            'usd': cotacao_usd,
            'eur': cotacao_eur,
            'taxa_usd': (cotacao_usd.venda if cotacao_usd else None),
            'taxa_eur': (cotacao_eur.venda if cotacao_eur else None),
        }
    except Exception:
        return {'usd': None, 'eur': None, 'taxa_usd': None, 'taxa_eur': None}


@login_required
def planejamento_custo_list(request):
    empresa = request.user.empresa
    plans = (
        PlanejamentoCustoSafra.objects
        .filter(empresa=empresa)
        .select_related('cultura', 'safra', 'talhao')
        .prefetch_related('itens')
    )
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
                    area_ha = safra_pre.talhoes.aggregate(total=Sum('area_hac'))['total']
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
def planejamento_custo_edit(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = PlanejamentoCustoSafraForm(request.POST, instance=plan, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Planejamento atualizado.')
            return redirect('operacoes_campo:planejamento_custo_detail', pk=plan.pk)
    else:
        form = PlanejamentoCustoSafraForm(instance=plan, user=request.user)
    return render(request, 'cadastros/planejamento_custo/planejamento_custo_form.html', {
        'form': form,
        'title': f'Editar: {plan.nome}',
        'plan': plan,
        'editing': True,
    })


@login_required
def planejamento_custo_detail(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    item_form = PlanejamentoCustoItemForm(user=request.user, initial={'area_ha': plan.area_ha})
    indireto_form = PlanejamentoCustoItemIndiretoForm()

    # ── Itens de campo (ordenados por fase) ─────────────────────────────────
    itens = list(
        plan.itens
        .select_related('produto', 'unidade_medida')
        .all()
    )
    itens.sort(key=lambda i: (FASE_ORDER.index(i.fase) if i.fase in FASE_ORDER else 99, i.categoria))

    planejado_total = sum((i.custo_total for i in itens), Decimal('0'))

    planejado_cat = defaultdict(Decimal)
    for item in itens:
        planejado_cat[item.categoria] += item.custo_total

    # ── Custos pós-campo ────────────────────────────────────────────────────
    itens_indiretos = list(plan.itens_indiretos.all())
    for item in itens_indiretos:
        item.color = TIPO_INDIRETO_COLOR.get(item.tipo, 'secondary')

    custo_indireto_total = sum(i.custo_calculado for i in itens_indiretos if i.inclui_no_total)
    custo_indireto_excluido = sum(i.custo_calculado for i in itens_indiretos if not i.inclui_no_total)

    # ── Formação de preço ───────────────────────────────────────────────────
    try:
        formacao = plan.formacao_preco
    except FormacaoPreco.DoesNotExist:
        formacao = None

    formacao_form = FormacaoPrecoForm(instance=formacao)

    cotacoes = _get_cotacoes()

    # Calcular preços em USD e EUR se tiver formação e cotações
    preco_minimo_usd = None
    preco_minimo_eur = None
    custo_ha_usd = None
    custo_ha_eur = None
    if formacao and formacao.preco_minimo_brl:
        if cotacoes['taxa_usd']:
            preco_minimo_usd = (formacao.preco_minimo_brl / cotacoes['taxa_usd']).quantize(Decimal('0.01'))
        if cotacoes['taxa_eur']:
            preco_minimo_eur = (formacao.preco_minimo_brl / cotacoes['taxa_eur']).quantize(Decimal('0.01'))

    # custo/ha em USD/EUR
    if plan.custo_planejado_por_ha and plan.custo_planejado_por_ha > 0:
        if cotacoes['taxa_usd']:
            custo_ha_usd = (plan.custo_planejado_por_ha / cotacoes['taxa_usd']).quantize(Decimal('0.01'))
        if cotacoes['taxa_eur']:
            custo_ha_eur = (plan.custo_planejado_por_ha / cotacoes['taxa_eur']).quantize(Decimal('0.01'))

    # ── Custo real ──────────────────────────────────────────────────────────
    custo_real = {k: Decimal('0') for k in ('total', 'mao_obra', 'maquinario', 'insumos', 'servico')}
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
        custo_real['mao_obra']   = agg['mo']  or Decimal('0')
        custo_real['maquinario'] = agg['maq'] or Decimal('0')
        custo_real['insumos']    = agg['ins'] or Decimal('0')
        custo_real['servico']    = agg['svc'] or Decimal('0')
        custo_real['total'] = sum(custo_real[k] for k in ('mao_obra', 'maquinario', 'insumos', 'servico'))

    variacao = custo_real['total'] - planejado_total if planejado_total > 0 else None
    variacao_pct = (
        (variacao / planejado_total * 100).quantize(Decimal('0.1'))
        if planejado_total > 0 and variacao is not None else None
    )

    # ── Breakdown de custo real por talhão ─────────────────────────────────
    custo_por_talhao = []
    if plan.safra and not plan.talhao:
        talhoes_safra = plan.safra.talhoes.filter(empresa=empresa).order_by('nome')
        for talhao in talhoes_safra:
            agg_t = CustoTalhao.objects.filter(
                empresa=empresa, safra=plan.safra, talhao=talhao
            ).aggregate(
                mo=Sum('custo_mao_obra'), maq=Sum('custo_maquinario'),
                ins=Sum('custo_insumos'), svc=Sum('custo_servico_externo'),
                area=Sum('area_executada_ha'),
            )
            total_t = sum(agg_t[k] or Decimal('0') for k in ('mo', 'maq', 'ins', 'svc'))
            if total_t > 0:
                area_t = agg_t['area'] or Decimal('0')
                custo_por_talhao.append({
                    'talhao': talhao,
                    'total': total_t,
                    'mo':    agg_t['mo']  or Decimal('0'),
                    'maq':   agg_t['maq'] or Decimal('0'),
                    'ins':   agg_t['ins'] or Decimal('0'),
                    'svc':   agg_t['svc'] or Decimal('0'),
                    'area':  area_t,
                    'custo_ha': (total_t / area_t).quantize(Decimal('0.01')) if area_t else Decimal('0'),
                })

    # ── Comparativo por categoria ───────────────────────────────────────────
    cat_labels = {
        'MO': ('Mão de Obra', 'mao_obra'),
        'MAQUINARIO': ('Maquinário', 'maquinario'),
        'INSUMO': ('Insumos', 'insumos'),
        'SERVICO_EXTERNO': ('Serviço Externo', 'servico'),
    }
    comparativo_cat = []
    for cat_key, (cat_label, real_key) in cat_labels.items():
        plan_val = planejado_cat.get(cat_key, Decimal('0'))
        real_val = custo_real[real_key]
        if plan_val or real_val:
            var = real_val - plan_val
            var_pct = (var / plan_val * 100).quantize(Decimal('0.1')) if plan_val else None
            comparativo_cat.append({
                'label': cat_label,
                'planejado': plan_val,
                'real': real_val,
                'variacao': var,
                'variacao_pct': var_pct,
            })

    # ── DRE Real (colheita concluída) ───────────────────────────────────────
    dre = None
    etapas_colheita = []
    if plan.safra:
        qs_etapas = EtapaColheita.objects.filter(
            empresa=empresa, safra=plan.safra, status='CONCLUIDA',
        ).select_related('talhao', 'os')
        if plan.talhao:
            qs_etapas = qs_etapas.filter(talhao=plan.talhao)
        etapas_colheita = list(qs_etapas.order_by('os__data_inicio'))

        if etapas_colheita:
            producao_real_kg = sum(e.total_liquido_kg for e in etapas_colheita)
            kg_pu = plan.kg_por_unidade or Decimal('60')
            producao_real_unid = (producao_real_kg / kg_pu).quantize(Decimal('0.01')) if kg_pu else Decimal('0')

            receita_real = None
            if plan.preco_venda_unitario and producao_real_unid:
                receita_real = (producao_real_unid * plan.preco_venda_unitario).quantize(Decimal('0.01'))

            custo_real_total_dre = custo_real['total'] + (custo_indireto_total if formacao and formacao.inclui_custos_indiretos else Decimal('0'))

            lucro_real = None
            margem_real_pct = None
            if receita_real is not None:
                lucro_real = (receita_real - custo_real_total_dre).quantize(Decimal('0.01'))
                if receita_real > 0:
                    margem_real_pct = (lucro_real / receita_real * 100).quantize(Decimal('0.1'))

            dre = {
                'producao_real_kg': producao_real_kg,
                'producao_real_unid': producao_real_unid,
                'unidade': plan.unidade_producao,
                'receita_real': receita_real,
                'custo_real_total': custo_real_total_dre,
                'lucro_real': lucro_real,
                'margem_real_pct': margem_real_pct,
            }

    return render(request, 'cadastros/planejamento_custo/planejamento_custo_detail.html', {
        'plan': plan,
        'itens': itens,
        'item_form': item_form,
        'custo_real': custo_real,
        'planejado_total': planejado_total,
        'variacao': variacao,
        'variacao_pct': variacao_pct,
        'comparativo_cat': comparativo_cat,
        'custo_por_talhao': custo_por_talhao,
        # Pós-campo
        'itens_indiretos': itens_indiretos,
        'indireto_form': indireto_form,
        'custo_indireto_total': custo_indireto_total,
        'custo_indireto_excluido': custo_indireto_excluido,
        # Formação de preço
        'formacao': formacao,
        'formacao_form': formacao_form,
        'cotacoes': cotacoes,
        'preco_minimo_usd': preco_minimo_usd,
        'preco_minimo_eur': preco_minimo_eur,
        'custo_ha_usd': custo_ha_usd,
        'custo_ha_eur': custo_ha_eur,
        # DRE real
        'dre': dre,
        'etapas_colheita': etapas_colheita,
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
def planejamento_custo_indireto_add(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = PlanejamentoCustoItemIndiretoForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.planejamento = plan
            item.save()
            messages.success(request, 'Custo pós-campo adicionado.')
        else:
            messages.error(request, 'Erro: ' + str(form.errors))
    return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)


@login_required
def planejamento_custo_indireto_delete(request, pk, item_pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    item = get_object_or_404(PlanejamentoCustoItemIndireto, pk=item_pk, planejamento=plan)
    item.delete()
    messages.success(request, 'Custo pós-campo removido.')
    return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)


@login_required
def planejamento_custo_formacao_preco_salvar(request, pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    if request.method != 'POST':
        return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)

    try:
        formacao = plan.formacao_preco
    except FormacaoPreco.DoesNotExist:
        formacao = None

    form = FormacaoPrecoForm(request.POST, instance=formacao)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.planejamento = plan
        obj.save()
        messages.success(request, 'Formação de preço salva.')
    else:
        messages.error(request, 'Erro ao salvar formação de preço: ' + str(form.errors))
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


# ── AJAX endpoints ───────────────────────────────────────────────────────────

@login_required
def ajax_preco_produto(request):
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
            fazenda__empresa=empresa, cultura_id=cultura_id
        ).order_by('-ano', 'nome')
    return JsonResponse({'safras': [{'id': s.pk, 'nome': str(s)} for s in safras]})


@login_required
def ajax_talhoes_por_safra(request):
    safra_id = request.GET.get('safra_id')
    empresa = request.user.empresa
    talhoes = []
    if safra_id:
        talhoes = Talhao.objects.filter(
            empresa=empresa, ativo=True, safras__id=safra_id
        ).distinct().order_by('nome')
    return JsonResponse({
        'talhoes': [{'id': t.pk, 'nome': str(t), 'area_hac': str(t.area_hac)} for t in talhoes]
    })


@login_required
def ajax_cotacoes_bcb(request):
    """Retorna cotações USD e EUR mais recentes do BCB."""
    cotacoes = _get_cotacoes()
    return JsonResponse({
        'usd': {
            'taxa': str(cotacoes['taxa_usd']) if cotacoes['taxa_usd'] else None,
            'data': cotacoes['usd'].data.strftime('%d/%m/%Y') if cotacoes['usd'] else None,
        },
        'eur': {
            'taxa': str(cotacoes['taxa_eur']) if cotacoes['taxa_eur'] else None,
            'data': cotacoes['eur'].data.strftime('%d/%m/%Y') if cotacoes['eur'] else None,
        },
    })


@login_required
def ajax_energia_periodo(request):
    """Soma o valor faturado de energia no período (mes_referencia entre data_ini e data_fim)."""
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    if not data_ini or not data_fim:
        return JsonResponse({'error': 'data_ini e data_fim são obrigatórios'}, status=400)
    try:
        from energia.models import LancamentoMensal
        total = LancamentoMensal.objects.filter(
            empresa=request.user.empresa,
            mes_referencia__range=(data_ini, data_fim),
        ).aggregate(total=Sum('valor_faturado_rs'))['total'] or Decimal('0')
        return JsonResponse({'total': str(total)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
