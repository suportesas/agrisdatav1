"""Views de Veículos — CRUD completo para o módulo Frota."""
import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VehicleForm, VehiclePlateForm
from .models import AbastecimentoVeiculo, Vehicle, VehicleDocument, VehiclePlate


@login_required
def vehicle_list(request):
    if not request.user.empresa:
        messages.warning(request, 'Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    veiculos = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates', 'transportadora')

    q = request.GET.get('q', '').strip()
    if q:
        veiculos = veiculos.filter(
            Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(plates__placa__icontains=q)
        ).distinct()

    tipo = request.GET.get('tipo', '').strip()
    if tipo:
        veiculos = veiculos.filter(tipo=tipo)

    tipo_combustivel = request.GET.get('tipo_combustivel', '').strip()
    if tipo_combustivel:
        veiculos = veiculos.filter(tipo_combustivel=tipo_combustivel)

    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        veiculos = veiculos.filter(transportadora__pk=transportadora_id)

    sort = request.GET.get('sort')
    allowed_sort = {'marca', '-marca', 'modelo', '-modelo', 'consumo_medio', '-consumo_medio', 'tipo', '-tipo'}
    if sort in allowed_sort:
        veiculos = veiculos.order_by(sort)

    paginator = Paginator(veiculos, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    from cadastros.models import Transportadora
    transportadoras = Transportadora.objects.filter(empresa=request.user.empresa).order_by('razao_social')
    tipo_choices = Vehicle._meta.get_field('tipo').choices
    fuel_choices = Vehicle._meta.get_field('tipo_combustivel').choices

    base_qs = request.GET.copy()
    def make_link(value):
        qs = base_qs.copy()
        qs['sort'] = value
        return qs.urlencode()

    sort_links = {
        'marca': make_link('marca'), 'marca_desc': make_link('-marca'),
        'modelo': make_link('modelo'), 'modelo_desc': make_link('-modelo'),
        'consumo': make_link('consumo_medio'), 'consumo_desc': make_link('-consumo_medio'),
        'tipo': make_link('tipo'), 'tipo_desc': make_link('-tipo'),
    }

    for v in page_obj.object_list:
        v.transportadora_name = getattr(v.transportadora, 'razao_social', '') if v.transportadora else ''

    tipo_counts = []
    for val, label in tipo_choices:
        cnt = Vehicle.objects.filter(empresa=request.user.empresa, tipo=val).count()
        tipo_counts.append({'key': val, 'label': label, 'count': cnt})

    active_count = Vehicle.objects.filter(empresa=request.user.empresa, ativo=True).count()

    return render(request, 'cadastros/vehicle/vehicle_list.html', {
        'page_obj': page_obj,
        'total': veiculos.count(),
        'active_count': active_count,
        'transportadoras_count': len(list(transportadoras)),
        'tipo_used_count': sum(1 for t in tipo_counts if t['count'] > 0),
        'tipo_choices': tipo_choices,
        'fuel_choices': fuel_choices,
        'transportadoras': transportadoras,
        'sort_links': sort_links,
        'tipo_counts': tipo_counts,
    })


@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)
    plate_form = VehiclePlateForm()

    abastecimentos_qs = AbastecimentoVeiculo.objects.filter(vehicle=vehicle).order_by('-data', '-criado_em')
    data_ini = request.GET.get('data_ini')
    data_fim = request.GET.get('data_fim')
    if data_ini:
        abastecimentos_qs = abastecimentos_qs.filter(data__gte=data_ini)
    if data_fim:
        abastecimentos_qs = abastecimentos_qs.filter(data__lte=data_fim)

    return render(request, 'cadastros/vehicle/vehicle_detail.html', {
        'vehicle': vehicle,
        'plates': vehicle.plates.all().order_by('-atual', '-vigencia_inicio'),
        'plate_form': plate_form,
        'abastecimentos': abastecimentos_qs[:30],
        'data_ini': data_ini or '',
        'data_fim': data_fim or '',
        'total_abastecimentos': AbastecimentoVeiculo.objects.filter(vehicle=vehicle).count(),
    })


@login_required
def vehicle_create(request):
    if not request.user.empresa:
        messages.warning(request, 'Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, empresa=request.user.empresa)
        if form.is_valid():
            v = form.save(user=request.user)
            messages.success(request, f'Veículo "{v}" cadastrado com sucesso!')
            return redirect('frota:vehicle_detail', pk=v.pk)
        else:
            campos_com_erro = []
            for field_name, errors in form.errors.items():
                campo_label = 'Formulário' if field_name == '__all__' else (form.fields[field_name].label if field_name in form.fields else field_name)
                campos_com_erro.append(f"{campo_label}: {', '.join(errors)}")
            messages.error(request, 'Corrija os erros no formulário:<br>' + '<br>'.join(f'• {e}' for e in campos_com_erro))
    else:
        form = VehicleForm(empresa=request.user.empresa)

    return render(request, 'cadastros/vehicle/vehicle_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = VehicleForm(request.POST, request.FILES, instance=vehicle, empresa=request.user.empresa)
        if form.is_valid():
            v = form.save(user=request.user)
            messages.success(request, f'Veículo "{v}" atualizado!')
            return redirect('frota:vehicle_list')
        else:
            campos_com_erro = []
            for field_name, errors in form.errors.items():
                campo_label = 'Formulário' if field_name == '__all__' else (form.fields[field_name].label if field_name in form.fields else field_name)
                campos_com_erro.append(f"{campo_label}: {', '.join(errors)}")
            messages.error(request, 'Corrija os erros no formulário:<br>' + '<br>'.join(f'• {e}' for e in campos_com_erro))
    else:
        form = VehicleForm(instance=vehicle, empresa=request.user.empresa)

    return render(request, 'cadastros/vehicle/vehicle_form.html', {'form': form, 'vehicle': vehicle, 'action': 'Editar'})


@login_required
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        nome = str(vehicle)
        vehicle.delete()
        messages.success(request, f'Veículo "{nome}" excluído com sucesso!')
        return redirect('frota:vehicle_list')
    return render(request, 'cadastros/vehicle/vehicle_confirm_delete.html', {'vehicle': vehicle})


@login_required
def vehicle_plate_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = VehiclePlateForm(request.POST, vehicle=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, 'Placa adicionada com sucesso!')
        else:
            messages.error(request, 'Corrija os erros no formulário de placa.')
    return redirect('frota:vehicle_detail', pk=vehicle.pk)


@login_required
def vehicle_plate_update(request, vehicle_pk, plate_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    plate = get_object_or_404(VehiclePlate, pk=plate_pk, vehicle=vehicle)

    if request.method == 'POST':
        form = VehiclePlateForm(request.POST, instance=plate, vehicle=vehicle)
        if form.is_valid():
            plate = form.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True, 'placa': plate.placa,
                    'vigencia_inicio': plate.vigencia_inicio.isoformat() if plate.vigencia_inicio else None,
                    'vigencia_fim': plate.vigencia_fim.isoformat() if plate.vigencia_fim else None,
                    'atual': plate.atual, 'plate_pk': plate.pk,
                })
            messages.success(request, 'Placa atualizada com sucesso!')
            return redirect('frota:vehicle_detail', pk=vehicle.pk)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, 'Corrija os erros no formulário de placa.')
    else:
        form = VehiclePlateForm(instance=plate, vehicle=vehicle)

    return render(request, 'cadastros/vehicle/vehicle_plate_form.html', {
        'form': form, 'vehicle': vehicle, 'plate': plate, 'action': 'Editar Placa'
    })


@login_required
def vehicle_plate_delete(request, vehicle_pk, plate_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    plate = get_object_or_404(VehiclePlate, pk=plate_pk, vehicle=vehicle)

    if request.method == 'POST':
        placa = plate.placa
        plate.delete()
        messages.success(request, f'Placa "{placa}" excluída com sucesso!')
        return redirect('frota:vehicle_detail', pk=vehicle.pk)

    return render(request, 'cadastros/vehicle/vehicle_plate_confirm_delete.html', {
        'vehicle': vehicle, 'plate': plate
    })


@login_required
def api_vehicles(request):
    if not request.user.empresa:
        return JsonResponse({'error': 'Usuário sem empresa'}, status=400)

    qs = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(plates__placa__icontains=q)
        ).distinct()

    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    tipo_combustivel = request.GET.get('tipo_combustivel')
    if tipo_combustivel:
        qs = qs.filter(tipo_combustivel=tipo_combustivel)

    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        qs = qs.filter(transportadora__pk=transportadora_id)

    sort = request.GET.get('sort')
    allowed_sort = {'marca', '-marca', 'modelo', '-modelo', 'consumo_medio', '-consumo_medio', 'tipo', '-tipo'}
    if sort in allowed_sort:
        qs = qs.order_by(sort)

    page = int(request.GET.get('page', 1))
    per = int(request.GET.get('per', 20))
    paginator = Paginator(qs, per)
    page_obj = paginator.get_page(page)

    items = []
    for v in page_obj.object_list:
        transportadora = None
        if v.transportadora:
            transportadora = {'id': v.transportadora.pk, 'razao_social': getattr(v.transportadora, 'razao_social', '')}
        placa_atual = v.get_current_plate()
        if not placa_atual:
            first_plate = v.plates.order_by('-atual', '-vigencia_inicio').first()
            placa_atual = first_plate.placa if first_plate else None

        items.append({
            'id': v.pk, 'marca': v.marca, 'modelo': v.modelo, 'tipo': v.tipo,
            'placa_atual': placa_atual, 'renavam': v.renavam, 'chassis': v.chassis,
            'numero_motor': v.numero_motor, 'tipo_combustivel': v.tipo_combustivel,
            'codigo_patrimonio': v.codigo_patrimonio,
            'consumo_medio': str(v.consumo_medio) if v.consumo_medio is not None else None,
            'capacidade_ton': str(v.capacidade_ton) if v.capacidade_ton is not None else None,
            'tara_kg': v.tara_kg, 'eixos': v.eixos, 'transportadora': transportadora,
        })

    return JsonResponse({'count': paginator.count, 'num_pages': paginator.num_pages, 'page': page_obj.number, 'items': items})


@login_required
def vehicle_export_csv(request):
    if not request.user.empresa:
        return redirect('dashboard:index')

    qs = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates').order_by('pk')

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename=veiculos.csv'
    writer = csv.writer(resp)

    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)
    tipo_combustivel = request.GET.get('tipo_combustivel')
    if tipo_combustivel:
        qs = qs.filter(tipo_combustivel=tipo_combustivel)
    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        qs = qs.filter(transportadora__pk=transportadora_id)

    writer.writerow(['id', 'marca', 'modelo', 'tipo', 'placa_atual', 'renavam', 'chassis', 'numero_motor', 'tipo_combustivel', 'codigo_patrimonio', 'consumo_medio', 'transportadora_id', 'transportadora_razao_social'])

    for v in qs:
        tid = v.transportadora.pk if v.transportadora else ''
        tname = getattr(v.transportadora, 'razao_social', '') if v.transportadora else ''
        writer.writerow([
            v.pk, v.marca, v.modelo, v.tipo, v.get_current_plate() or '',
            v.renavam or '', v.chassis or '', v.numero_motor or '',
            v.tipo_combustivel or '', v.codigo_patrimonio or '',
            str(v.consumo_medio) if v.consumo_medio is not None else '',
            tid, tname,
        ])

    return resp
