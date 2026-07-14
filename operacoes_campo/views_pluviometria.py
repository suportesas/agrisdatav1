"""Views do módulo Pluviometria (RF-107)."""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from operacoes_campo.models import RegistroPluviometria
from cadastros.models import Fazenda
from operacoes_campo.forms import RegistroPluviometriaForm


@login_required
def pluviometria_list(request):
    empresa = request.user.empresa
    qs = RegistroPluviometria.objects.filter(empresa=empresa).select_related('fazenda', 'responsavel')

    # Filtros
    fazenda_id = request.GET.get('fazenda')
    ano = request.GET.get('ano')
    mes = request.GET.get('mes')

    if fazenda_id:
        qs = qs.filter(fazenda_id=fazenda_id)
    if ano:
        qs = qs.filter(data__year=ano)
    if mes:
        qs = qs.filter(data__month=mes)

    fazendas = Fazenda.objects.filter(empresa=empresa, ativa=True)

    # Dados para gráfico (últimos 30 registros filtrados, mais recente primeiro → reverter para gráfico)
    chart_qs = qs.order_by('data')[:60]
    chart_labels = json.dumps([r.data.strftime('%d/%m') for r in chart_qs])
    chart_data = json.dumps([float(r.mm_chuva) for r in chart_qs])

    # Acumulado do período
    total_mm = qs.aggregate(t=Sum('mm_chuva'))['t'] or 0

    # Paginação
    paginator = Paginator(qs.order_by('-data'), 20)
    page = request.GET.get('page', 1)
    try:
        registros_page = paginator.page(page)
    except Exception:
        registros_page = paginator.page(1)

    context = {
        'registros': registros_page,
        'fazendas': fazendas,
        'fazenda_selecionada': fazenda_id,
        'ano_selecionado': ano,
        'mes_selecionado': mes,
        'total_mm': total_mm,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'title': 'Pluviometria',
    }
    return render(request, 'cadastros/pluviometria/pluviometria_list.html', context)


@login_required
def pluviometria_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = RegistroPluviometriaForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.save()
            messages.success(request, f'Registro de {obj.mm_chuva} mm em {obj.data.strftime("%d/%m/%Y")} cadastrado com sucesso.')
            return redirect('operacoes_campo:pluviometria_list')
    else:
        form = RegistroPluviometriaForm(user=request.user)
    return render(request, 'cadastros/pluviometria/pluviometria_form.html', {'form': form, 'title': 'Novo Registro de Pluviometria'})


@login_required
def pluviometria_update(request, pk):
    obj = get_object_or_404(RegistroPluviometria, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = RegistroPluviometriaForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro atualizado com sucesso.')
            return redirect('operacoes_campo:pluviometria_list')
    else:
        form = RegistroPluviometriaForm(instance=obj, user=request.user)
    return render(request, 'cadastros/pluviometria/pluviometria_form.html', {'form': form, 'obj': obj, 'title': 'Editar Registro de Pluviometria'})


@login_required
def pluviometria_delete(request, pk):
    obj = get_object_or_404(RegistroPluviometria, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Registro excluído com sucesso.')
        return redirect('operacoes_campo:pluviometria_list')
    return render(request, 'cadastros/pluviometria/pluviometria_confirm_delete.html', {'obj': obj})


@login_required
def pluviometria_dashboard(request):
    """Retorna dados JSON para gráfico de acumulado mensal por fazenda."""
    empresa = request.user.empresa
    fazenda_id = request.GET.get('fazenda_id')
    ano = request.GET.get('ano')

    qs = RegistroPluviometria.objects.filter(empresa=empresa)
    if fazenda_id:
        qs = qs.filter(fazenda_id=fazenda_id)
    if ano:
        qs = qs.filter(data__year=ano)

    mensal = (
        qs.annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('mm_chuva'))
        .order_by('mes')
    )

    return JsonResponse({
        'labels': [m['mes'].strftime('%b/%Y') for m in mensal],
        'data': [float(m['total']) for m in mensal],
    })
