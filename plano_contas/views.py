from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ContaContabilForm, CentroCustoForm
from .models import ContaContabil, CentroCusto, TIPO_CONTA_CHOICES


# ---------------------------------------------------------------------------
# ContaContabil — CRUD
# ---------------------------------------------------------------------------

@login_required
def conta_list(request):
    empresa = request.user.empresa
    q = request.GET.get('q', '').strip()
    tipo_filter = request.GET.get('tipo', '')
    ativo_filter = request.GET.get('ativo', 'true')

    contas = ContaContabil.objects.filter(empresa=empresa).select_related('conta_pai')

    if q:
        contas = contas.filter(Q(codigo__icontains=q) | Q(nome__icontains=q))
    if tipo_filter:
        contas = contas.filter(tipo=tipo_filter)
    if ativo_filter == 'false':
        contas = contas.filter(ativo=False)
    elif ativo_filter == 'todos':
        pass
    else:
        contas = contas.filter(ativo=True)

    # Lista de (tipo_key, tipo_label, contagem) para o template iterar sem precisar de dict lookup
    totais_lista = [
        (tipo_key, tipo_label, ContaContabil.objects.filter(empresa=empresa, tipo=tipo_key, ativo=True).count())
        for tipo_key, tipo_label in TIPO_CONTA_CHOICES
    ]

    paginator = Paginator(contas, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'plano_contas/conta_list.html', {
        'page_obj': page_obj,
        'q': q,
        'tipo_filter': tipo_filter,
        'ativo_filter': ativo_filter,
        'tipos': TIPO_CONTA_CHOICES,
        'totais_lista': totais_lista,
    })


@login_required
def conta_arvore(request):
    empresa = request.user.empresa
    tipo_filter = request.GET.get('tipo', '')

    qs = ContaContabil.objects.filter(empresa=empresa, ativo=True).select_related('conta_pai')
    if tipo_filter:
        qs = qs.filter(tipo=tipo_filter)

    contas_raiz = qs.filter(conta_pai=None).prefetch_related(
        'subcontas__subcontas__subcontas__subcontas'
    )

    return render(request, 'plano_contas/conta_arvore.html', {
        'contas_raiz': contas_raiz,
        'tipo_filter': tipo_filter,
        'tipos': TIPO_CONTA_CHOICES,
    })


@login_required
def conta_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = ContaContabilForm(request.POST, empresa=empresa)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.empresa = empresa
            conta.save()
            messages.success(request, f'Conta "{conta}" criada com sucesso.')
            return redirect('plano_contas:conta_detail', pk=conta.pk)
    else:
        conta_pai_id = request.GET.get('pai')
        initial = {}
        if conta_pai_id:
            try:
                pai = ContaContabil.objects.get(pk=conta_pai_id, empresa=empresa)
                initial['conta_pai'] = pai
            except ContaContabil.DoesNotExist:
                pass
        form = ContaContabilForm(empresa=empresa, initial=initial)

    return render(request, 'plano_contas/conta_form.html', {
        'form': form,
        'titulo': 'Nova Conta Contábil',
    })


@login_required
def conta_detail(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaContabil, pk=pk, empresa=empresa)
    subcontas = ContaContabil.objects.filter(conta_pai=conta, empresa=empresa).order_by('codigo')

    uso_cp = 0
    uso_cr = 0
    try:
        uso_cp = conta.contas_pagar.count()
    except Exception:
        pass
    try:
        uso_cr = conta.contas_receber.count()
    except Exception:
        pass

    return render(request, 'plano_contas/conta_detail.html', {
        'conta': conta,
        'subcontas': subcontas,
        'caminho': conta.get_caminho(),
        'uso_cp': uso_cp,
        'uso_cr': uso_cr,
    })


@login_required
def conta_edit(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaContabil, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = ContaContabilForm(request.POST, instance=conta, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Conta "{conta}" atualizada com sucesso.')
            return redirect('plano_contas:conta_detail', pk=conta.pk)
    else:
        form = ContaContabilForm(instance=conta, empresa=empresa)

    return render(request, 'plano_contas/conta_form.html', {
        'form': form,
        'conta': conta,
        'titulo': f'Editar Conta: {conta.codigo}',
    })


@login_required
def conta_toggle_ativo(request, pk):
    empresa = request.user.empresa
    conta = get_object_or_404(ContaContabil, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if conta.ativo and conta.tem_subcontas_ativas:
            messages.error(request, 'Não é possível desativar uma conta que possui subcontas ativas.')
            return redirect('plano_contas:conta_detail', pk=pk)
        conta.ativo = not conta.ativo
        conta.save(update_fields=['ativo', 'updated_at'])
        acao = 'ativada' if conta.ativo else 'desativada'
        messages.success(request, f'Conta "{conta}" {acao} com sucesso.')
        return redirect('plano_contas:conta_list')

    return render(request, 'plano_contas/conta_confirm_toggle.html', {
        'conta': conta,
        'tem_subcontas': conta.tem_subcontas_ativas,
    })


@login_required
def conta_autocomplete(request):
    empresa = request.user.empresa
    q = request.GET.get('q', '').strip()
    analitica_only = request.GET.get('analitica', '') == '1'

    if len(q) < 2:
        return JsonResponse({'results': []})

    qs = ContaContabil.objects.filter(
        empresa=empresa,
        ativo=True,
    ).filter(Q(codigo__icontains=q) | Q(nome__icontains=q))

    if analitica_only:
        qs = qs.filter(analitica=True)

    results = [{'id': c.pk, 'text': str(c)} for c in qs[:15]]
    return JsonResponse({'results': results})


@login_required
def balancete(request):
    empresa = request.user.empresa
    tipo_filter = request.GET.get('tipo', '')

    contas = ContaContabil.objects.filter(
        empresa=empresa,
        analitica=True,
        ativo=True,
    ).order_by('codigo')

    if tipo_filter:
        contas = contas.filter(tipo=tipo_filter)

    return render(request, 'plano_contas/balancete.html', {
        'contas': contas,
        'tipo_filter': tipo_filter,
        'tipos': TIPO_CONTA_CHOICES,
    })


# ---------------------------------------------------------------------------
# CentroCusto — CRUD
# ---------------------------------------------------------------------------

@login_required
def centro_list(request):
    empresa = request.user.empresa
    q = request.GET.get('q', '').strip()
    ativo_filter = request.GET.get('ativo', 'true')

    centros = CentroCusto.objects.filter(empresa=empresa).select_related('centro_pai')

    if q:
        centros = centros.filter(Q(codigo__icontains=q) | Q(nome__icontains=q))
    if ativo_filter == 'false':
        centros = centros.filter(ativo=False)
    elif ativo_filter == 'todos':
        pass
    else:
        centros = centros.filter(ativo=True)

    paginator = Paginator(centros, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'plano_contas/centro_list.html', {
        'page_obj': page_obj,
        'q': q,
        'ativo_filter': ativo_filter,
    })


@login_required
def centro_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = CentroCustoForm(request.POST, empresa=empresa)
        if form.is_valid():
            centro = form.save(commit=False)
            centro.empresa = empresa
            centro.save()
            messages.success(request, f'Centro de custo "{centro}" criado com sucesso.')
            return redirect('plano_contas:centro_detail', pk=centro.pk)
    else:
        form = CentroCustoForm(empresa=empresa)

    return render(request, 'plano_contas/centro_form.html', {
        'form': form,
        'titulo': 'Novo Centro de Custo',
    })


@login_required
def centro_detail(request, pk):
    empresa = request.user.empresa
    centro = get_object_or_404(CentroCusto, pk=pk, empresa=empresa)
    subcentros = CentroCusto.objects.filter(centro_pai=centro, empresa=empresa).order_by('codigo')

    return render(request, 'plano_contas/centro_detail.html', {
        'centro': centro,
        'subcentros': subcentros,
    })


@login_required
def centro_edit(request, pk):
    empresa = request.user.empresa
    centro = get_object_or_404(CentroCusto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = CentroCustoForm(request.POST, instance=centro, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Centro de custo "{centro}" atualizado com sucesso.')
            return redirect('plano_contas:centro_detail', pk=centro.pk)
    else:
        form = CentroCustoForm(instance=centro, empresa=empresa)

    return render(request, 'plano_contas/centro_form.html', {
        'form': form,
        'centro': centro,
        'titulo': f'Editar Centro: {centro.codigo}',
    })


@login_required
def centro_toggle_ativo(request, pk):
    empresa = request.user.empresa
    centro = get_object_or_404(CentroCusto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if centro.ativo and centro.tem_subcentros_ativos:
            messages.error(request, 'Não é possível desativar um centro que possui subcentros ativos.')
            return redirect('plano_contas:centro_detail', pk=pk)
        centro.ativo = not centro.ativo
        centro.save(update_fields=['ativo', 'updated_at'])
        acao = 'ativado' if centro.ativo else 'desativado'
        messages.success(request, f'Centro "{centro}" {acao} com sucesso.')
        return redirect('plano_contas:centro_list')

    return render(request, 'plano_contas/centro_confirm_toggle.html', {
        'centro': centro,
        'tem_subcentros': centro.tem_subcentros_ativos,
    })


@login_required
def centro_autocomplete(request):
    empresa = request.user.empresa
    q = request.GET.get('q', '').strip()

    if len(q) < 2:
        return JsonResponse({'results': []})

    qs = CentroCusto.objects.filter(
        empresa=empresa,
        ativo=True,
    ).filter(Q(codigo__icontains=q) | Q(nome__icontains=q))[:15]

    results = [{'id': c.pk, 'text': str(c)} for c in qs]
    return JsonResponse({'results': results})
