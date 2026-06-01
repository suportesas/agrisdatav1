from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum, Avg, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    LancamentoMensalForm, OcorrenciaUsinaForm, RelatorioMensalUsinaForm,
    UsinaFotovoltaicaForm, UnidadeConsumidoraForm,
)
from .models import LancamentoMensal, OcorrenciaUsina, RelatorioMensalUsina, UsinaFotovoltaica, UnidadeConsumidora


# ─────────────────────────── Dashboard ──────────────────────────────────────

@login_required
def dashboard(request):
    empresa = request.user.empresa
    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)

    usinas = UsinaFotovoltaica.objects.filter(empresa=empresa, ativa=True)

    # Totais do mês atual (relatórios de usina)
    relatorio_mes = RelatorioMensalUsina.objects.filter(
        empresa=empresa, mes_referencia=mes_atual)
    totais_mes = relatorio_mes.aggregate(
        geracao=Sum('geracao_kwh'),
        economia=Sum('economia_rs'),
        faturado=Sum('faturado_rs'),
        desempenho=Avg('desempenho_pct'),
    )

    # Últimos 12 meses — geração e economia por mês
    from dateutil.relativedelta import relativedelta
    meses = []
    for i in range(11, -1, -1):
        m = date(hoje.year, hoje.month, 1) - relativedelta(months=i)
        agg = RelatorioMensalUsina.objects.filter(
            empresa=empresa, mes_referencia=m
        ).aggregate(g=Sum('geracao_kwh'), e=Sum('economia_rs'), f=Sum('faturado_rs'))
        meses.append({
            'label': m.strftime('%b/%y'),
            'geracao': float(agg['g'] or 0),
            'economia': float(agg['e'] or 0),
            'faturado': float(agg['f'] or 0),
        })

    # UCs do mês atual
    lancamentos_mes = LancamentoMensal.objects.filter(
        empresa=empresa, mes_referencia=mes_atual
    ).select_related('unidade_consumidora__usina').order_by('unidade_consumidora__nome')

    return render(request, 'energia/dashboard.html', {
        'usinas': usinas,
        'total_usinas': usinas.count(),
        'totais_mes': totais_mes,
        'mes_atual': mes_atual,
        'meses': meses,
        'lancamentos_mes': lancamentos_mes,
    })


# ─────────────────────────── Consolidado ────────────────────────────────────

@login_required
def consolidado(request):
    from dateutil.relativedelta import relativedelta

    empresa = request.user.empresa
    hoje = date.today()

    # Filtro de mês
    mes_param = request.GET.get('mes', '')
    try:
        mes_ref = date.fromisoformat(mes_param + '-01') if mes_param else date(hoje.year, hoje.month, 1)
    except ValueError:
        mes_ref = date(hoje.year, hoje.month, 1)

    usinas = UsinaFotovoltaica.objects.filter(empresa=empresa, ativa=True).order_by('nome')

    # Relatórios do mês selecionado para cada usina
    relatorios_mes = {
        r.usina_id: r
        for r in RelatorioMensalUsina.objects.filter(empresa=empresa, mes_referencia=mes_ref)
                                             .select_related('usina')
    }

    # Monta linhas da tabela comparativa
    linhas = []
    for u in usinas:
        r = relatorios_mes.get(u.pk)
        linhas.append({'usina': u, 'relatorio': r})

    # Séries para os gráficos — apenas usinas com relatório no mês
    usinas_com_rel = [l for l in linhas if l['relatorio']]
    # Ordena por geração decrescente para o ranking
    usinas_com_rel_sorted = sorted(usinas_com_rel, key=lambda x: x['relatorio'].geracao_kwh, reverse=True)

    chart_labels   = [l['usina'].codigo for l in usinas_com_rel_sorted]
    chart_geracao  = [float(l['relatorio'].geracao_kwh)     for l in usinas_com_rel_sorted]
    chart_desemp   = [float(l['relatorio'].desempenho_pct)  for l in usinas_com_rel_sorted]
    chart_economia = [float(l['relatorio'].economia_rs)     for l in usinas_com_rel_sorted]
    chart_co2      = [float(l['relatorio'].co2_nao_produzido_t) for l in usinas_com_rel_sorted]

    # Histórico 12 meses — série por usina (para gráfico de linhas)
    historico_usinas = []
    meses_labels = []
    for i in range(11, -1, -1):
        m = date(hoje.year, hoje.month, 1) - relativedelta(months=i)
        meses_labels.append(m.strftime('%b/%y'))

    for u in usinas:
        serie = []
        for i in range(11, -1, -1):
            m = date(hoje.year, hoje.month, 1) - relativedelta(months=i)
            try:
                r = RelatorioMensalUsina.objects.get(empresa=empresa, usina=u, mes_referencia=m)
                serie.append(float(r.geracao_kwh))
            except RelatorioMensalUsina.DoesNotExist:
                serie.append(None)
        historico_usinas.append({'label': f'{u.codigo} — {u.nome}', 'data': serie})

    return render(request, 'energia/consolidado.html', {
        'linhas': linhas,
        'mes_ref': mes_ref,
        'mes_param': mes_ref.strftime('%Y-%m'),
        'chart_labels': chart_labels,
        'chart_geracao': chart_geracao,
        'chart_desemp': chart_desemp,
        'chart_economia': chart_economia,
        'chart_co2': chart_co2,
        'meses_labels': meses_labels,
        'historico_usinas': historico_usinas,
    })


# ─────────────────────────── Usinas ─────────────────────────────────────────

@login_required
def usina_list(request):
    empresa = request.user.empresa
    qs = UsinaFotovoltaica.objects.filter(empresa=empresa)
    q = request.GET.get('q', '')
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(codigo__icontains=q))
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'energia/usina_list.html', {
        'page_obj': page_obj, 'q': q, 'total': qs.count(),
    })


@login_required
def usina_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = UsinaFotovoltaicaForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Usina "{obj.nome}" cadastrada com sucesso.')
            return redirect('energia:usina_detail', pk=obj.pk)
    else:
        form = UsinaFotovoltaicaForm(empresa=empresa)
    return render(request, 'energia/usina_form.html', {'form': form, 'titulo': 'Nova Usina'})


@login_required
def usina_detail(request, pk):
    empresa = request.user.empresa
    usina = get_object_or_404(UsinaFotovoltaica, pk=pk, empresa=empresa)
    relatorios = usina.relatorios.order_by('-mes_referencia')[:24]
    ucs = usina.unidades_consumidoras.filter(ativa=True)
    ocorrencias = usina.ocorrencias.order_by('-data_ocorrencia')[:10]
    ocorrencias_pendentes = usina.ocorrencias.filter(resolvido=False).count()
    return render(request, 'energia/usina_detail.html', {
        'usina': usina, 'relatorios': relatorios, 'ucs': ucs,
        'ocorrencias': ocorrencias, 'ocorrencias_pendentes': ocorrencias_pendentes,
    })


@login_required
def usina_update(request, pk):
    empresa = request.user.empresa
    usina = get_object_or_404(UsinaFotovoltaica, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = UsinaFotovoltaicaForm(request.POST, instance=usina, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usina atualizada.')
            return redirect('energia:usina_detail', pk=usina.pk)
    else:
        form = UsinaFotovoltaicaForm(instance=usina, empresa=empresa)
    return render(request, 'energia/usina_form.html', {
        'form': form, 'titulo': f'Editar Usina — {usina.nome}', 'usina': usina,
    })


# ─────────────────────────── Unidades Consumidoras ──────────────────────────

@login_required
def uc_list(request):
    empresa = request.user.empresa
    qs = UnidadeConsumidora.objects.filter(empresa=empresa).select_related('usina')
    q = request.GET.get('q', '')
    usina_id = request.GET.get('usina', '')
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(codigo_cliente__icontains=q))
    if usina_id:
        qs = qs.filter(usina_id=usina_id)
    usinas = UsinaFotovoltaica.objects.filter(empresa=empresa, ativa=True)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'energia/uc_list.html', {
        'page_obj': page_obj, 'q': q, 'usinas': usinas,
        'usina_id': usina_id, 'total': qs.count(),
    })


@login_required
def uc_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = UnidadeConsumidoraForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'UC "{obj.nome}" cadastrada com sucesso.')
            return redirect('energia:uc_detail', pk=obj.pk)
    else:
        form = UnidadeConsumidoraForm(empresa=empresa)
    return render(request, 'energia/uc_form.html', {'form': form, 'titulo': 'Nova UC'})


@login_required
def uc_detail(request, pk):
    empresa = request.user.empresa
    uc = get_object_or_404(UnidadeConsumidora, pk=pk, empresa=empresa)
    lancamentos = uc.lancamentos.order_by('-mes_referencia')[:24]
    return render(request, 'energia/uc_detail.html', {'uc': uc, 'lancamentos': lancamentos})


@login_required
def uc_update(request, pk):
    empresa = request.user.empresa
    uc = get_object_or_404(UnidadeConsumidora, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = UnidadeConsumidoraForm(request.POST, instance=uc, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'UC atualizada.')
            return redirect('energia:uc_detail', pk=uc.pk)
    else:
        form = UnidadeConsumidoraForm(instance=uc, empresa=empresa)
    return render(request, 'energia/uc_form.html', {
        'form': form, 'titulo': f'Editar UC — {uc.nome}', 'uc': uc,
    })


# ─────────────────────────── Lançamentos Mensais ────────────────────────────

@login_required
def lancamento_list(request):
    empresa = request.user.empresa
    qs = LancamentoMensal.objects.filter(empresa=empresa).select_related(
        'unidade_consumidora__usina')
    mes = request.GET.get('mes', '')
    uc_id = request.GET.get('uc', '')
    if mes:
        try:
            d = date.fromisoformat(mes + '-01')
            qs = qs.filter(mes_referencia=d)
        except ValueError:
            pass
    if uc_id:
        qs = qs.filter(unidade_consumidora_id=uc_id)
    ucs = UnidadeConsumidora.objects.filter(empresa=empresa, ativa=True)
    totais = qs.aggregate(
        consumo=Sum('consumo_registrado_kwh'),
        compensado=Sum('energia_compensada_kwh'),
        injetado=Sum('energia_injetada_kwh'),
        faturado=Sum('valor_faturado_rs'),
        economizado=Sum('valor_economizado_rs'),
    )
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'energia/lancamento_list.html', {
        'page_obj': page_obj, 'mes': mes, 'uc_id': uc_id,
        'ucs': ucs, 'totais': totais, 'total': qs.count(),
    })


@login_required
def lancamento_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = LancamentoMensalForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Lançamento de {obj} salvo.')
            return redirect('energia:lancamento_detail', pk=obj.pk)
    else:
        form = LancamentoMensalForm(empresa=empresa)
    return render(request, 'energia/lancamento_form.html', {
        'form': form, 'titulo': 'Novo Lançamento Mensal',
    })


@login_required
def lancamento_detail(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(LancamentoMensal, pk=pk, empresa=empresa)
    return render(request, 'energia/lancamento_detail.html', {'obj': obj})


@login_required
def lancamento_update(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(LancamentoMensal, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = LancamentoMensalForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lançamento atualizado.')
            return redirect('energia:lancamento_detail', pk=obj.pk)
    else:
        form = LancamentoMensalForm(instance=obj, empresa=empresa)
    return render(request, 'energia/lancamento_form.html', {
        'form': form, 'titulo': f'Editar Lançamento — {obj}', 'obj': obj,
    })


# ─────────────────────────── Relatórios Mensais Usina ───────────────────────

@login_required
def relatorio_usina_list(request):
    empresa = request.user.empresa
    qs = RelatorioMensalUsina.objects.filter(empresa=empresa).select_related('usina')
    usina_id = request.GET.get('usina', '')
    mes = request.GET.get('mes', '')
    if usina_id:
        qs = qs.filter(usina_id=usina_id)
    if mes:
        try:
            d = date.fromisoformat(mes + '-01')
            qs = qs.filter(mes_referencia=d)
        except ValueError:
            pass
    usinas = UsinaFotovoltaica.objects.filter(empresa=empresa, ativa=True)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'energia/relatorio_usina_list.html', {
        'page_obj': page_obj, 'usinas': usinas,
        'usina_id': usina_id, 'mes': mes, 'total': qs.count(),
    })


@login_required
def relatorio_usina_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = RelatorioMensalUsinaForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Relatório de {obj} salvo.')
            return redirect('energia:relatorio_usina_detail', pk=obj.pk)
    else:
        form = RelatorioMensalUsinaForm(empresa=empresa)
    return render(request, 'energia/relatorio_usina_form.html', {
        'form': form, 'titulo': 'Novo Relatório de Usina',
    })


@login_required
def relatorio_usina_detail(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(RelatorioMensalUsina, pk=pk, empresa=empresa)
    return render(request, 'energia/relatorio_usina_detail.html', {'obj': obj})


@login_required
def relatorio_usina_update(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(RelatorioMensalUsina, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = RelatorioMensalUsinaForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Relatório atualizado.')
            return redirect('energia:relatorio_usina_detail', pk=obj.pk)
    else:
        form = RelatorioMensalUsinaForm(instance=obj, empresa=empresa)
    return render(request, 'energia/relatorio_usina_form.html', {
        'form': form, 'titulo': f'Editar Relatório — {obj}', 'obj': obj,
    })


# ─────────────────────────── Ocorrências de Usina ───────────────────────────

_GRAVIDADE_BADGE = {
    'BAIXA':   'bg-success',
    'MEDIA':   'bg-warning text-dark',
    'ALTA':    'bg-orange text-white',
    'CRITICA': 'bg-danger',
}

@login_required
def ocorrencia_list(request):
    empresa = request.user.empresa
    qs = OcorrenciaUsina.objects.filter(empresa=empresa).select_related('usina', 'relatorio')
    usina_id  = request.GET.get('usina', '')
    resolvido = request.GET.get('resolvido', '')
    tipo      = request.GET.get('tipo', '')
    if usina_id:
        qs = qs.filter(usina_id=usina_id)
    if resolvido == '0':
        qs = qs.filter(resolvido=False)
    elif resolvido == '1':
        qs = qs.filter(resolvido=True)
    if tipo:
        qs = qs.filter(tipo=tipo)
    usinas = UsinaFotovoltaica.objects.filter(empresa=empresa, ativa=True)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'energia/ocorrencia_list.html', {
        'page_obj': page_obj,
        'usinas': usinas,
        'usina_id': usina_id,
        'resolvido': resolvido,
        'tipo': tipo,
        'tipo_choices': OcorrenciaUsina.TIPO_CHOICES,
        'total': qs.count(),
        'pendentes': OcorrenciaUsina.objects.filter(empresa=empresa, resolvido=False).count(),
    })


@login_required
def ocorrencia_create(request, usina_pk=None):
    empresa = request.user.empresa
    usina = None
    if usina_pk:
        usina = get_object_or_404(UsinaFotovoltaica, pk=usina_pk, empresa=empresa)
    if request.method == 'POST':
        form = OcorrenciaUsinaForm(request.POST, empresa=empresa, usina=usina)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'Ocorrência "{obj.titulo}" registrada.')
            return redirect('energia:ocorrencia_detail', pk=obj.pk)
    else:
        form = OcorrenciaUsinaForm(empresa=empresa, usina=usina)
    return render(request, 'energia/ocorrencia_form.html', {
        'form': form,
        'titulo': 'Nova Ocorrência',
        'usina': usina,
    })


@login_required
def ocorrencia_detail(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(OcorrenciaUsina, pk=pk, empresa=empresa)
    return render(request, 'energia/ocorrencia_detail.html', {
        'obj': obj,
        'badge': _GRAVIDADE_BADGE.get(obj.gravidade, 'bg-secondary'),
    })


@login_required
def ocorrencia_update(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(OcorrenciaUsina, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = OcorrenciaUsinaForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ocorrência atualizada.')
            return redirect('energia:ocorrencia_detail', pk=obj.pk)
    else:
        form = OcorrenciaUsinaForm(instance=obj, empresa=empresa)
    return render(request, 'energia/ocorrencia_form.html', {
        'form': form,
        'titulo': f'Editar Ocorrência — {obj.titulo}',
        'obj': obj,
    })


@login_required
def ocorrencia_resolver(request, pk):
    """Toggle rápido resolvido/pendente via POST."""
    from django.utils import timezone
    empresa = request.user.empresa
    obj = get_object_or_404(OcorrenciaUsina, pk=pk, empresa=empresa)
    if request.method == 'POST':
        obj.resolvido = not obj.resolvido
        if obj.resolvido and not obj.data_resolucao:
            obj.data_resolucao = date.today()
        elif not obj.resolvido:
            obj.data_resolucao = None
        obj.save(update_fields=['resolvido', 'data_resolucao', 'atualizado_em'])
        status = 'resolvida' if obj.resolvido else 'reaberta'
        messages.success(request, f'Ocorrência marcada como {status}.')
    return redirect(request.POST.get('next', 'energia:ocorrencia_list'))
