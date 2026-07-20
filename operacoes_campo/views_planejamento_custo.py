"""Views do módulo Planejamento de Custo por Safra/Cultura."""

from collections import defaultdict
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Sum

from .models import (
    PlanejamentoCustoSafra, PlanejamentoCustoItem,
    PlanejamentoCustoItemIndireto, FormacaoPreco,
    CustoTalhao, EtapaColheita, SubcategoriaItemCusto,
    OrdemServico,
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
        .order_by('-data_criacao')
    )

    paginator = Paginator(plans, 20)
    page = request.GET.get('page', 1)
    try:
        plans_page = paginator.page(page)
    except Exception:
        plans_page = paginator.page(1)

    return render(request, 'cadastros/planejamento_custo/planejamento_custo_list.html', {
        'plans': plans_page,
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
                safra_pre = Safra.objects.get(
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
        .select_related('produto', 'unidade_medida', 'subcategoria')
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

    return render(request, 'cadastros/planejamento_custo/planejamento_custo_detail.html', {
        'plan': plan,
        'itens': itens,
        'item_form': item_form,
        'planejado_total': planejado_total,
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
            subcategoria_id = request.POST.get('subcategoria_id')
            if subcategoria_id:
                try:
                    item.subcategoria = SubcategoriaItemCusto.objects.get(pk=subcategoria_id)
                except SubcategoriaItemCusto.DoesNotExist:
                    pass
            if item.tipo_servico and item.tipo_servico.tipo_legado:
                item.fase = item.tipo_servico.tipo_legado
            item.save()
            messages.success(request, 'Item adicionado.')
        else:
            messages.error(request, 'Erro ao adicionar item: ' + str(form.errors))
    return redirect('operacoes_campo:planejamento_custo_detail', pk=pk)


@login_required
def planejamento_custo_item_edit(request, pk, item_pk):
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    item = get_object_or_404(PlanejamentoCustoItem, pk=item_pk, planejamento=plan)
    if request.method == 'POST':
        form = PlanejamentoCustoItemForm(request.POST, instance=item, user=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            subcategoria_id = request.POST.get('subcategoria_id')
            if subcategoria_id:
                try:
                    updated.subcategoria = SubcategoriaItemCusto.objects.get(pk=subcategoria_id)
                except SubcategoriaItemCusto.DoesNotExist:
                    updated.subcategoria = None
            else:
                updated.subcategoria = None
            if updated.tipo_servico and updated.tipo_servico.tipo_legado:
                updated.fase = updated.tipo_servico.tipo_legado
            updated.save()
            messages.success(request, 'Item atualizado.')
        else:
            messages.error(request, 'Erro ao atualizar item: ' + str(form.errors))
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
            pk=produto_id, categoria__empresa=request.user.empresa
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
def ajax_talhoes_comparativo(request, pk):
    """Retorna talhões com custo real registrado, filtrados pela cultura do plano."""
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    talhoes_qs = (
        Talhao.objects
        .filter(
            empresa=empresa,
            ativo=True,
            pk__in=CustoTalhao.objects.filter(empresa=empresa).values('talhao_id'),
        )
        .order_by('nome')
    )
    if plan.cultura_id:
        talhoes_qs = talhoes_qs.filter(safras__cultura=plan.cultura).distinct()
    return JsonResponse({
        'talhoes': [{'id': t.pk, 'nome': t.nome, 'area': str(t.area_hac)} for t in talhoes_qs]
    })


@login_required
def ajax_comparativo_talhao(request, pk):
    """Retorna comparativo planejado (re-escalado) vs. realizado para um talhão.

    Se o plano tem itens com tipo_servico, agrupa por tipo_servico (modo rico).
    Caso contrário, usa o fallback por categoria (planos sem tipo_servico).
    """
    empresa = request.user.empresa
    plan = get_object_or_404(PlanejamentoCustoSafra, pk=pk, empresa=empresa)
    talhao_id = request.GET.get('talhao_id')
    if not talhao_id:
        return JsonResponse({'error': 'talhao_id obrigatório'}, status=400)

    talhao = get_object_or_404(Talhao, pk=talhao_id, empresa=empresa)

    agg_geral = CustoTalhao.objects.filter(empresa=empresa, talhao=talhao).aggregate(
        mo=Sum('custo_mao_obra'), maq=Sum('custo_maquinario'),
        ins=Sum('custo_insumos'), svc=Sum('custo_servico_externo'),
        area=Sum('area_executada_ha'),
    )
    area_real = Decimal(str(agg_geral['area'] or 0)) or talhao.area_hac or plan.area_ha or Decimal('1')
    area_plan = plan.area_ha or Decimal('1')
    fator = area_real / area_plan

    itens_com_tipo = plan.itens.filter(tipo_servico__isnull=False).select_related('tipo_servico', 'subtipo_servico')

    if itens_com_tipo.exists():
        # ── Modo por TipoServiço ──
        os_qs = OrdemServico.objects.filter(
            empresa=empresa, talhao=talhao, status='CONCLUIDA',
            custo_talhao__isnull=False, tipo_servico__isnull=False,
        )

        plan_por_tipo = defaultdict(Decimal)
        tipo_nomes = {}
        subtipo_por_tipo = defaultdict(list)
        for item in itens_com_tipo:
            ts_id = item.tipo_servico_id
            plan_por_tipo[ts_id] += item.custo_total
            tipo_nomes[ts_id] = item.tipo_servico.nome
            if item.subtipo_servico and item.subtipo_servico.nome not in subtipo_por_tipo[ts_id]:
                subtipo_por_tipo[ts_id].append(item.subtipo_servico.nome)

        linhas = []
        for ts_id, plan_orig in plan_por_tipo.items():
            plan_ajust = (plan_orig * fator).quantize(Decimal('0.01'))
            real_agg = os_qs.filter(tipo_servico_id=ts_id).aggregate(
                mo=Sum('custo_talhao__custo_mao_obra'),
                maq=Sum('custo_talhao__custo_maquinario'),
                ins=Sum('custo_talhao__custo_insumos'),
                svc=Sum('custo_talhao__custo_servico_externo'),
            )
            real_val = (
                Decimal(str(real_agg['mo'] or 0)) +
                Decimal(str(real_agg['maq'] or 0)) +
                Decimal(str(real_agg['ins'] or 0)) +
                Decimal(str(real_agg['svc'] or 0))
            )
            variacao = real_val - plan_ajust
            var_pct = (variacao / plan_ajust * 100).quantize(Decimal('0.1')) if plan_ajust else None
            linhas.append({
                'label': tipo_nomes[ts_id],
                'sublabel': ', '.join(subtipo_por_tipo[ts_id]),
                'planejado_orig':  str(plan_orig),
                'planejado_ajust': str(plan_ajust),
                'real':     str(real_val),
                'variacao': str(variacao),
                'variacao_pct': str(var_pct) if var_pct is not None else None,
            })
        modo = 'tipo_servico'
    else:
        # ── Fallback: por categoria (planos sem tipo_servico) ──
        planejado_cat = defaultdict(Decimal)
        for item in plan.itens.all():
            planejado_cat[item.categoria] += item.custo_total

        MAPA = [
            ('MO', 'Mão de Obra', 'mo'),
            ('MAQUINARIO', 'Maquinário', 'maq'),
            ('INSUMO', 'Insumos', 'ins'),
            ('SERVICO_EXTERNO', 'Serviço Externo', 'svc'),
        ]
        linhas = []
        for cat_key, cat_label, agg_key in MAPA:
            plan_orig  = planejado_cat.get(cat_key, Decimal('0'))
            plan_ajust = (plan_orig * fator).quantize(Decimal('0.01'))
            real_val   = Decimal(str(agg_geral[agg_key] or 0))
            variacao   = real_val - plan_ajust
            var_pct    = (variacao / plan_ajust * 100).quantize(Decimal('0.1')) if plan_ajust else None
            linhas.append({
                'label': cat_label,
                'sublabel': '',
                'planejado_orig':  str(plan_orig),
                'planejado_ajust': str(plan_ajust),
                'real':     str(real_val),
                'variacao': str(variacao),
                'variacao_pct': str(var_pct) if var_pct is not None else None,
            })
        modo = 'categoria'

    total_orig  = sum(Decimal(l['planejado_orig'])  for l in linhas)
    total_ajust = sum(Decimal(l['planejado_ajust']) for l in linhas)
    total_real  = sum(Decimal(l['real'])            for l in linhas)
    var_total   = total_real - total_ajust
    var_total_pct = (var_total / total_ajust * 100).quantize(Decimal('0.1')) if total_ajust else None

    return JsonResponse({
        'modo': modo,
        'talhao': {'nome': talhao.nome, 'area': str(area_real)},
        'area_plan': str(area_plan),
        'fator': str(fator.quantize(Decimal('0.0001'))),
        'linhas': linhas,
        'totais': {
            'planejado_orig':  str(total_orig),
            'planejado_ajust': str(total_ajust),
            'real':     str(total_real),
            'variacao': str(var_total),
            'variacao_pct': str(var_total_pct) if var_total_pct is not None else None,
        },
    })


@login_required
def ajax_subcategorias_por_categoria(request):
    categoria = request.GET.get('categoria', '')
    subs = list(
        SubcategoriaItemCusto.objects
        .filter(categoria=categoria, ativo=True)
        .values('id', 'nome')
    )
    return JsonResponse({'results': subs})


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
