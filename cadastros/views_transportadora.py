from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.core.paginator import Paginator
from core.pagination import paginate
from .models import Transportadora, Viagem
from .forms import TransportadoraForm
from django.contrib import messages


@login_required
def transportadora_list(request):
    if not request.user.empresa:
        return render(request, 'cadastros/transportadora/transportadora_list.html', {'page_obj': None, 'total': 0})

    qs = Transportadora.objects.filter(empresa=request.user.empresa).prefetch_related('viagens')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(razao_social__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj__icontains=q)
        )

    # Filters
    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    uf = request.GET.get('uf')
    if uf:
        qs = qs.filter(uf=uf)

    ativo = request.GET.get('ativo')
    if ativo == '1':
        qs = qs.filter(ativa=True)
    elif ativo == '0':
        qs = qs.filter(ativa=False)

    frete_min = request.GET.get('frete_min')
    frete_max = request.GET.get('frete_max')
    if frete_min:
        qs = qs.filter(frete_padrao__gte=frete_min)
    if frete_max:
        qs = qs.filter(frete_padrao__lte=frete_max)

    # Annotate with counts and last viagem
    qs = qs.annotate(total_viagens=Count('viagens'), ultima_viagem=Max('viagens__data'))

    page_obj, per_page, per_page_options = paginate(request, qs)

    UFS = ['AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG','PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SE','SP','TO']

    context = {
        'page_obj': page_obj,
        'total': qs.count(),
        'filtro_tipo': tipo,
        'filtro_uf': uf,
        'ufs': UFS,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/transportadora/transportadora_list.html', context)


@login_required
def transportadora_detail(request, pk):
    t = get_object_or_404(Transportadora, pk=pk, empresa=request.user.empresa)
    viagens = t.viagens.order_by('-data')[:10]

    context = {
        'transportadora': t,
        'viagens': viagens,
    }
    return render(request, 'cadastros/transportadora/transportadora_detail.html', context)


@login_required
def transportadora_create(request):
    if not request.user.empresa:
        messages.warning(request, 'Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('cadastros:transportadora_list')

    if request.method == 'POST':
        form = TransportadoraForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            t = form.save()
            messages.success(request, 'Transportadora criada com sucesso!')
            return redirect('cadastros:transportadora_detail', pk=t.pk)
    else:
        form = TransportadoraForm(empresa=request.user.empresa)

    return render(request, 'cadastros/transportadora/transportadora_form.html', {'form': form, 'action': 'Criar'})


@login_required
def transportadora_update(request, pk):
    t = get_object_or_404(Transportadora, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = TransportadoraForm(request.POST, instance=t, empresa=request.user.empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transportadora atualizada!')
            return redirect('cadastros:transportadora_detail', pk=t.pk)
    else:
        form = TransportadoraForm(instance=t, empresa=request.user.empresa)

    return render(request, 'cadastros/transportadora/transportadora_form.html', {'form': form, 'transportadora': t, 'action': 'Editar'})


@login_required
def transportadora_delete(request, pk):
    t = get_object_or_404(Transportadora, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        t.delete()
        messages.success(request, 'Transportadora excluída!')
        return redirect('cadastros:transportadora_list')
    return render(request, 'cadastros/transportadora/transportadora_confirm_delete.html', {'transportadora': t})


@login_required
def transportadora_update_frete(request, pk):
    """Atualiza o frete_padrao via AJAX. Retorna JSON."""
    if request.method != 'POST' or request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    t = get_object_or_404(Transportadora, pk=pk, empresa=request.user.empresa)

    frete_raw = request.POST.get('frete', '').replace(',', '.')
    from decimal import Decimal, InvalidOperation
    try:
        if frete_raw == '':
            frete_value = None
        else:
            frete_value = Decimal(frete_raw)
            if frete_value < 0:
                return JsonResponse({'erro': 'Valor de frete deve ser >= 0'}, status=400)
    except InvalidOperation:
        return JsonResponse({'erro': 'Valor de frete inválido'}, status=400)

    t.frete_padrao = frete_value
    t.save()

    return JsonResponse({'sucesso': True, 'frete_padrao': str(t.frete_padrao) if t.frete_padrao is not None else None})