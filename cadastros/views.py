"""
Views do módulo Fazendas
CRUD completo + integração com APIs externas
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.utils import timezone
import requests
import re
from django.core.cache import cache
from .models import FornecedorEndereco, Funcionario, FuncaoFuncionario
from .forms import FornecedorEnderecoForm, FuncionarioForm, FuncaoFuncionarioForm

from .models import (
    Fazenda, EnderecoFazenda, ContatoFazenda,
    ContaBancariaFazenda, DocumentoFazenda, DocumentoFornecedor,
    Area, Talhao, Cultura, HistoricoTalhao, Safra,
    Vendedor, ComissaoVendedor, Fornecedor, FornecedorContato, FornecedorDadoBancario, Porto,
    Cliente, EnderecoCliente, ContatoCliente, ContaBancariaCliente, DocumentoCliente
)

from .forms import VendedorForm, VendedorFiltroForm, ComissaoVendedorForm, FornecedorForm, FornecedorContatoForm, FornecedorDadoBancarioForm, TransportadoraForm

from .forms import (
    FazendaForm, EnderecoFazendaForm, ContatoFazendaForm,
    ContaBancariaFazendaForm, DocumentoFazendaForm, DocumentoFornecedorForm,
    
    AreaForm, TalhaoForm, CulturaForm, HistoricoTalhaoForm, SafraForm, PortoForm,

    # Cliente-related forms
    ClienteForm, EnderecoClienteForm, ContatoClienteForm, ContaBancariaClienteForm, DocumentoClienteForm,
)

# Transportadora views (moved to a dedicated module for clarity)
from .views_transportadora import (
    transportadora_list, transportadora_detail,
    transportadora_create, transportadora_update, transportadora_delete,
    transportadora_update_frete
)

# API views
from .views_api import api_transportadoras, api_transportadora_viagens

# Vehicle related imports
from .models import Vehicle, VehiclePlate, VehicleDocument
from .forms import VehicleForm, VehiclePlateForm


# ==================== VEÍCULOS (FROTA) ====================

@login_required
def vehicle_list(request):
    """Lista veículos da empresa"""
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    veiculos = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates', 'transportadora')

    q = request.GET.get('q', '').strip()
    if q:
        veiculos = veiculos.filter(
            Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(plates__placa__icontains=q)
        ).distinct()

    # Filters
    tipo = request.GET.get('tipo', '').strip()
    if tipo:
        veiculos = veiculos.filter(tipo=tipo)

    tipo_combustivel = request.GET.get('tipo_combustivel', '').strip()
    if tipo_combustivel:
        veiculos = veiculos.filter(tipo_combustivel=tipo_combustivel)

    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        veiculos = veiculos.filter(transportadora__pk=transportadora_id)



    # Ordering
    sort = request.GET.get('sort')
    allowed_sort = {'marca', '-marca', 'modelo', '-modelo', 'consumo_medio', '-consumo_medio', 'tipo', '-tipo'}
    if sort in allowed_sort:
        veiculos = veiculos.order_by(sort)

    # Pagination: show 10 items per page for a compact list view
    paginator = Paginator(veiculos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Prepare extra context for template
    transportadoras = []
    try:
        from .models import Transportadora
        transportadoras = Transportadora.objects.filter(empresa=request.user.empresa).order_by('razao_social')
    except Exception:
        transportadoras = []

    tipo_choices = Vehicle._meta.get_field('tipo').choices
    fuel_choices = Vehicle._meta.get_field('tipo_combustivel').choices

    # Build sort links (querystrings)
    base_qs = request.GET.copy()
    sort_links = {}
    def make_link(value):
        qs = base_qs.copy()
        qs['sort'] = value
        return qs.urlencode()
    sort_links['marca'] = make_link('marca')
    sort_links['marca_desc'] = make_link('-marca')
    sort_links['modelo'] = make_link('modelo')
    sort_links['modelo_desc'] = make_link('-modelo')
    sort_links['consumo'] = make_link('consumo_medio')
    sort_links['consumo_desc'] = make_link('-consumo_medio')
    sort_links['tipo'] = make_link('tipo')
    sort_links['tipo_desc'] = make_link('-tipo')

    # Compute transport names for vehicles in the current page
    for v in page_obj.object_list:
        v.transportadora_name = getattr(v.transportadora, 'razao_social', '') if v.transportadora else ''

    # Counts per vehicle tipo (Leve, Médio, Pesado, etc.)
    tipo_counts = []
    for val, label in tipo_choices:
        cnt = Vehicle.objects.filter(empresa=request.user.empresa, tipo=val).count()
        tipo_counts.append({'key': val, 'label': label, 'count': cnt})

    # Extra metrics for header stats
    active_count = Vehicle.objects.filter(empresa=request.user.empresa, ativo=True).count()
    transportadoras_count = len(transportadoras)
    tipo_used_count = sum(1 for t in tipo_counts if t['count'] > 0)

    return render(request, 'cadastros/vehicle/vehicle_list.html', {
        'page_obj': page_obj,
        'total': veiculos.count(),
        'active_count': active_count,
        'transportadoras_count': transportadoras_count,
        'tipo_used_count': tipo_used_count,
        'tipo_choices': tipo_choices,
        'fuel_choices': fuel_choices,
        'transportadoras': transportadoras,
        'sort_links': sort_links,
        'tipo_counts': tipo_counts,
    })


@login_required
def vehicle_detail(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)

    # Assignment form moved to a dedicated page; only prepare plate form here
    plate_form = VehiclePlateForm()

    context = {
        'vehicle': vehicle,
        'plates': vehicle.plates.all().order_by('-atual', '-vigencia_inicio'),
        'plate_form': plate_form,
    }
    return render(request, 'cadastros/vehicle/vehicle_detail.html', context)


@login_required
def vehicle_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = VehicleForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            v = form.save(user=request.user)
            messages.success(request, f'✅ Veículo "{v}" cadastrado com sucesso!')
            return redirect('cadastros:vehicle_detail', pk=v.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = VehicleForm(empresa=request.user.empresa)

    return render(request, 'cadastros/vehicle/vehicle_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def vehicle_update(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle, empresa=request.user.empresa)
        if form.is_valid():
            v = form.save(user=request.user)
            messages.success(request, f'✅ Veículo "{v}" atualizado!')
            return redirect('cadastros:vehicle_list')
    else:
        form = VehicleForm(instance=vehicle, empresa=request.user.empresa)

    return render(request, 'cadastros/vehicle/vehicle_form.html', {'form': form, 'vehicle': vehicle, 'action': 'Editar'})


@login_required
def vehicle_delete(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        nome = str(vehicle)
        vehicle.delete()
        messages.success(request, f'🗑️ Veículo "{nome}" excluído com sucesso!')
        return redirect('cadastros:vehicle_list')
    return render(request, 'cadastros/vehicle/vehicle_confirm_delete.html', {'vehicle': vehicle})


@login_required
def vehicle_plate_create(request, vehicle_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = VehiclePlateForm(request.POST, vehicle=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Placa adicionada com sucesso!')
            return redirect('cadastros:vehicle_detail', pk=vehicle.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário de placa.')
    return redirect('cadastros:vehicle_detail', pk=vehicle.pk)  # template for plate handled via vehicle page


@login_required
def vehicle_plate_update(request, vehicle_pk, plate_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    plate = get_object_or_404(VehiclePlate, pk=plate_pk, vehicle=vehicle)

    if request.method == 'POST':
        form = VehiclePlateForm(request.POST, instance=plate, vehicle=vehicle)
        if form.is_valid():
            plate = form.save()
            # If AJAX, return JSON with updated values
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'placa': plate.placa,
                    'vigencia_inicio': plate.vigencia_inicio.isoformat() if plate.vigencia_inicio else None,
                    'vigencia_fim': plate.vigencia_fim.isoformat() if plate.vigencia_fim else None,
                    'atual': plate.atual,
                    'plate_pk': plate.pk,
                })
            messages.success(request, '✅ Placa atualizada com sucesso!')
            return redirect('cadastros:vehicle_detail', pk=vehicle.pk)
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, '❌ Corrija os erros no formulário de placa.')
    else:
        form = VehiclePlateForm(instance=plate, vehicle=vehicle)

    return render(request, 'cadastros/vehicle/vehicle_plate_form.html', {
        'form': form,
        'vehicle': vehicle,
        'plate': plate,
        'action': 'Editar Placa'
    })


@login_required
def vehicle_plate_delete(request, vehicle_pk, plate_pk):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    plate = get_object_or_404(VehiclePlate, pk=plate_pk, vehicle=vehicle)

    if request.method == 'POST':
        placa = plate.placa
        plate.delete()
        messages.success(request, f'🗑️ Placa "{placa}" excluída com sucesso!')
        return redirect('cadastros:vehicle_detail', pk=vehicle.pk)

    return render(request, 'cadastros/vehicle/vehicle_plate_confirm_delete.html', {
        'vehicle': vehicle,
        'plate': plate
    })








# ==================== VEÍCULOS: API / EXPORT ====================

@login_required
def api_vehicles(request):
    """JSON list of vehicles (paginated) including optional fields"""
    if not request.user.empresa:
        return JsonResponse({'error': 'Usuário sem empresa'}, status=400)

    qs = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates')

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(plates__placa__icontains=q)
        ).distinct()

    # Additional filters
    tipo = request.GET.get('tipo')
    if tipo:
        qs = qs.filter(tipo=tipo)

    tipo_combustivel = request.GET.get('tipo_combustivel')
    if tipo_combustivel:
        qs = qs.filter(tipo_combustivel=tipo_combustivel)



    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        qs = qs.filter(transportadora__pk=transportadora_id)

    # Ordering
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

        # Resolve placa_atual: prefer placa marcada como atual, else fallback to first plate if available
        placa_atual = v.get_current_plate()
        if not placa_atual:
            first_plate = v.plates.order_by('-atual', '-vigencia_inicio').first()
            placa_atual = first_plate.placa if first_plate else None

        items.append({
            'id': v.pk,
            'marca': v.marca,
            'modelo': v.modelo,
            'tipo': v.tipo,
            'placa_atual': placa_atual,
            'renavam': v.renavam,
            'chassis': v.chassis,
            'numero_motor': v.numero_motor,
            'tipo_combustivel': v.tipo_combustivel,
            'codigo_patrimonio': v.codigo_patrimonio,
            'consumo_medio': str(v.consumo_medio) if v.consumo_medio is not None else None,
            'capacidade_ton': str(v.capacidade_ton) if v.capacidade_ton is not None else None,
            'tara_kg': v.tara_kg,
            'eixos': v.eixos,
            'transportadora': transportadora,
        })

    return JsonResponse({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'page': page_obj.number,
        'items': items
    })


@login_required
def vehicle_export_csv(request):
    """Export vehicles for user's company as CSV including the optional fields"""
    import csv
    if not request.user.empresa:
        return redirect('dashboard:index')

    qs = Vehicle.objects.filter(empresa=request.user.empresa).prefetch_related('plates').order_by('pk')

    # Prepare response
    from django.http import HttpResponse
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename=veiculos.csv'

    writer = csv.writer(resp)
    # Support filters/order parameters on export as well
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

    header = ['id', 'marca', 'modelo', 'tipo', 'placa_atual', 'renavam', 'chassis', 'numero_motor', 'tipo_combustivel', 'codigo_patrimonio', 'consumo_medio', 'transportadora_id', 'transportadora_razao_social']
    writer.writerow(header)

    for v in qs:
        transportadora_id = v.transportadora.pk if v.transportadora else ''
        transportadora_razao = getattr(v.transportadora, 'razao_social', '') if v.transportadora else ''
        writer.writerow([
            v.pk,
            v.marca,
            v.modelo,
            v.tipo,
            v.get_current_plate() or '',
            v.renavam or '',
            v.chassis or '',
            v.numero_motor or '',
            v.tipo_combustivel or '',
            v.codigo_patrimonio or '',
            str(v.consumo_medio) if v.consumo_medio is not None else '',
            transportadora_id,
            transportadora_razao,
            current_driver_id,
            current_driver_nome,
        ])

    return resp


# ==================== FAZENDAS ====================

@login_required
def fazenda_list(request):
    """Lista todas as fazendas da empresa"""
    # ✅ Verifica se usuário tem empresa
    if not request.user.empresa:
        messages.warning(
            request,
            '⚠️ Seu usuário não está vinculado a nenhuma empresa. '
            'Entre em contato com o administrador.'
        )
        return redirect('dashboard:index')
    
    fazendas = Fazenda.objects.filter(
        empresa=request.user.empresa
    ).select_related('empresa').prefetch_related(
        'enderecos', 'contatos', 'contas_bancarias', 'documentos'
    )
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        fazendas = fazendas.filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj_cpf__icontains=q)
        )
    
    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'ativas':
        fazendas = fazendas.filter(ativa=True)
    elif status == 'inativas':
        fazendas = fazendas.filter(ativa=False)
    
    # Paginação
    paginator = Paginator(fazendas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Informações adicionais
    context = {
        'page_obj': page_obj,
        'total_fazendas': fazendas.count(),
        'limite_plano': request.user.empresa.limite_fazendas,
        'pode_adicionar': fazendas.filter(ativa=True).count() < request.user.empresa.limite_fazendas,
    }
    
    return render(request, 'cadastros/fazenda/fazenda_list.html', context)


@login_required
def fazenda_detail(request, pk):
    """Detalhes completos da fazenda"""
    fazenda = get_object_or_404(
        Fazenda.objects.prefetch_related(
            'enderecos', 'contatos', 'contas_bancarias', 'documentos'
        ),
        pk=pk,
        empresa=request.user.empresa
    )
    
    # Documentos que precisam de atenção
    docs_vencidos = fazenda.documentos.filter(
        data_validade__lt=timezone.now().date(),
        gerar_alerta_vencimento=True
    )
    
    docs_vencendo = []
    for doc in fazenda.documentos.filter(gerar_alerta_vencimento=True):
        if doc.precisa_alerta():
            docs_vencendo.append(doc)
    
    context = {
        'fazenda': fazenda,
        'docs_vencidos': docs_vencidos,
        'docs_vencendo': docs_vencendo,
    }
    
    return render(request, 'cadastros/fazenda/fazenda_detail.html', context)


@login_required
def fazenda_create(request):
    """Cria nova fazenda"""
    # ✅ Verifica se usuário tem empresa
    if not request.user.empresa:
        messages.warning(
            request,
            '⚠️ Seu usuário não está vinculado a nenhuma empresa. '
            'Entre em contato com o administrador.'
        )
        return redirect('dashboard:index')
    
    # Verifica limite do plano
    total_fazendas_ativas = Fazenda.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    ).count()
    
    if total_fazendas_ativas >= request.user.empresa.limite_fazendas:
        messages.error(
            request,
            f'❌ Limite de fazendas atingido! Seu plano permite apenas '
            f'{request.user.empresa.limite_fazendas} fazenda(s) ativa(s). '
            f'Faça upgrade do plano para cadastrar mais.'
        )
        return redirect('cadastros:fazenda_list')
    
    if request.method == 'POST':
        form = FazendaForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            try:
                fazenda = form.save()
                messages.success(request, f'✅ Fazenda "{fazenda.nome}" cadastrada com sucesso!')
                return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
            except Exception as e:
                messages.error(request, f'❌ Erro ao salvar: {e}')
        else:
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')
    else:
        form = FazendaForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/fazenda/fazenda_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })

@login_required
def fazenda_update(request, pk):
    """Edita fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FazendaForm(
            request.POST,
            instance=fazenda,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            fazenda = form.save()
            messages.success(request, f'✅ Fazenda "{fazenda.nome}" atualizada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = FazendaForm(
            instance=fazenda,
            empresa=request.user.empresa,
            usuario=request.user
            
        )
    
    return render(request, 'cadastros/fazenda/fazenda_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Editar'
    })


@login_required
def fazenda_delete(request, pk):
    """Deleta fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=pk, empresa=request.user.empresa)
    
    # Verifica se tem talhões ou outras dependências
    # total_talhoes = fazenda.talhoes.count()
    # if total_talhoes > 0:
    #     messages.error(request, f'❌ Não é possível excluir! A fazenda possui {total_talhoes} talhão(ões) cadastrado(s).')
    #     return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    if request.method == 'POST':
        nome = fazenda.nome
        fazenda.delete()
        messages.success(request, f'🗑️ Fazenda "{nome}" excluída com sucesso!')
        return redirect('cadastros:fazenda_list')
    
    return render(request, 'cadastros/fazenda/fazenda_confirm_delete.html', {'fazenda': fazenda})


# ==================== PORTOS ====================

@login_required
def porto_list(request):
    """Lista os portos da empresa - versão card-based, espelhada em `fornecedor_list`"""
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa. Entre em contato com o administrador.')
        return redirect('dashboard:index')

    portos_qs = Porto.objects.filter(empresa=request.user.empresa)

    q = request.GET.get('q', '').strip()
    tipo_atual = request.GET.get('tipo', '')

    if q:
        portos_qs = portos_qs.filter(
            Q(codigo__icontains=q) | Q(nome__icontains=q) | Q(cidade__icontains=q)
        )

    if tipo_atual:
        portos_qs = portos_qs.filter(tipo=tipo_atual)

    paginator = Paginator(portos_qs, 25)
    portos = paginator.get_page(request.GET.get('page'))

    return render(request, 'cadastros/porto/porto_list.html', {
        'portos': portos,
        'q': q,
        'tipo_atual': tipo_atual,
        'total_portos': portos_qs.count(),
    })


@login_required
def porto_detail(request, pk):
    porto = get_object_or_404(Porto, pk=pk, empresa=request.user.empresa)
    return render(request, 'cadastros/porto/porto_detail.html', {'porto': porto})


@login_required
def porto_create(request):
    if not request.user.empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa. Entre em contato com o administrador.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = PortoForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            porto = form.save()
            messages.success(request, f'✅ Porto "{porto.nome}" cadastrado com sucesso!')
            return redirect('cadastros:porto_detail', pk=porto.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário abaixo.')
    else:
        form = PortoForm(empresa=request.user.empresa)

    return render(request, 'cadastros/porto/porto_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def porto_update(request, pk):
    porto = get_object_or_404(Porto, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        form = PortoForm(request.POST, instance=porto, empresa=request.user.empresa)
        if form.is_valid():
            porto = form.save()
            messages.success(request, f'✅ Porto "{porto.nome}" atualizado!')
            return redirect('cadastros:porto_detail', pk=porto.pk)
    else:
        form = PortoForm(instance=porto, empresa=request.user.empresa)

    return render(request, 'cadastros/porto/porto_form.html', {
        'form': form,
        'porto': porto,
        'action': 'Editar'
    })


@login_required
def porto_delete(request, pk):
    porto = get_object_or_404(Porto, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        nome = porto.nome
        porto.delete()
        messages.success(request, f'🗑️ Porto "{nome}" excluído com sucesso!')
        return redirect('cadastros:porto_list')

    return render(request, 'cadastros/porto/porto_confirm_delete.html', {'porto': porto})


# ==================== API EXTERNA - CNPJ ====================

def buscar_cnpj(request):
    # If AJAX + not authenticated return 401 JSON instead of redirect
    if not request.user.is_authenticated and (request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept','')):
        return JsonResponse({'erro': 'Não autorizado'}, status=401)
    """Busca dados do CNPJ via API ReceitaWS. Suporta POST e GET (parâmetro 'cnpj') e implementa cache."""
    # Accept GET or POST for AJAX convenience
    cnpj = ''
    if request.method == 'POST':
        cnpj = request.POST.get('cnpj', '')
    elif request.method == 'GET':
        cnpj = request.GET.get('cnpj', '')
    else:
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    cnpj = cnpj.replace('.', '').replace('/', '').replace('-', '')
    if len(cnpj) != 14:
        return JsonResponse({'erro': 'CNPJ inválido'}, status=400)

    cache_key = f'buscar_cnpj:{cnpj}'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        # API ReceitaWS (gratuita)
        url = f'https://www.receitaws.com.br/v1/cnpj/{cnpj}'
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            dados = response.json()

            if dados.get('status') == 'ERROR':
                return JsonResponse({'erro': dados.get('message', 'CNPJ não encontrado')}, status=404)

            # Formata dados para retornar
            resultado = {
                'nome': dados.get('nome', ''),
                'nome_fantasia': dados.get('fantasia', ''),
                'cnpj': dados.get('cnpj', ''),
                'telefone': dados.get('telefone', ''),
                'email': dados.get('email', ''),
                'logradouro': dados.get('logradouro', ''),
                'numero': dados.get('numero', ''),
                'complemento': dados.get('complemento', ''),
                'bairro': dados.get('bairro', ''),
                'cidade': dados.get('municipio', ''),
                'uf': dados.get('uf', ''),
                'cep': dados.get('cep', '').replace('.', '').replace('-', ''),
            }

            payload = {'sucesso': True, 'dados': resultado}
            # Cache for 24 hours
            cache.set(cache_key, payload, timeout=60 * 60 * 24)
            return JsonResponse(payload)
        else:
            return JsonResponse({'erro': 'Erro ao consultar API'}, status=500)

    except requests.exceptions.Timeout:
        return JsonResponse({'erro': 'Timeout na consulta'}, status=500)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


# ==================== API EXTERNA - CEP ====================

@login_required
def buscar_cep(request):
    """Busca endereço via CEP usando ViaCEP. Suporta POST e GET e implementa cache."""
    if request.method == 'POST':
        cep = request.POST.get('cep', '').replace('-', '').replace('.', '')
    elif request.method == 'GET':
        cep = request.GET.get('cep', '').replace('-', '').replace('.', '')
    else:
        return JsonResponse({'erro': 'Método não permitido'}, status=405)

    if len(cep) != 8:
        return JsonResponse({'erro': 'CEP inválido'}, status=400)

    cache_key = f'buscar_cep:{cep}'
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        # API ViaCEP (gratuita)
        url = f'https://viacep.com.br/ws/{cep}/json/'
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            dados = response.json()

            if dados.get('erro'):
                return JsonResponse({'erro': 'CEP não encontrado'}, status=404)

            resultado = {
                'cep': dados.get('cep', ''),
                'logradouro': dados.get('logradouro', ''),
                'complemento': dados.get('complemento', ''),
                'bairro': dados.get('bairro', ''),
                'cidade': dados.get('localidade', ''),
                'uf': dados.get('uf', ''),
            }
            # Return both wrapped ('dados') and flat keys for backward compatibility with older clients
            resp_payload = {'sucesso': True, 'dados': resultado}
            resp_payload.update(resultado)
            # Cache for 24 hours
            cache.set(cache_key, resp_payload, timeout=60 * 60 * 24)
            return JsonResponse(resp_payload)
        else:
            return JsonResponse({'erro': 'Erro ao consultar API'}, status=500)

    except requests.exceptions.Timeout:
        return JsonResponse({'erro': 'Timeout na consulta'}, status=500)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


# ==================== ENDEREÇOS ====================

@login_required
def endereco_create(request, fazenda_pk):
    """Adiciona endereço à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = EnderecoFazendaForm(request.POST)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.fazenda = fazenda
            endereco.save()
            messages.success(request, '✅ Endereço adicionado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = EnderecoFazendaForm()
    
    return render(request, 'cadastros/endereco/endereco_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def endereco_update(request, fazenda_pk, endereco_pk):
    """Edita endereço"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoFazenda, pk=endereco_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = EnderecoFazendaForm(request.POST, instance=endereco)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Endereço atualizado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = EnderecoFazendaForm(instance=endereco)
    
    return render(request, 'cadastros/endereco/endereco_form.html', {
        'form': form,
        'fazenda': fazenda,
        'endereco': endereco,
        'action': 'Editar'
    })


@login_required
def endereco_delete(request, fazenda_pk, endereco_pk):
    """Remove endereço"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoFazenda, pk=endereco_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, '🗑️ Endereço removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/endereco/endereco_confirm_delete.html', {
        'fazenda': fazenda,
        'endereco': endereco
    })


# ==================== CONTATOS ====================

@login_required
def contato_create(request, fazenda_pk):
    """Adiciona contato à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ContatoFazendaForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.fazenda = fazenda
            contato.save()
            messages.success(request, '✅ Contato adicionado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContatoFazendaForm()
    
    return render(request, 'cadastros/contato/contato_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def contato_update(request, fazenda_pk, contato_pk):
    """Edita contato"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoFazenda, pk=contato_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = ContatoFazendaForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Contato atualizado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContatoFazendaForm(instance=contato)
    
    return render(request, 'cadastros/contato/contato_form.html', {
        'form': form,
        'fazenda': fazenda,
        'contato': contato,
        'action': 'Editar'
    })


@login_required
def contato_delete(request, fazenda_pk, contato_pk):
    """Remove contato"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoFazenda, pk=contato_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        contato.delete()
        messages.success(request, '🗑️ Contato removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/contato/contato_confirm_delete.html', {
        'fazenda': fazenda,
        'contato': contato
    })


# ==================== CONTAS BANCÁRIAS ====================

@login_required
def conta_bancaria_create(request, fazenda_pk):
    """Adiciona conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ContaBancariaFazendaForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.fazenda = fazenda
            conta.save()
            messages.success(request, '✅ Conta bancária adicionada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContaBancariaFazendaForm()
    
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def conta_bancaria_update(request, fazenda_pk, conta_pk):
    """Edita conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaFazenda, pk=conta_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        form = ContaBancariaFazendaForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Conta bancária atualizada!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = ContaBancariaFazendaForm(instance=conta)
    
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {
        'form': form,
        'fazenda': fazenda,
        'conta': conta,
        'action': 'Editar'
    })


@login_required
def conta_bancaria_delete(request, fazenda_pk, conta_pk):
    """Remove conta bancária"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaFazenda, pk=conta_pk, fazenda=fazenda)
    
    if request.method == 'POST':
        conta.delete()
        messages.success(request, '🗑️ Conta bancária removida!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_confirm_delete.html', {
        'fazenda': fazenda,
        'conta': conta
    })


# ==================== DOCUMENTOS ====================

@login_required
def documento_create(request, fazenda_pk):
    """Adiciona documento à fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = DocumentoFazendaForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.fazenda = fazenda
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, '✅ Documento anexado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = DocumentoFazendaForm()
    
    return render(request, 'cadastros/documento/documento_form.html', {
        'form': form,
        'fazenda': fazenda,
        'action': 'Adicionar'
    })


@login_required
def fornecedor_documento_create(request, fornecedor_pk):
    """Adiciona documento ao fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)

    if request.method == 'POST':
        form = DocumentoFornecedorForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.fornecedor = fornecedor
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, '✅ Documento anexado ao fornecedor!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            # Form inválido — será re-renderizado com erros
            pass
    else:
        form = DocumentoFornecedorForm()

    return render(request, 'cadastros/documento/documento_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'action': 'Adicionar'
    })


@login_required
def documento_update(request, fazenda_pk, documento_pk):
    """Edita um documento da fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoFazenda, pk=documento_pk, fazenda=fazenda)

    if request.method == 'POST':
        form = DocumentoFazendaForm(request.POST, request.FILES, instance=documento)
        if form.is_valid():
            # Se um novo arquivo foi enviado, remove o antigo antes de salvar
            if 'arquivo' in request.FILES and documento.arquivo:
                documento.arquivo.delete()
            form.save()
            messages.success(request, '✅ Documento atualizado!')
            return redirect('cadastros:fazenda_detail', pk=fazenda.pk)
    else:
        form = DocumentoFazendaForm(instance=documento)

    return render(request, 'cadastros/documento/documento_form.html', {
        'form': form,
        'fazenda': fazenda,
        'documento': documento,
        'action': 'Editar'
    })


@login_required
def fornecedor_documento_update(request, fornecedor_pk, documento_pk):
    """Edita um documento do fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoFornecedor, pk=documento_pk, fornecedor=fornecedor)

    if request.method == 'POST':
        form = DocumentoFornecedorForm(request.POST, request.FILES, instance=documento)
        if form.is_valid():
            if 'arquivo' in request.FILES and documento.arquivo:
                documento.arquivo.delete()
            form.save()
            messages.success(request, '✅ Documento atualizado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    else:
        form = DocumentoFornecedorForm(instance=documento)

    return render(request, 'cadastros/documento/documento_form.html', {
        'form': form,
        'fornecedor': fornecedor,
        'documento': documento,
        'action': 'Editar'
    })


@login_required
def documento_delete(request, fazenda_pk, documento_pk):
    """Remove documento da fazenda"""
    fazenda = get_object_or_404(Fazenda, pk=fazenda_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoFazenda, pk=documento_pk, fazenda=fazenda)

    if request.method == 'POST':
        # Remove arquivo físico
        if documento.arquivo:
            documento.arquivo.delete()
        
        documento.delete()
        messages.success(request, '🗑️ Documento removido!')
        return redirect('cadastros:fazenda_detail', pk=fazenda.pk)

    return render(request, 'cadastros/documento/documento_confirm_delete.html', {
        'fazenda': fazenda,
        'documento': documento
    })


@login_required
def fornecedor_documento_delete(request, fornecedor_pk, documento_pk):
    """Remove documento do fornecedor"""
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoFornecedor, pk=documento_pk, fornecedor=fornecedor)

    if request.method == 'POST':
        if documento.arquivo:
            documento.arquivo.delete()
        documento.delete()
        messages.success(request, '🗑️ Documento removido!')
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)

    return render(request, 'cadastros/documento/documento_confirm_delete.html', {
        'fornecedor': fornecedor,
        'documento': documento
    })


# ==================== ALERTAS ====================

@login_required
def dashboard_alertas(request):
    """Dashboard com alertas de documentos vencidos/vencendo"""
    fazendas = Fazenda.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    )
    
    docs_vencidos = []
    docs_vencendo = []
    
    for fazenda in fazendas:
        # Vencidos
        vencidos = DocumentoFazenda.objects.filter(
            fazenda=fazenda,
            data_validade__lt=timezone.now().date(),
            gerar_alerta_vencimento=True
        )
        docs_vencidos.extend(vencidos)
        
        # A vencer
        for doc in DocumentoFazenda.objects.filter(fazenda=fazenda, gerar_alerta_vencimento=True):
            if doc.precisa_alerta():
                docs_vencendo.append(doc)
    
    context = {
        'docs_vencidos': docs_vencidos,
        'docs_vencendo': docs_vencendo,
        'total_alertas': len(docs_vencidos) + len(docs_vencendo),
    }
    
    return render(request, 'cadastros/dashboard_alertas.html', context)




"""
ADICIONE ESTAS VIEWS AO FINAL DO ARQUIVO cadastros/views.py
"""




# ==================== FUNÇÕES ====================

@login_required
def funcao_list(request):
    """Lista funções de funcionários"""
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa)
    
    q = request.GET.get('q', '').strip()
    if q:
        funcoes = funcoes.filter(nome__icontains=q)
    
    return render(request, 'cadastros/funcao/funcao_list.html', {'funcoes': funcoes})


@login_required
def funcao_create_ajax(request):
    """Cria função via AJAX (para modal)"""
    if request.method == 'POST':
        form = FuncaoFuncionarioForm(request.POST)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.empresa = request.user.empresa
            funcao.save()
            
            return JsonResponse({
                'sucesso': True,
                'id': funcao.id,
                'nome': funcao.nome,
                'mensagem': f'Função "{funcao.nome}" criada com sucesso!'
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'erros': form.errors
            }, status=400)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)


@login_required
def funcao_create(request):
    """Cria função de funcionário (fallback non-AJAX)"""
    if request.method == 'POST':
        form = FuncaoFuncionarioForm(request.POST)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.empresa = request.user.empresa
            funcao.save()
            messages.success(request, f'✅ Função "{funcao.nome}" criada com sucesso!')
            return redirect('cadastros:funcao_list')
    else:
        form = FuncaoFuncionarioForm()
    return render(request, 'cadastros/funcao/funcao_form.html', {'form': form, 'action': 'Cadastrar'})


def funcao_update(request, pk):
    """Editar função de funcionário"""
    funcao = get_object_or_404(FuncaoFuncionario, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = FuncaoFuncionarioForm(request.POST, instance=funcao)
        if form.is_valid():
            funcao = form.save()
            messages.success(request, f'✅ Função "{funcao.nome}" atualizada!')
            return redirect('cadastros:funcao_list')
    else:
        form = FuncaoFuncionarioForm(instance=funcao)
    return render(request, 'cadastros/funcao/funcao_form.html', {'form': form, 'funcao': funcao, 'action': 'Editar'})


@login_required
def funcao_delete(request, pk):
    """Excluir função de funcionário (trata dependências)"""
    from django.db.models.deletion import ProtectedError
    funcao = get_object_or_404(FuncaoFuncionario, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        try:
            nome = funcao.nome
            funcao.delete()
            messages.success(request, f'🗑️ Função "{nome}" excluída com sucesso!')
            return redirect('cadastros:funcao_list')
        except ProtectedError:
            empregados = funcao.funcionarios.all()
            sample = ', '.join([str(e) for e in empregados[:10]])
            messages.error(request, f'❌ Não é possível excluir a função porque está atribuída a funcionários: {sample}')
            return redirect('cadastros:funcao_list')
    return render(request, 'cadastros/funcao/funcao_confirm_delete.html', {'funcao': funcao})


# ==================== FUNCIONÁRIOS ====================

@login_required
def funcionario_list(request):
    """Lista funcionários"""
    funcionarios = Funcionario.objects.filter(
        empresa=request.user.empresa
    ).select_related('funcao', 'fazenda')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        funcionarios = funcionarios.filter(
            Q(nome_completo__icontains=q) |
            Q(cpf__icontains=q) |
            Q(funcao__nome__icontains=q)
        )
    
    # Filtros
    status = request.GET.get('status', '')
    if status == 'ativos':
        funcionarios = funcionarios.filter(ativo=True)
    elif status == 'inativos':
        funcionarios = funcionarios.filter(ativo=False)
    
    fazenda_id = request.GET.get('fazenda', '')
    if fazenda_id:
        funcionarios = funcionarios.filter(fazenda_id=fazenda_id)
    
    funcao_id = request.GET.get('funcao', '')
    if funcao_id:
        funcionarios = funcionarios.filter(funcao_id=funcao_id)
    
    # Paginação
    paginator = Paginator(funcionarios, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Para filtros
    fazendas = Fazenda.objects.filter(empresa=request.user.empresa, ativa=True)
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa, ativa=True)
    
    context = {
        'page_obj': page_obj,
        'fazendas': fazendas,
        'funcoes': funcoes,
        'total_funcionarios': funcionarios.count(),
    }
    
    return render(request, 'cadastros/funcionario/funcionario_list.html', context)


@login_required
def funcionario_detail(request, pk):
    """Detalhes do funcionário"""
    funcionario = get_object_or_404(
        Funcionario,
        pk=pk,
        empresa=request.user.empresa
    )
    
    return render(request, 'cadastros/funcionario/funcionario_detail.html', {
        'funcionario': funcionario
    })


@login_required
def funcionario_create(request):
    """Cria funcionário"""
    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" cadastrado!')
            return redirect('cadastros:funcionario_detail', pk=funcionario.pk)
        else:
            # Surface validation errors to the top to help debugging in the UI
            try:
                errors_text = '\n'.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            except Exception:
                errors_text = str(form.errors)
            messages.error(request, f'❌ Erros no formulário: {errors_text}')
    else:
        form = FuncionarioForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    # Para o modal de nova função
    form_funcao = FuncaoFuncionarioForm()
    
    return render(request, 'cadastros/funcionario/funcionario_form.html', {
        'form': form,
        'form_funcao': form_funcao,
        'action': 'Cadastrar'
    })


@login_required
def funcionario_update(request, pk):
    """Edita funcionário"""
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            funcionario = form.save()
            messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" atualizado!')
            return redirect('cadastros:funcionario_detail', pk=funcionario.pk)
        else:
            # Surface validation errors to the top to help debugging in the UI
            try:
                errors_text = '\n'.join([f"{k}: {', '.join(v)}" for k, v in form.errors.items()])
            except Exception:
                errors_text = str(form.errors)
            messages.error(request, f'❌ Erros no formulário: {errors_text}')
    else:
        form = FuncionarioForm(
            instance=funcionario,
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    form_funcao = FuncaoFuncionarioForm()
    
    return render(request, 'cadastros/funcionario/funcionario_form.html', {
        'form': form,
        'form_funcao': form_funcao,
        'funcionario': funcionario,
        'action': 'Editar'
    })


@login_required
def funcionario_delete(request, pk):
    """Deleta funcionário"""
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        nome = funcionario.nome_completo
        funcionario.delete()
        messages.success(request, f'🗑️ Funcionário "{nome}" excluído!')
        return redirect('cadastros:funcionario_list')
    
    return render(request, 'cadastros/funcionario/funcionario_confirm_delete.html', {
        'funcionario': funcionario
    })



"""
ADICIONE ESTE CÓDIGO NO FINAL DO ARQUIVO cadastros/views.py
"""




# ==================== CULTURAS ====================

@login_required
def cultura_list(request):
    """Lista todas as culturas da empresa"""
    culturas = Cultura.objects.filter(
        empresa=request.user.empresa
    ).select_related('empresa', 'cadastrado_por')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        culturas = culturas.filter(
            Q(nome__icontains=q) |
            Q(variedade__icontains=q) |
            Q(nome_cientifico__icontains=q) |
            Q(codigo_interno__icontains=q)
        )
    
    # Filtro por tipo
    tipo = request.GET.get('tipo', '')
    if tipo:
        culturas = culturas.filter(tipo=tipo)
    
    # Filtro por status
    status = request.GET.get('status', '')
    if status == 'ativas':
        culturas = culturas.filter(ativa=True)
    elif status == 'inativas':
        culturas = culturas.filter(ativa=False)
    
    # Paginação
    paginator = Paginator(culturas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Informações adicionais
    context = {
        'page_obj': page_obj,
        'total_culturas': culturas.count(),
        'limite_plano': request.user.empresa.limite_produtos,
        'pode_adicionar': culturas.filter(ativa=True).count() < request.user.empresa.limite_produtos,
        'tipos_cultura': Cultura.TIPO_CULTURA,
    }
    
    return render(request, 'cadastros/cultura/cultura_list.html', context)


@login_required
def cultura_detail(request, pk):
    """Detalhes completos da cultura"""
    cultura = get_object_or_404(
        Cultura,
        pk=pk,
        empresa=request.user.empresa
    )
    
    context = {
        'cultura': cultura,
        # 'total_plantios': cultura.get_total_plantios(),  # Implementar depois
    }
    
    return render(request, 'cadastros/cultura/cultura_detail.html', context)


@login_required
def cultura_create(request):
    """Cria nova cultura"""
    # Verifica limite do plano
    total_culturas_ativas = Cultura.objects.filter(
        empresa=request.user.empresa,
        ativa=True
    ).count()
    
    if total_culturas_ativas >= request.user.empresa.limite_produtos:
        messages.error(
            request,
            f'❌ Limite de culturas atingido! Seu plano permite apenas '
            f'{request.user.empresa.limite_produtos} cultura(s) ativa(s). '
            f'Faça upgrade do plano para cadastrar mais.'
        )
        return redirect('cadastros:cultura_list')
    
    if request.method == 'POST':
        form = CulturaForm(
            request.POST,
            request.FILES,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            cultura = form.save()
            messages.success(request, f'✅ Cultura "{cultura.nome}" cadastrada com sucesso!')
            return redirect('cadastros:cultura_detail', pk=cultura.pk)
    else:
        form = CulturaForm(
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/cultura/cultura_form.html', {
        'form': form,
        'action': 'Cadastrar'
    })


@login_required
def cultura_update(request, pk):
    """Edita cultura"""
    cultura = get_object_or_404(Cultura, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = CulturaForm(
            request.POST,
            request.FILES,
            instance=cultura,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            cultura = form.save()
            messages.success(request, f'✅ Cultura "{cultura.nome}" atualizada!')
            return redirect('cadastros:cultura_detail', pk=cultura.pk)
    else:
        form = CulturaForm(
            instance=cultura,
            empresa=request.user.empresa,
            usuario=request.user
        )
    
    return render(request, 'cadastros/cultura/cultura_form.html', {
        'form': form,
        'cultura': cultura,
        'action': 'Editar'
    })


@login_required
def cultura_delete(request, pk):
    """Deleta cultura"""
    cultura = get_object_or_404(Cultura, pk=pk, empresa=request.user.empresa)
    
    # Verifica se tem plantios associados (implementar depois)
    # total_plantios = cultura.get_total_plantios()
    # if total_plantios > 0:
    #     messages.error(request, f'❌ Não é possível excluir! A cultura possui {total_plantios} plantio(s).')
    #     return redirect('cadastros:cultura_detail', pk=cultura.pk)
    
    if request.method == 'POST':
        nome = cultura.nome
        
        # Remove imagem se existir
        if cultura.imagem:
            cultura.imagem.delete()
        
        cultura.delete()
        messages.success(request, f'🗑️ Cultura "{nome}" excluída com sucesso!')
        return redirect('cadastros:cultura_list')
    
    return render(request, 'cadastros/cultura/cultura_confirm_delete.html', {'cultura': cultura})



@login_required
def safra_list(request):
    """Lista safras da empresa do usuário"""
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        # Em vez de redirecionar, renderiza a lista com aviso e sem safras
        context = {'safras': [], 'empresa_missing': True}
        return render(request, 'cadastros/safra/safra_list.html', context)

    safras = Safra.objects.filter(fazenda__empresa=empresa).select_related('fazenda', 'cultura')

    # Filtros
    q = request.GET.get('q', '').strip()
    fazenda_id = request.GET.get('fazenda')
    cultura_id = request.GET.get('cultura')
    ano = request.GET.get('ano')
    status = request.GET.get('status')

    if q:
        safras = safras.filter(Q(nome__icontains=q) | Q(ano__icontains=q) | Q(fazenda__nome__icontains=q))
    if fazenda_id:
        safras = safras.filter(fazenda_id=fazenda_id)
    if cultura_id:
        safras = safras.filter(cultura_id=cultura_id)
    if ano:
        safras = safras.filter(ano=ano)
    if status:
        safras = safras.filter(status=status)

    # Paginação
    paginator = Paginator(safras.order_by('-ano', 'nome'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'safras': page_obj.object_list,
        'page_obj': page_obj,
        'fazendas': Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome'),
        'culturas': Cultura.objects.filter(empresa=empresa, ativa=True).order_by('nome'),
    }
    return render(request, 'cadastros/safra/safra_list.html', context)

#=====================================
#                SAFRAS
# ===================================+

# cadastros/views.py

@login_required
def safra_create(request):
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return render(request, 'cadastros/safra/safra_form.html', {'empresa_missing': True, 'action': 'Cadastrar'})

    if request.method == 'POST':
        form = SafraForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                safra = form.save(commit=False)
                safra.cadastrado_por = request.user
                safra.save()
                talhoes_ids = request.POST.get('talhoes', '').strip()
                if talhoes_ids:
                    try:
                        talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                        talhoes = Talhao.objects.filter(
                            id__in=talhao_ids_list,
                            empresa=empresa,
                            ativo=True
                        )
                        invalidos = [t.codigo for t in talhoes if t.fazenda != safra.fazenda]
                        if invalidos:
                            messages.error(request, f'❌ Talhões não pertencem à fazenda: {", ".join(invalidos)}')
                            safra.delete()
                            return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'action': 'Cadastrar'})

                        # Valida conflitos
                        conflitos = []
                        for talhao in talhoes:
                            safras_conflito = Safra.objects.filter(
                                talhoes=talhao
                            ).exclude(
                                status='FINALIZADA'
                            ).exclude(
                                pk=safra.pk
                            )
                            if safras_conflito.exists():
                                conflitos.append(f"{talhao.codigo} (em {safras_conflito.first()})")

                        if conflitos:
                            messages.error(request, f'❌ Talhões já estão em uso: {", ".join(conflitos)}')
                            safra.delete()
                            return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'action': 'Cadastrar'})

                        # Limpa e associa
                        safra.talhoes.clear()
                        safra.talhoes.set(talhoes)

                    except ValueError as e:
                        messages.error(request, f'❌ IDs de talhões inválidos: {e}')
                        safra.delete()
                        return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'action': 'Cadastrar'})
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        messages.error(request, f'❌ Erro ao processar talhões: {e}')
                        safra.delete()
                        return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'action': 'Cadastrar'})

                total_talhoes = safra.talhoes.count()
                messages.success(request, f'✅ Safra "{safra}" cadastrada com {total_talhoes} talhão(ões)!')
                return redirect('cadastros:safra_detail', pk=safra.pk)
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Erro ao salvar: {e}')
        else:
            messages.error(request, '❌ Corrija os erros do formulário de safra')
    else:
        form = SafraForm(user=request.user)

    return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def safra_update(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    empresa = request.user.empresa

    if request.method == 'POST':
        form = SafraForm(request.POST, instance=safra, user=request.user)
        if form.is_valid():
            try:
                safra = form.save()
                talhoes_ids = request.POST.get('talhoes', '').strip()
                safra.talhoes.clear()
                if talhoes_ids:
                    try:
                        talhao_ids_list = [int(tid.strip()) for tid in talhoes_ids.split(',') if tid.strip()]
                        talhoes = Talhao.objects.filter(
                            id__in=talhao_ids_list,
                            empresa=empresa,
                            ativo=True
                        )

                        invalidos = [t.codigo for t in talhoes if t.fazenda != safra.fazenda]
                        if invalidos:
                            messages.error(request, f'❌ Talhões não pertencem à fazenda: {", ".join(invalidos)}')
                            return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'safra': safra, 'action': 'Editar'})

                        # Valida conflitos
                        conflitos = []
                        for talhao in talhoes:
                            safras_conflito = Safra.objects.filter(
                                talhoes=talhao
                            ).exclude(
                                status='FINALIZADA'
                            ).exclude(
                                pk=safra.pk
                            )
                            if safras_conflito.exists():
                                conflitos.append(f"{talhao.codigo} (em {safras_conflito.first()})")

                        if conflitos:
                            messages.error(request, f'❌ Talhões já estão em uso: {", ".join(conflitos)}')
                            return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'safra': safra, 'action': 'Editar'})

                        safra.talhoes.set(talhoes)
                    except ValueError as e:
                        messages.error(request, f'❌ IDs de talhões inválidos: {e}')
                        return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'safra': safra, 'action': 'Editar'})
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        messages.error(request, f'❌ Erro ao processar talhões: {e}')
                        return render(request, 'cadastros/safra/safra_form.html', {'form': form, 'safra': safra, 'action': 'Editar'})

                messages.success(request, f'✅ Safra "{safra}" atualizada com sucesso')
                return redirect('cadastros:safra_detail', pk=safra.pk)
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Erro ao salvar safra: {e}')
        else:
            messages.error(request, f'❌ Corrija os erros no formulário: {form.errors}')
    else:
        form = SafraForm(instance=safra, user=request.user)

    return render(request, 'cadastros/safra/safra_form.html', {
        'form': form,
        'safra': safra,
        'action': 'Editar'
    })

@login_required
def safra_detail(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    # Prepare comparativo
    context = {'safra': safra}
    return render(request, 'cadastros/safra/safra_detail.html', context)


@login_required
def safra_delete(request, pk):
    safra = get_object_or_404(Safra, pk=pk, fazenda__empresa=request.user.empresa)
    if request.method == 'POST':
        nome = str(safra)
        safra.delete()
        messages.success(request, f'🗑️ Safra "{nome}" excluída com sucesso!')
        return redirect('cadastros:safra_list')
    return render(request, 'cadastros/safra/safra_confirm_delete.html', {'safra': safra})





    """
ADICIONE ESTAS VIEWS AO ARQUIVO cadastros/views.py
Views para Áreas e Talhões com isolamento Multi-Tenant
"""




# ============================================
# VIEWS DE ÁREA
# ============================================

@login_required
def area_list(request):
    """
    Lista áreas da empresa do usuário logado
    🔒 FILTRO AUTOMÁTICO POR EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    # 🔒 Filtra apenas áreas da empresa do usuário
    # Nem sempre o manager customizado pode estar disponível (erro em alguns ambientes).
    # Usamos um fallback seguro para evitar AttributeError caso `da_empresa` não exista.
    if hasattr(Area.objects, 'da_empresa'):
        areas = Area.objects.da_empresa(empresa).select_related(
            'fazenda', 'cadastrado_por'
        ).prefetch_related('talhoes')
    else:
        areas = Area.objects.filter(empresa=empresa).select_related(
            'fazenda', 'cadastrado_por'
        ).prefetch_related('talhoes')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        areas = areas.filter(
            Q(nome__icontains=q) |
            Q(codigo_interno__icontains=q) |
            Q(fazenda__nome__icontains=q)
        )
    
    # Filtro por fazenda
    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        areas = areas.filter(fazenda_id=fazenda_id)
    
    # Filtro por tipo
    tipo = request.GET.get('tipo')
    if tipo:
        areas = areas.filter(tipo_area=tipo)
    
    # Filtro por status
    status = request.GET.get('status')
    if status:
        areas = areas.filter(status=status)
    
    # Adiciona estatísticas
    for area in areas:
        area.total_talhoes = area.talhoes.filter(ativo=True).count()
        area.area_disponivel = area.get_area_disponivel()
        area.percentual_uso = area.get_percentual_uso()
    
    # 🔒 Fazendas da empresa para filtro
    fazendas = Fazenda.objects.filter(
        empresa=empresa, 
        ativa=True
    ).order_by('nome')
    
    context = {
        'areas': areas,
        'fazendas': fazendas,
        'total_areas': areas.count(),
    }
    
    return render(request, 'cadastros/area/area_list.html', context)


@login_required
def area_create(request):
    """
    Cria nova área
    🔒 VINCULA AUTOMATICAMENTE À EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = AreaForm(request.POST, user=request.user)
        if form.is_valid():
            area = form.save(commit=False)
            area.empresa = empresa  # 🔒 Vincula à empresa
            area.cadastrado_por = request.user
            area.save()
            
            messages.success(
                request, 
                f'✅ Área "{area.nome}" cadastrada com sucesso!'
            )
            return redirect('cadastros:area_list')
    else:
        form = AreaForm(user=request.user)
    
    return render(request, 'cadastros/area/area_form.html', {
        'form': form,
        'title': 'Nova Área'
    })


@login_required
def area_update(request, pk):
    """
    Edita área existente
    🔒 VERIFICA SE PERTENCE À EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = AreaForm(request.POST, instance=area, user=request.user)
        if form.is_valid():
            area = form.save()
            messages.success(request, f'✅ Área "{area.nome}" atualizada!')
            return redirect('cadastros:area_list')
    else:
        form = AreaForm(instance=area, user=request.user)
    
    return render(request, 'cadastros/area/area_form.html', {
        'form': form,
        'area': area,
        'title': f'Editar Área: {area.nome}'
    })


@login_required
def area_delete(request, pk):
    """
    Exclui área
    🔒 VERIFICA PERMISSÃO E VALIDA EXCLUSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa),
        pk=pk
    )
    
    # Verifica se tem talhões vinculados
    total_talhoes = area.talhoes.filter(ativo=True).count()
    
    if total_talhoes > 0:
        messages.error(
            request,
            f'❌ Não é possível excluir! A área possui {total_talhoes} talhão(ões) ativo(s).'
        )
        return redirect('cadastros:area_list')
    
    if request.method == 'POST':
        nome = area.nome
        area.delete()
        messages.success(request, f'🗑️ Área "{nome}" excluída com sucesso!')
        return redirect('cadastros:area_list')
    
    return render(request, 'cadastros/area/area_confirm_delete.html', {
        'area': area
    })


@login_required
def area_detail(request, pk):
    """
    Detalhes da área com talhões
    🔒 ACESSO APENAS PARA EMPRESA DONA
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    area = get_object_or_404(
        Area.objects.da_empresa(empresa).select_related('fazenda'),
        pk=pk
    )
    
    # Talhões da área
    talhoes = area.talhoes.filter(ativo=True).select_related('cultura_atual')
    
    # Estatísticas
    stats = {
        'total_talhoes': talhoes.count(),
        'area_ocupada': talhoes.aggregate(Sum('area_hac'))['area_hac__sum'] or 0,
        'area_disponivel': area.get_area_disponivel(),
        'percentual_uso': area.get_percentual_uso(),
        'talhoes_plantados': talhoes.filter(status='PLANTADO').count(),
        'talhoes_disponiveis': talhoes.filter(status='DISPONIVEL').count(),
    }
    
    return render(request, 'cadastros/area/area_detail.html', {
        'area': area,
        'talhoes': talhoes,
        'stats': stats
    })


# ============================================
# VIEWS DE TALHÃO
# ============================================

# cadastros/views.py - Localize e SUBSTITUA a função talhao_list

@login_required
def talhao_list(request):
    """
    Lista talhões da empresa
    🔒 FILTRO AUTOMÁTICO POR EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.warning(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    # 🔒 Filtra apenas talhões da empresa
    if hasattr(Talhao.objects, 'da_empresa'):
        talhoes = Talhao.objects.da_empresa(empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        ).prefetch_related('safras')
    else:
        talhoes = Talhao.objects.filter(empresa=empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        ).prefetch_related('safras')
    
    # Busca
    q = request.GET.get('q', '').strip()
    if q:
        talhoes = talhoes.filter(
            Q(nome__icontains=q) |
            Q(codigo__icontains=q) |
            Q(fazenda__nome__icontains=q)
        )
    
    # Filtros
    fazenda_id = request.GET.get('fazenda')
    if fazenda_id:
        talhoes = talhoes.filter(fazenda_id=fazenda_id)
    
    area_id = request.GET.get('area')
    if area_id:
        talhoes = talhoes.filter(area_id=area_id)
    
    status = request.GET.get('status')
    if status:
        talhoes = talhoes.filter(status=status)
    
    # Estatísticas
    stats = {
        'total': talhoes.count(),
        'plantados': talhoes.filter(status='PLANTADO').count(),
        'disponiveis': talhoes.filter(status='DISPONIVEL').count(),
        'area_total': talhoes.aggregate(Sum('area_hac'))['area_hac__sum'] or 0,
    }
    
    # 🔥 NOVO: Adiciona informação da safra ativa para cada talhão
    talhoes_list = list(talhoes)  # Converte para lista para poder modificar
    for talhao in talhoes_list:
        # Busca safra ativa (não finalizada) associada ao talhão
        safra_ativa = talhao.safras.filter(
            status__in=['PLANEJADA', 'EM_ANDAMENTO']
        ).select_related('cultura').first()
        
        # Anexa a safra e cultura ao objeto talhão
        talhao.safra_ativa = safra_ativa
        if safra_ativa:
            talhao.cultura_safra = safra_ativa.cultura
            talhao.safra_nome = str(safra_ativa)
        else:
            talhao.cultura_safra = None
            talhao.safra_nome = None
    
    # 🔒 Dados para filtros (apenas da empresa)
    fazendas = Fazenda.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    if hasattr(Area.objects, 'da_empresa'):
        areas = Area.objects.da_empresa(empresa).filter(ativa=True).order_by('nome')
    else:
        areas = Area.objects.filter(empresa=empresa, ativa=True).order_by('nome')
    
    context = {
        'talhoes': talhoes_list,
        'fazendas': fazendas,
        'areas': areas,
        'stats': stats,
    }
    
    return render(request, 'cadastros/talhao/talhao_list.html', context)


@login_required
def talhao_create(request):
    """
    Cria novo talhão
    🔒 VINCULA AUTOMATICAMENTE À EMPRESA
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, 'Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = TalhaoForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                talhao = form.save(commit=False)
                talhao.empresa = empresa  # 🔒 Vincula à empresa
                talhao.cadastrado_por = request.user
                
                # 🔥 GARANTIA: area_hac já foi setado pelo form.save(), mas vamos garantir
                area_tamanho = form.cleaned_data.get('area_tamanho')
                if area_tamanho and not talhao.area_hac:
                    talhao.area_hac = area_tamanho
                
                talhao.save()
                
                messages.success(
                    request,
                    f'✅ Talhão "{talhao.codigo} - {talhao.nome}" cadastrado com {talhao.area_hac} ha!'
                )
                return redirect('cadastros:talhao_list')
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f'❌ Erro ao salvar talhão: {e}')
        else:
            messages.error(request, '❌ Corrija os erros no formulário')
    else:
        form = TalhaoForm(user=request.user)
    
    return render(request, 'cadastros/talhao/talhao_form.html', {
        'form': form,
        'title': 'Novo Talhão'
    })


@login_required
def talhao_update(request, pk):
    """
    Edita talhão
    🔒 VERIFICA PERMISSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = TalhaoForm(request.POST, instance=talhao, user=request.user)
        if form.is_valid():
            talhao = form.save()
            messages.success(request, f'✅ Talhão "{talhao.codigo}" atualizado!')
            return redirect('cadastros:talhao_list')
    else:
        form = TalhaoForm(instance=talhao, user=request.user)
    
    return render(request, 'cadastros/talhao/talhao_form.html', {
        'form': form,
        'talhao': talhao,
        'title': f'Editar Talhão: {talhao.codigo}'
    })

@login_required
def talhao_delete(request, pk):
    """
    Exclui talhão
    🔒 VERIFICA PERMISSÃO
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa),
        pk=pk
    )
    
    # Verifica se está em uso
    if talhao.status == 'PLANTADO':
        messages.error(
            request,
            '❌ Não é possível excluir talhão com cultivo ativo!'
        )
        return redirect('cadastros:talhao_list')
    
    if request.method == 'POST':
        codigo = talhao.codigo
        talhao.delete()
        messages.success(request, f'🗑️ Talhão "{codigo}" excluído!')
        return redirect('cadastros:talhao_list')
    
    return render(request, 'cadastros/talhao/talhao_confirm_delete.html', {
        'talhao': talhao
    })


@login_required
def talhao_detail(request, pk):
    """
    Detalhes do talhão com histórico
    🔒 ACESSO APENAS PARA EMPRESA DONA
    """
    empresa = request.user.empresa
    
    # 🔒 Busca apenas se pertencer à empresa
    talhao = get_object_or_404(
        Talhao.objects.da_empresa(empresa).select_related(
            'fazenda', 'area', 'cultura_atual'
        ),
        pk=pk
    )
    
    # Histórico de cultivos
    historico = talhao.historico.all().order_by('-data_plantio')[:10]
    
    # Estatísticas do histórico
    historico_stats = talhao.historico.aggregate(
        total_safras=Count('id'),
        producao_total=Sum('producao_real'),
        media_produtividade=Avg('produtividade')
    )
    
    return render(request, 'cadastros/talhao/talhao_detail.html', {
        'talhao': talhao,
        'historico': historico,
        'historico_stats': historico_stats
    })


@login_required
def historico_create(request, talhao_pk):
    """Cria um registro de histórico para um talhão (usuário da empresa)."""
    empresa = request.user.empresa
    talhao = get_object_or_404(Talhao.objects.da_empresa(empresa), pk=talhao_pk)

    if request.method == 'POST':
        form = HistoricoTalhaoForm(request.POST, user=request.user)
        if form.is_valid():
            hist = form.save(commit=False)
            hist.talhao = talhao
            hist.empresa = empresa
            hist.registrado_por = request.user
            hist.save()
            messages.success(request, f'✅ Histórico registrado para {talhao.nome}!')
            return redirect('cadastros:talhao_detail', pk=talhao.pk)
    else:
        form = HistoricoTalhaoForm(initial={'talhao': talhao}, user=request.user)

    return render(request, 'cadastros/talhao/historico_form.html', {
        'form': form,
        'talhao': talhao,
        'action': 'Registrar'
    })


@login_required
def historico_update(request, pk):
    """Edita um registro de histórico (pertence à mesma empresa)."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = HistoricoTalhaoForm(request.POST, instance=historico, user=request.user)
        if form.is_valid():
            hist = form.save()
            messages.success(request, '✅ Histórico atualizado!')
            return redirect('cadastros:talhao_detail', pk=hist.talhao.pk)
    else:
        form = HistoricoTalhaoForm(instance=historico, user=request.user)

    return render(request, 'cadastros/talhao/historico_form.html', {
        'form': form,
        'historico': historico,
        'action': 'Editar'
    })


@login_required
def historico_delete(request, pk):
    """Exclui um registro de histórico."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao, pk=pk, empresa=empresa)

    if request.method == 'POST':
        talhao_pk = historico.talhao.pk
        historico.delete()
        messages.success(request, '🗑️ Histórico excluído!')
        return redirect('cadastros:talhao_detail', pk=talhao_pk)

    return render(request, 'cadastros/talhao/historico_confirm_delete.html', {
        'historico': historico
    })


@login_required
def historico_detail(request, pk):
    """Mostra detalhes de um registro de histórico."""
    empresa = request.user.empresa
    historico = get_object_or_404(HistoricoTalhao.objects.select_related('talhao', 'cultura', 'registrado_por'), pk=pk, empresa=empresa)

    return render(request, 'cadastros/talhao/historico_detail.html', {
        'historico': historico
    })


# ============================================
# AJAX: ÁREAS POR FAZENDA
# ============================================

@login_required
def ajax_areas_por_fazenda(request, fazenda_id):
    """
    Retorna áreas de uma fazenda (para select dinâmico)
    🔒 APENAS ÁREAS DA EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa
    
    # 🔒 Valida se fazenda pertence à empresa
    try:
        fazenda = Fazenda.objects.get(pk=fazenda_id, empresa=empresa)
    except Fazenda.DoesNotExist:
        return JsonResponse({'error': 'Fazenda não encontrada'}, status=404)
    
    # 🔒 Busca apenas áreas da empresa
    areas = Area.objects.filter(
        fazenda=fazenda,
        empresa=empresa,
        ativa=True
    ).values('id', 'nome', 'area_total')
    
    return JsonResponse(list(areas), safe=False)


# ============================================
# AJAX: TALHÕES POR FAZENDA
# ============================================


@login_required
def ajax_talhoes_por_fazenda(request, fazenda_id):
    """
    Retorna talhões de uma fazenda (para select dinâmico)
    🔒 APENAS TALHÕES DA EMPRESA DO USUÁRIO
    """
    empresa = request.user.empresa

    # 🔒 Valida se fazenda pertence à empresa
    try:
        fazenda = Fazenda.objects.get(pk=fazenda_id, empresa=empresa)
    except Fazenda.DoesNotExist:
        return JsonResponse({'error': 'Fazenda não encontrada'}, status=404)

    talhoes = Talhao.objects.filter(
        fazenda=fazenda,
        empresa=empresa,
        ativo=True
    ).values('id', 'nome', 'codigo', 'area_hac')
    # Para cada talhão, informa se já está associado a uma safra não finalizada
    talhao_ids = [t['id'] for t in talhoes]
    safra_map = {}
    if talhao_ids:
        safras = Safra.objects.filter(talhoes__in=talhao_ids).exclude(status='FINALIZADA').select_related('fazenda')
        for s in safras:
            for t in s.talhoes.all():
                if t.id in talhao_ids and t.id not in safra_map:
                    safra_map[t.id] = str(s)

    result = []
    for t in talhoes:
        tid = t['id']
        result.append({
            'id': tid,
            'nome': t['nome'],
            'codigo': t.get('codigo'),
            'area_hac': t.get('area_hac'),
            'in_use': tid in safra_map,
            'in_use_by': safra_map.get(tid)
        })

    return JsonResponse(result, safe=False)


"""
=============================================================================
📝 VIEWS DE VENDEDOR - VERSÃO FINAL CONSOLIDADA
=============================================================================

TODAS as views de vendedor em um único arquivo, sem duplicações.
Inclui CRUD completo, ações rápidas, comissões e API JSON.

INSTRUÇÕES:
1. Abra cadastros/views.py
2. Localize TODAS as views de vendedor existentes
3. DELETE todas elas
4. Cole ESTE código no lugar
5. Salve e teste

LISTA DE VIEWS INCLUÍDAS:
- vendedor_list (listagem com filtros)
- vendedor_create (criar)
- vendedor_update (editar)
- vendedor_detail (detalhes)
- vendedor_delete (excluir)
- vendedor_inativar (inativar)
- vendedor_reativar (reativar)
- vendedor_json (API JSON)
- comissao_list (listar comissões)
- comissao_create (criar comissão)
- comissao_pagar (pagar comissão)
"""




# =============================================================================
# CRUD DE VENDEDOR
# =============================================================================

@login_required
def vendedor_list(request):
    """
    Lista vendedores da empresa com filtros e estatísticas
    GET /cadastros/vendedores/
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.debug('Entering vendedor_list')

    empresa = getattr(request.user, 'empresa', None)
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    try:
        # Formulário de filtros
        filtro_form = VendedorFiltroForm(request.GET or None)
        
        # QuerySet base
        vendedores = Vendedor.objects.filter(empresa=empresa).select_related('supervisor', 'empresa')
        
        # Aplicar filtros se o formulário for válido
        if filtro_form.is_valid():
            busca = filtro_form.cleaned_data.get('busca')
            status = filtro_form.cleaned_data.get('status')
            tipo_mercado = filtro_form.cleaned_data.get('tipo_mercado')
            
            if busca:
                vendedores = vendedores.filter(
                    Q(nome_completo__icontains=busca) |
                    Q(cpf__icontains=busca) |
                    Q(email_corporativo__icontains=busca)
                )
            
            if status:
                vendedores = vendedores.filter(status=status)
            
            if tipo_mercado:
                vendedores = vendedores.filter(tipo_mercado=tipo_mercado)
        
        # Estatísticas para o dashboard
        total_vendedores = vendedores.count()
        total_ativos = vendedores.filter(status='ATIVO').count()
        total_mercado_interno = vendedores.filter(tipo_mercado__in=['INTERNO', 'AMBOS']).count()
        total_exportacao = vendedores.filter(tipo_mercado__in=['EXTERNO', 'AMBOS']).count()

        context = {
            'vendedores': vendedores,
            'filtro_form': filtro_form,
            'total_vendedores': total_vendedores,
            'total_ativos': total_ativos,
            'total_mercado_interno': total_mercado_interno,
            'total_exportacao': total_exportacao,
        }

        logger.debug('About to render vendedor_list with %d vendedores', total_vendedores)
        return render(request, 'cadastros/vendedor/vendedor_list.html', context)
    except Exception as e:
        logger.exception('Error in vendedor_list')
        messages.error(request, 'Erro ao listar vendedores: %s' % str(e))
        return redirect('dashboard:index')


@login_required
def vendedores_por_tipo(request):
    """Retorna JSON com vendedores filtrados pelo tipo (usado em formulários de cliente)."""
    from django.http import JsonResponse
    tipo = request.GET.get('tipo', 'NACIONAL')
    empresa = getattr(request.user, 'empresa', None)

    if not empresa:
        return JsonResponse({'vendedores': []})

    if tipo == 'IMPORTADOR':
        qs = Vendedor.objects.filter(empresa=empresa, tipo_mercado__in=['EXTERNO', 'AMBOS'])
    else:
        qs = Vendedor.objects.filter(empresa=empresa, tipo_mercado__in=['INTERNO', 'AMBOS'])

    data = [{'id': v.pk, 'nome': v.nome_completo} for v in qs.order_by('nome_completo')]
    return JsonResponse({'vendedores': data})


# =============================================================================
# CRUD DE FORNECEDORES
# =============================================================================

@login_required
def fornecedor_list(request):
    """Lista fornecedores da empresa"""
    empresa = request.user.empresa
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')

    fornecedores = Fornecedor.objects.filter(empresa=empresa).order_by('nome')

    # busca e filtros
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    tipo = request.GET.get('tipo', '').strip()

    if q:
        fornecedores = fornecedores.filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(cnpj_cpf__icontains=q)
        )

    if status:
        if status == 'ATIVO':
            fornecedores = fornecedores.filter(ativa=True)
        elif status == 'INATIVO':
            fornecedores = fornecedores.filter(ativa=False)

    if categoria:
        try:
            fornecedores = fornecedores.filter(categorias__id=int(categoria))
        except ValueError:
            pass

    if tipo:
        if tipo == 'INTERNACIONAL':
            fornecedores = fornecedores.filter(is_exportador=True)
        elif tipo == 'NACIONAL':
            fornecedores = fornecedores.filter(is_exportador=False)

    # pagination
    paginator = Paginator(fornecedores.distinct().order_by('nome'), 10)
    page = request.GET.get('page')
    try:
        fornecedores_page = paginator.get_page(page)
    except Exception:
        fornecedores_page = paginator.get_page(1)

    # categorias para o filtro
    from .models import CategoriaFornecedor
    categorias = CategoriaFornecedor.objects.filter(empresa=empresa) if empresa else CategoriaFornecedor.objects.all()

    context = {
        'fornecedores': fornecedores_page,
        'q': q,
        'status_atual': status,
        'categoria_atual': categoria,
        'tipo_atual': tipo,
        'categorias': categorias,
        'paginator': paginator,
    }
    return render(request, 'cadastros/fornecedor/fornecedor_list.html', context)


@login_required
def fornecedor_detail(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk, empresa=request.user.empresa)

    # Documentos vencidos / em alerta
    today = timezone.now().date()
    docs = fornecedor.documentos.all()
    docs_vencidos = docs.filter(data_validade__isnull=False, data_validade__lt=today).count()

    # Avaliações
    total_avaliacoes = fornecedor.avaliacoes.count() if hasattr(fornecedor, 'avaliacoes') else 0
    avaliacoes_recentes = fornecedor.avaliacoes.order_by('-data_avaliacao')[:5] if hasattr(fornecedor, 'avaliacoes') else []

    # Contas bancárias
    contas = fornecedor.contas_bancarias.all()

    context = {
        'fornecedor': fornecedor,
        'docs_vencidos': docs_vencidos,
        'total_avaliacoes': total_avaliacoes,
        'avaliacoes_recentes': avaliacoes_recentes,
        'contas': contas,
    }

    return render(request, 'cadastros/fornecedor/fornecedor_detail.html', context)


@login_required
def fornecedor_create(request):
    if request.method == 'POST':
        form = FornecedorForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            fornecedor = form.save()
            messages.success(request, f'✅ Fornecedor "{fornecedor.nome}" cadastrado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = FornecedorForm(empresa=request.user.empresa, usuario=request.user)

    return render(request, 'cadastros/fornecedor/fornecedor_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
def fornecedor_update(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = FornecedorForm(request.POST, instance=fornecedor, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            fornecedor = form.save()
            messages.success(request, f'✅ Fornecedor "{fornecedor.nome}" atualizado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    else:
        form = FornecedorForm(instance=fornecedor, empresa=request.user.empresa, usuario=request.user)

    return render(request, 'cadastros/fornecedor/fornecedor_form.html', {'form': form, 'action': 'Editar', 'fornecedor': fornecedor})


@login_required
def fornecedor_delete(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        nome = fornecedor.nome
        fornecedor.delete()
        messages.success(request, f'🗑️ Fornecedor "{nome}" excluído!')
        return redirect('cadastros:fornecedor_list')
    return render(request, 'cadastros/fornecedor/fornecedor_confirm_delete.html', {'fornecedor': fornecedor})


# ==================== ENDEREÇOS DO FORNECEDOR ====================


# ==================== CLIENTES ====================

@login_required
def cliente_list(request):
    """Lista de clientes com filtros, paginação e visão em cards (semelhante a fornecedor_list)."""
    # Verifica empresa do usuário
    empresa = request.user.empresa
    if not empresa:
        messages.warning(request, '⚠️ Seu usuário não está vinculado a nenhuma empresa. Entre em contato com o administrador.')
        return redirect('dashboard:index')

    # Filtros de busca
    q = request.GET.get('q', '').strip()
    status_atual = request.GET.get('status', 'ATIVO')  # por padrão mostra apenas clientes ATIVO
    tipo_atual = request.GET.get('tipo', '')
    vendedor_atual = request.GET.get('vendedor', '')
    page = request.GET.get('page', 1)

    clientes_qs = Cliente.objects.filter(empresa=empresa)

    if q:
        clientes_qs = clientes_qs.filter(
            Q(razao_social__icontains=q) | Q(nome_comercial__icontains=q) | Q(cnpj_cpf__icontains=q)
        )

    if status_atual:
        clientes_qs = clientes_qs.filter(status=status_atual)

    if tipo_atual:
        clientes_qs = clientes_qs.filter(tipo_cliente=tipo_atual)

    if vendedor_atual:
        clientes_qs = clientes_qs.filter(vendedor_responsavel_id=vendedor_atual)

    clientes_qs = clientes_qs.order_by('razao_social')

    # Paginação
    paginator = Paginator(clientes_qs, 10)
    try:
        clientes = paginator.page(page)
    except Exception:
        clientes = paginator.page(1)

    # Lista de vendedores para filtro
    vendedores = Vendedor.objects.filter(empresa=empresa)

    context = {
        'clientes': clientes,
        'q': q,
        'status_atual': status_atual,
        'tipo_atual': tipo_atual,
        'vendedores': vendedores,
        'vendedor_atual': vendedor_atual,
    }

    return render(request, 'cadastros/cliente/cliente_list.html', context)


@login_required
def cliente_detail(request, pk):
    cliente = get_object_or_404(
        Cliente.objects.prefetch_related('enderecos','contatos','contas_bancarias','documentos'),
        pk=pk,
        empresa=request.user.empresa
    )
    # Documentos que precisam de atenção
    docs_vencidos = cliente.documentos.filter(
        data_validade__lt=timezone.now().date(),
        gerar_alerta_vencimento=True
    )

    docs_vencendo = []
    for doc in cliente.documentos.filter(gerar_alerta_vencimento=True):
        try:
            if doc.precisa_alerta():
                docs_vencendo.append(doc)
        except AttributeError:
            # Fallback for models missing method: calculate directly
            if doc.data_validade and doc.gerar_alerta_vencimento:
                dias_restantes = (doc.data_validade - timezone.now().date()).days
                if 0 <= dias_restantes <= (doc.dias_antecedencia_alerta or 0):
                    docs_vencendo.append(doc)

    enderecos = cliente.enderecos.all()
    contatos = cliente.contatos.all()
    contas = cliente.contas_bancarias.all()
    documentos = cliente.documentos.all()
    context = {
        'cliente': cliente,
        'docs_vencidos': docs_vencidos,
        'docs_vencendo': docs_vencendo,
        'enderecos': enderecos,
        'contatos': contatos,
        'contas': contas,
        'documentos': documentos,
    }
    return render(request, 'cadastros/cliente/cliente_detail.html', context)


@login_required
def cliente_create(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = request.user.empresa
            cliente.cadastrado_por = request.user
            cliente.save()
            messages.success(request, f'✅ Cliente "{cliente.razao_social}" cadastrado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            # If AJAX, return structured JSON errors so client can display specific alerts
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept',''):
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ClienteForm(empresa=request.user.empresa, usuario=request.user)
    # Also pass presets for template convenience
    from .models import PrazoPagamentoPadrao, Moeda
    presets = PrazoPagamentoPadrao.objects.filter(empresa=request.user.empresa, ativo=True)
    moedas = Moeda.objects.all()
    # determine selected moeda from POST, initial or instance
    selected_moeda = ''
    if request.method == 'POST':
        selected_moeda = request.POST.get('moeda_padrao','')
    else:
        selected_moeda = form.initial.get('moeda_padrao') or getattr(form.instance, 'moeda_padrao', '')

    # determine selected prazo preset from POST, initial or instance
    selected_preset = ''
    if request.method == 'POST':
        selected_preset = str(request.POST.get('prazo_pagamento_padrao','') or '')
    else:
        selected_preset = str(form.initial.get('prazo_pagamento_padrao') or getattr(form.instance, 'prazo_pagamento_padrao_id', '') or '')

    moedas_exist = moedas.exists()
    return render(request, 'cadastros/cliente/cliente_form.html', {'form': form, 'action': 'Cadastrar', 'presets': presets, 'moedas_exist': moedas_exist, 'moedas': moedas, 'selected_moeda': selected_moeda, 'selected_preset': selected_preset})


@login_required
def moeda_create_ajax(request):
    """Cria uma Moeda via AJAX (POST) e retorna JSON.
    Permite adicionar moedas diretamente do formulário de cliente.
    """
    from django.http import JsonResponse
    from .models import Moeda

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    codigo = (request.POST.get('codigo') or '').strip().upper()
    nome = (request.POST.get('nome') or '').strip()

    if not codigo or not nome:
        return JsonResponse({'success': False, 'error': 'Código e nome são obrigatórios'}, status=400)

    # Evitar duplicados
    moeda, created = Moeda.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
    if not created:
        return JsonResponse({'success': False, 'error': 'Moeda já existe'}, status=409)

    return JsonResponse({'success': True, 'moeda': {'codigo': moeda.codigo, 'nome': moeda.nome}})


@login_required
def cliente_update(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = request.user.empresa
            cliente.save()
            messages.success(request, f'✅ Cliente "{cliente.razao_social}" atualizado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept',''):
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ClienteForm(instance=cliente, empresa=request.user.empresa, usuario=request.user)
    # Also pass presets for template convenience
    from .models import PrazoPagamentoPadrao, Moeda
    presets = PrazoPagamentoPadrao.objects.filter(empresa=request.user.empresa, ativo=True)
    moedas = Moeda.objects.all()
    # determine selected moeda from POST, initial or instance
    selected_moeda = ''
    if request.method == 'POST':
        selected_moeda = request.POST.get('moeda_padrao','')
    else:
        selected_moeda = form.initial.get('moeda_padrao') or getattr(form.instance, 'moeda_padrao', '')

    # determine selected prazo preset from POST, initial or instance
    selected_preset = ''
    if request.method == 'POST':
        selected_preset = str(request.POST.get('prazo_pagamento_padrao','') or '')
    else:
        selected_preset = str(form.initial.get('prazo_pagamento_padrao') or getattr(form.instance, 'prazo_pagamento_padrao_id', '') or '')

    moedas_exist = moedas.exists()
    return render(request, 'cadastros/cliente/cliente_form.html', {'form': form, 'action': 'Editar', 'cliente': cliente, 'presets': presets, 'moedas_exist': moedas_exist, 'moedas': moedas, 'selected_moeda': selected_moeda, 'selected_preset': selected_preset})


@login_required
def cliente_delete(request, pk):
    """Desativa o cliente ao invés de excluir para preservar histórico."""
    cliente = get_object_or_404(Cliente, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        nome = cliente.razao_social
        cliente.status = 'INATIVO'
        cliente.save()
        messages.success(request, f'🗑️ Cliente "{nome}" desativado (status INATIVO)')
        return redirect('cadastros:cliente_list')
    return render(request, 'cadastros/cliente/cliente_confirm_delete.html', {'cliente': cliente})


@login_required
def cliente_activate(request, pk):
    """Reativa um cliente inativo (rota POST)."""
    cliente = get_object_or_404(Cliente, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        cliente.status = 'ATIVO'
        cliente.save()
        messages.success(request, f'✅ Cliente "{cliente.razao_social}" reativado!')
        return redirect('cadastros:cliente_detail', pk=cliente.pk)
    return render(request, 'cadastros/cliente/cliente_confirm_activate.html', {'cliente': cliente})


# ==================== ENDEREÇOS DO CLIENTE ====================

@login_required
def cliente_endereco_create(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        # If cliente is IMPORTADOR, ensure UF is present as 'EX' before validation
        post_data = request.POST
        try:
            # Make a mutable copy so we can inject ViaCEP results
            post_data = request.POST.copy()
            # If UF is missing but CEP present, try to lookup via ViaCEP and prefill fields
            cep_raw = post_data.get('cep', '')
            if cep_raw and not post_data.get('uf'):
                try:
                    import requests
                    cep_digits = re.sub(r'\D', '', cep_raw)
                    resp = requests.get(f'https://viacep.com.br/ws/{cep_digits}/json/', timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data:
                            if data.get('uf'):
                                post_data['uf'] = data.get('uf').upper()
                            if data.get('logradouro') and not post_data.get('logradouro'):
                                post_data['logradouro'] = data.get('logradouro')
                            if data.get('bairro') and not post_data.get('bairro'):
                                post_data['bairro'] = data.get('bairro')
                            if (data.get('localidade') or data.get('cidade')) and not post_data.get('cidade'):
                                post_data['cidade'] = data.get('localidade') or data.get('cidade')
                            if data.get('cep') and not post_data.get('cep'):
                                post_data['cep'] = data.get('cep')
                except Exception:
                    # Ignore network issues and proceed with original POST
                    pass
            # If cliente is IMPORTADOR, force UF to EX
            if getattr(cliente, 'tipo_cliente', '') == 'IMPORTADOR':
                post_data['uf'] = 'EX'
        except Exception:
            post_data = request.POST
        form = EnderecoClienteForm(post_data)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.cliente = cliente
            # Server-side safeguard: force UF = 'EX' if cliente is IMPORTADOR
            try:
                if getattr(cliente, 'tipo_cliente', '') == 'IMPORTADOR':
                    endereco.uf = 'EX'
            except Exception:
                pass
            endereco.save()
            messages.success(request, '✅ Endereço adicionado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = EnderecoClienteForm()
    return render(request, 'cadastros/endereco/endereco_form.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'})


@login_required
def cliente_endereco_update(request, cliente_pk, endereco_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoCliente, pk=endereco_pk, cliente=cliente)
    if request.method == 'POST':
        post_data = request.POST
        try:
            post_data = request.POST.copy()
            # If UF is missing but CEP present, try to lookup via ViaCEP and prefill fields
            cep_raw = post_data.get('cep', '')
            if cep_raw and not post_data.get('uf'):
                try:
                    import requests
                    cep_digits = re.sub(r'\D', '', cep_raw)
                    resp = requests.get(f'https://viacep.com.br/ws/{cep_digits}/json/', timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data:
                            if data.get('uf'):
                                post_data['uf'] = data.get('uf').upper()
                            if data.get('logradouro') and not post_data.get('logradouro'):
                                post_data['logradouro'] = data.get('logradouro')
                            if data.get('bairro') and not post_data.get('bairro'):
                                post_data['bairro'] = data.get('bairro')
                            if (data.get('localidade') or data.get('cidade')) and not post_data.get('cidade'):
                                post_data['cidade'] = data.get('localidade') or data.get('cidade')
                            if data.get('cep') and not post_data.get('cep'):
                                post_data['cep'] = data.get('cep')
                except Exception:
                    pass
            if getattr(cliente, 'tipo_cliente', '') == 'IMPORTADOR':
                post_data['uf'] = 'EX'
        except Exception:
            post_data = request.POST
        form = EnderecoClienteForm(post_data, instance=endereco)
        if form.is_valid():
            endereco = form.save(commit=False)
            try:
                if getattr(cliente, 'tipo_cliente', '') == 'IMPORTADOR':
                    endereco.uf = 'EX'
            except Exception:
                pass
            endereco.save()
            messages.success(request, '✅ Endereço atualizado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = EnderecoClienteForm(instance=endereco)
    debug_form = request.GET.get('debug_form') == '1'
    return render(request, 'cadastros/endereco/endereco_form.html', {'form': form, 'cliente': cliente, 'endereco': endereco, 'action': 'Editar', 'debug_form': debug_form})


@login_required
def cliente_endereco_delete(request, cliente_pk, endereco_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(EnderecoCliente, pk=endereco_pk, cliente=cliente)
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, '🗑️ Endereço removido!')
        return redirect('cadastros:cliente_detail', pk=cliente.pk)
    return render(request, 'cadastros/endereco/endereco_confirm_delete.html', {'cliente': cliente, 'endereco': endereco})


# ==================== CONTATOS DO CLIENTE ====================

@login_required
def cliente_contato_create(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ContatoClienteForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.cliente = cliente
            contato.save()
            messages.success(request, '✅ Contato adicionado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContatoClienteForm()
    return render(request, 'cadastros/contato/contato_form.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'})


@login_required
def cliente_contato_create_ajax(request, cliente_pk):
    """AJAX endpoint to render and submit contato form inside a modal"""
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    from django.template.loader import render_to_string

    if request.method == 'GET':
        form = ContatoClienteForm()
        html = render_to_string('cadastros/partials/contato_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
        return JsonResponse({'form_html': html})

    elif request.method == 'POST':
        form = ContatoClienteForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.cliente = cliente
            contato.save()
            item_html = render_to_string('cadastros/partials/contato_row.html', {'c': contato}, request=request)
            return JsonResponse({'success': True, 'item_html': item_html})
        else:
            html = render_to_string('cadastros/partials/contato_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
            return JsonResponse({'success': False, 'form_html': html}, status=400)


@login_required
def cliente_contato_update(request, cliente_pk, contato_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoCliente, pk=contato_pk, cliente=cliente)
    if request.method == 'POST':
        form = ContatoClienteForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Contato atualizado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContatoClienteForm(instance=contato)
    return render(request, 'cadastros/contato/contato_form.html', {'form': form, 'cliente': cliente, 'contato': contato, 'action': 'Editar'})


@login_required
def cliente_contato_delete(request, cliente_pk, contato_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    contato = get_object_or_404(ContatoCliente, pk=contato_pk, cliente=cliente)
    if request.method == 'POST':
        contato.delete()
        messages.success(request, '🗑️ Contato removido!')
        return redirect('cadastros:cliente_detail', pk=cliente.pk)
    return render(request, 'cadastros/contato/contato_confirm_delete.html', {'cliente': cliente, 'contato': contato})


# ==================== CONTAS BANCÁRIAS DO CLIENTE ====================

@login_required
def cliente_conta_create(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ContaBancariaClienteForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.cliente = cliente
            conta.save()
            messages.success(request, '✅ Conta bancária adicionada!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContaBancariaClienteForm()
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'})


@login_required
def cliente_conta_create_ajax(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    from django.template.loader import render_to_string

    if request.method == 'GET':
        form = ContaBancariaClienteForm()
        html = render_to_string('cadastros/partials/conta_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
        return JsonResponse({'form_html': html})

    elif request.method == 'POST':
        form = ContaBancariaClienteForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.cliente = cliente
            conta.save()
            item_html = render_to_string('cadastros/partials/conta_card.html', {'b': conta}, request=request)
            return JsonResponse({'success': True, 'item_html': item_html})
        else:
            html = render_to_string('cadastros/partials/conta_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
            return JsonResponse({'success': False, 'form_html': html}, status=400)

@login_required
def cliente_conta_update(request, cliente_pk, conta_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaCliente, pk=conta_pk, cliente=cliente)
    if request.method == 'POST':
        form = ContaBancariaClienteForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Conta bancária atualizada!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = ContaBancariaClienteForm(instance=conta)
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {'form': form, 'cliente': cliente, 'conta': conta, 'action': 'Editar'})


@login_required
def cliente_conta_delete(request, cliente_pk, conta_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaCliente, pk=conta_pk, cliente=cliente)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, '🗑️ Conta bancária removida!')
        return redirect('cadastros:cliente_detail', pk=cliente.pk)
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_confirm_delete.html', {'cliente': cliente, 'conta': conta})


@login_required
def cliente_conta_update_ajax(request, cliente_pk, conta_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaCliente, pk=conta_pk, cliente=cliente)
    from django.template.loader import render_to_string

    if request.method == 'GET':
        form = ContaBancariaClienteForm(instance=conta)
        html = render_to_string('cadastros/partials/conta_form_partial.html', {'form': form, 'cliente': cliente, 'conta': conta, 'action': 'Editar'}, request=request)
        return JsonResponse({'form_html': html})

    elif request.method == 'POST':
        form = ContaBancariaClienteForm(request.POST, instance=conta)
        if form.is_valid():
            conta = form.save()
            item_html = render_to_string('cadastros/partials/conta_card.html', {'b': conta}, request=request)
            return JsonResponse({'success': True, 'item_html': item_html, 'conta_id': conta.pk})
        else:
            html = render_to_string('cadastros/partials/conta_form_partial.html', {'form': form, 'cliente': cliente, 'conta': conta, 'action': 'Editar'}, request=request)
            return JsonResponse({'success': False, 'form_html': html}, status=400)


@login_required
def cliente_conta_delete_ajax(request, cliente_pk, conta_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    conta = get_object_or_404(ContaBancariaCliente, pk=conta_pk, cliente=cliente)
    from django.template.loader import render_to_string

    if request.method == 'GET':
        html = render_to_string('cadastros/partials/conta_confirm_delete_partial.html', {'cliente': cliente, 'conta': conta}, request=request)
        return JsonResponse({'form_html': html})

    elif request.method == 'POST':
        conta_id = conta.pk
        conta.delete()
        return JsonResponse({'success': True, 'conta_id': conta_id})


# ==================== DOCUMENTOS DO CLIENTE ====================

@login_required
def cliente_documento_create(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = DocumentoClienteForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.cliente = cliente
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, '✅ Documento anexado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = DocumentoClienteForm()
    return render(request, 'cadastros/documento/documento_form.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'})


@login_required
def cliente_documento_create_ajax(request, cliente_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    from django.template.loader import render_to_string

    if request.method == 'GET':
        form = DocumentoClienteForm()
        html = render_to_string('cadastros/partials/documento_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
        return JsonResponse({'form_html': html})

    elif request.method == 'POST':
        form = DocumentoClienteForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.cliente = cliente
            documento.enviado_por = request.user
            documento.save()
            item_html = render_to_string('cadastros/partials/documento_card.html', {'d': documento}, request=request)
            return JsonResponse({'success': True, 'item_html': item_html})
        else:
            html = render_to_string('cadastros/partials/documento_form_partial.html', {'form': form, 'cliente': cliente, 'action': 'Adicionar'}, request=request)
            return JsonResponse({'success': False, 'form_html': html}, status=400)

@login_required
def cliente_documento_update(request, cliente_pk, documento_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoCliente, pk=documento_pk, cliente=cliente)
    if request.method == 'POST':
        form = DocumentoClienteForm(request.POST, request.FILES, instance=documento)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Documento atualizado!')
            return redirect('cadastros:cliente_detail', pk=cliente.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = DocumentoClienteForm(instance=documento)
    return render(request, 'cadastros/documento/documento_form.html', {'form': form, 'cliente': cliente, 'documento': documento, 'action': 'Editar'})


@login_required
def cliente_documento_delete(request, cliente_pk, documento_pk):
    cliente = get_object_or_404(Cliente, pk=cliente_pk, empresa=request.user.empresa)
    documento = get_object_or_404(DocumentoCliente, pk=documento_pk, cliente=cliente)
    if request.method == 'POST':
        documento.delete()
        messages.success(request, '🗑️ Documento removido!')
        return redirect('cadastros:cliente_detail', pk=cliente.pk)
    return render(request, 'cadastros/documento/documento_confirm_delete.html', {'cliente': cliente, 'documento': documento})


# ==================== ENDEREÇOS DO FORNECEDOR ====================

@login_required
def fornecedor_endereco_create(request, fornecedor_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = FornecedorEnderecoForm(request.POST)
        if form.is_valid():
            endereco = form.save(commit=False)
            endereco.fornecedor = fornecedor
            endereco.save()
            messages.success(request, '✅ Endereço adicionado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = FornecedorEnderecoForm()
    return render(request, 'cadastros/endereco/endereco_form.html', {'form': form, 'fornecedor': fornecedor, 'action': 'Adicionar'})


@login_required
def fornecedor_endereco_update(request, fornecedor_pk, endereco_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(FornecedorEndereco, pk=endereco_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        form = FornecedorEnderecoForm(request.POST, instance=endereco)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Endereço atualizado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = FornecedorEnderecoForm(instance=endereco)

    # Optional debug: visit URL with ?debug_form=1 to display raw form HTML for diagnostics
    debug_form = request.GET.get('debug_form') == '1'
    return render(request, 'cadastros/endereco/endereco_form.html', {'form': form, 'fornecedor': fornecedor, 'endereco': endereco, 'action': 'Editar', 'debug_form': debug_form})


@login_required
def fornecedor_endereco_delete(request, fornecedor_pk, endereco_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    endereco = get_object_or_404(FornecedorEndereco, pk=endereco_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        endereco.delete()
        messages.success(request, '🗑️ Endereço removido!')
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    return render(request, 'cadastros/endereco/endereco_confirm_delete.html', {'fornecedor': fornecedor, 'endereco': endereco})


# ==================== CONTATOS DO FORNECEDOR ====================

@login_required
def fornecedor_contato_create(request, fornecedor_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = FornecedorContatoForm(request.POST)
        if form.is_valid():
            contato = form.save(commit=False)
            contato.fornecedor = fornecedor
            contato.save()
            messages.success(request, '✅ Contato adicionado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = FornecedorContatoForm()
    return render(request, 'cadastros/contato/contato_form.html', {'form': form, 'fornecedor': fornecedor, 'action': 'Adicionar'})


@login_required
def fornecedor_contato_update(request, fornecedor_pk, contato_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    contato = get_object_or_404(FornecedorContato, pk=contato_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        form = FornecedorContatoForm(request.POST, instance=contato)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Contato atualizado!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    else:
        form = FornecedorContatoForm(instance=contato)
    return render(request, 'cadastros/contato/contato_form.html', {'form': form, 'fornecedor': fornecedor, 'contato': contato, 'action': 'Editar'})


@login_required
def fornecedor_contato_delete(request, fornecedor_pk, contato_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    contato = get_object_or_404(FornecedorContato, pk=contato_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        contato.delete()
        messages.success(request, '🗑️ Contato removido!')
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    return render(request, 'cadastros/contato/contato_confirm_delete.html', {'fornecedor': fornecedor, 'contato': contato})


# ==================== CONTAS BANCÁRIAS DO FORNECEDOR ====================

@login_required
def fornecedor_conta_create(request, fornecedor_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = FornecedorDadoBancarioForm(request.POST)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.fornecedor = fornecedor
            conta.save()
            messages.success(request, '✅ Conta bancária adicionada!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
        else:
            messages.error(request, '❌ Corrija os erros no formulário: %s' % form.errors)
    else:
        form = FornecedorDadoBancarioForm()
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {'form': form, 'fornecedor': fornecedor, 'action': 'Adicionar'})


@login_required
def fornecedor_conta_update(request, fornecedor_pk, conta_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    conta = get_object_or_404(FornecedorDadoBancario, pk=conta_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        form = FornecedorDadoBancarioForm(request.POST, instance=conta)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Conta bancária atualizada!')
            return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    else:
        form = FornecedorDadoBancarioForm(instance=conta)
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_form.html', {'form': form, 'fornecedor': fornecedor, 'conta': conta, 'action': 'Editar'})


@login_required
def fornecedor_conta_delete(request, fornecedor_pk, conta_pk):
    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_pk, empresa=request.user.empresa)
    conta = get_object_or_404(FornecedorDadoBancario, pk=conta_pk, fornecedor=fornecedor)
    if request.method == 'POST':
        conta.delete()
        messages.success(request, '🗑️ Conta bancária removida!')
        return redirect('cadastros:fornecedor_detail', pk=fornecedor.pk)
    return render(request, 'cadastros/conta_bancaria/conta_bancaria_confirm_delete.html', {'fornecedor': fornecedor, 'conta': conta})


@login_required
def vendedor_create(request):
    """
    Cria novo vendedor
    GET/POST /cadastros/vendedores/novo/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = VendedorForm(
            request.POST, 
            request.FILES, 
            usuario=request.user,  # ✅ Parâmetro correto
            empresa=empresa
        )
        if form.is_valid():
            vendedor = form.save()
            messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' cadastrado com sucesso!")
            return redirect('cadastros:vendedor_list')
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = VendedorForm(
            usuario=request.user,  # ✅ Parâmetro correto
            empresa=empresa
        )
    
    context = {
        'form': form,
        'action': 'Criar',
        'title': 'Novo Vendedor'
    }
    
    return render(request, 'cadastros/vendedor/vendedor_form.html', context)


@login_required
def vendedor_update(request, pk):
    """
    Edita vendedor existente
    GET/POST /cadastros/vendedores/<pk>/editar/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = VendedorForm(
            request.POST, 
            request.FILES, 
            instance=vendedor, 
            usuario=request.user,  # ✅ Parâmetro correto
            empresa=empresa
        )
        if form.is_valid():
            vendedor = form.save()
            messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' atualizado com sucesso!")
            return redirect('cadastros:vendedor_list')
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = VendedorForm(
            instance=vendedor, 
            usuario=request.user,  # ✅ Parâmetro correto
            empresa=empresa
        )
    
    context = {
        'form': form,
        'vendedor': vendedor,
        'action': 'Editar',
        'title': f'Editar: {vendedor.nome_completo}'
    }
    
    return render(request, 'cadastros/vendedor/vendedor_form.html', context)


@login_required
def vendedor_detail(request, pk):
    """
    Exibe detalhes completos do vendedor
    GET /cadastros/vendedores/<pk>/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(
        Vendedor.objects.select_related('supervisor', 'empresa'), 
        pk=pk, 
        empresa=empresa
    )
    
    # Busca subordinados (se for gerente)
    subordinados = []
    if hasattr(vendedor, 'subordinados'):
        subordinados = vendedor.subordinados.filter(status='ATIVO')
    
    # Calcula totais de comissões
    comissoes_pendentes = vendedor.comissoes.filter(status='PENDENTE').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    comissoes_pagas = vendedor.comissoes.filter(status='PAGA').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    # Últimas 5 comissões
    ultimas_comissoes = vendedor.comissoes.all().order_by('-referencia_mes')[:5]
    
    context = {
        'vendedor': vendedor,
        'subordinados': subordinados,
        'comissoes_pendentes': comissoes_pendentes,
        'comissoes_pagas': comissoes_pagas,
        'ultimas_comissoes': ultimas_comissoes,
    }
    
    return render(request, 'cadastros/vendedor/vendedor_detail.html', context)


@login_required
def vendedor_delete(request, pk):
    """
    Exclui vendedor (com validações de segurança)
    GET/POST /cadastros/vendedores/<pk>/excluir/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    # ✅ VALIDAÇÃO 1: Verifica se tem subordinados
    if hasattr(vendedor, 'subordinados') and vendedor.subordinados.exists():
        total_subordinados = vendedor.subordinados.count()
        messages.error(
            request,
            f"❌ Não é possível excluir! O vendedor '{vendedor.nome_completo}' possui "
            f"{total_subordinados} subordinado(s). Reatribua-os primeiro."
        )
        return redirect('cadastros:vendedor_list')
    
    # ✅ VALIDAÇÃO 2: Verifica comissões pendentes
    comissoes_pendentes = vendedor.comissoes.filter(status='PENDENTE').count()
    if comissoes_pendentes > 0:
        messages.error(
            request,
            f"❌ Não é possível excluir! O vendedor possui {comissoes_pendentes} "
            f"comissão(ões) pendente(s). Resolva-as primeiro."
        )
        return redirect('cadastros:vendedor_list')
    
    # Confirmação de exclusão
    if request.method == 'POST':
        nome = vendedor.nome_completo
        vendedor.delete()
        messages.success(request, f"🗑️ Vendedor '{nome}' excluído com sucesso!")
        return redirect('cadastros:vendedor_list')
    
    context = {'vendedor': vendedor}
    return render(request, 'cadastros/vendedor/vendedor_confirm_delete.html', context)


# =============================================================================
# AÇÕES RÁPIDAS
# =============================================================================

@login_required
def vendedor_inativar(request, pk):
    """
    Inativa vendedor (sem excluir do banco)
    POST /cadastros/vendedores/<pk>/inativar/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if vendedor.status == 'ATIVO':
        vendedor.status = 'INATIVO'
        vendedor.data_desligamento = timezone.now().date()
        vendedor.save()
        messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' inativado com sucesso!")
    else:
        messages.warning(request, f"⚠️ Vendedor '{vendedor.nome_completo}' já está inativo.")
    
    return redirect('cadastros:vendedor_list')


@login_required
def vendedor_reativar(request, pk):
    """
    Reativa vendedor inativo
    POST /cadastros/vendedores/<pk>/reativar/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    vendedor = get_object_or_404(Vendedor, pk=pk, empresa=empresa)
    
    if vendedor.status != 'ATIVO':
        vendedor.status = 'ATIVO'
        vendedor.data_desligamento = None
        vendedor.save()
        messages.success(request, f"✅ Vendedor '{vendedor.nome_completo}' reativado com sucesso!")
    else:
        messages.warning(request, f"⚠️ Vendedor '{vendedor.nome_completo}' já está ativo.")
    
    return redirect('cadastros:vendedor_list')


# =============================================================================
# API JSON
# =============================================================================

@login_required
def vendedor_json(request):
    """
    API JSON para listagem de vendedores
    Útil para autocomplete, select2, AJAX, etc
    
    GET /cadastros/vendedores/api/json/
    
    Parâmetros GET opcionais:
    - status: ATIVO, INATIVO, FERIAS, AFASTADO
    - tipo_mercado: INTERNO, EXTERNO, AMBOS
    
    Retorna:
    {
        "vendedores": [
            {
                "id": 1,
                "nome_completo": "João Silva",
                "email_corporativo": "joao@empresa.com",
                "tipo_mercado": "INTERNO",
                "telefone_principal": "(84) 99999-9999"
            }
        ],
        "total": 1
    }
    """
    empresa = request.user.empresa
    
    if not empresa:
        return JsonResponse({'error': 'Empresa não encontrada'}, status=400)
    
    # Filtros opcionais via GET
    status = request.GET.get('status', 'ATIVO')
    tipo_mercado = request.GET.get('tipo_mercado', '')
    
    # QuerySet base
    vendedores = Vendedor.objects.filter(empresa=empresa)
    
    # Aplica filtros
    if status:
        vendedores = vendedores.filter(status=status)
    
    if tipo_mercado:
        vendedores = vendedores.filter(tipo_mercado=tipo_mercado)
    
    # Retorna apenas campos necessários
    vendedores_data = list(vendedores.values(
        'id', 
        'nome_completo', 
        'email_corporativo', 
        'tipo_mercado',
        'telefone_principal'
    ))
    
    return JsonResponse({
        'vendedores': vendedores_data,
        'total': len(vendedores_data)
    })


# =============================================================================
# COMISSÕES
# =============================================================================

@login_required
def comissao_list(request):
    """
    Lista comissões de vendedores
    GET /cadastros/comissoes/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    comissoes = ComissaoVendedor.objects.filter(
        empresa=empresa
    ).select_related('vendedor').order_by('-referencia_mes')
    
    # Filtros opcionais
    vendedor_id = request.GET.get('vendedor')
    status = request.GET.get('status')
    
    if vendedor_id:
        comissoes = comissoes.filter(vendedor_id=vendedor_id)
    
    if status:
        comissoes = comissoes.filter(status=status)
    
    # Estatísticas
    total_pendente = comissoes.filter(status='PENDENTE').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    total_pago = comissoes.filter(status='PAGA').aggregate(
        total=Sum('valor_comissao')
    )['total'] or 0
    
    context = {
        'comissoes': comissoes,
        'total_pendente': total_pendente,
        'total_pago': total_pago,
        'vendedores': Vendedor.objects.filter(empresa=empresa, status='ATIVO'),
    }
    
    return render(request, 'cadastros/comissao/comissao_list.html', context)


@login_required
def comissao_create(request):
    """
    Cria nova comissão para vendedor
    GET/POST /cadastros/comissoes/nova/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    if request.method == 'POST':
        form = ComissaoVendedorForm(request.POST, empresa=empresa)
        if form.is_valid():
            comissao = form.save()
            messages.success(
                request, 
                f"✅ Comissão de R$ {comissao.valor_comissao:.2f} criada para "
                f"{comissao.vendedor.nome_completo}!"
            )
            return redirect('cadastros:comissao_list')
        else:
            messages.error(request, '❌ Corrija os erros no formulário.')
    else:
        form = ComissaoVendedorForm(empresa=empresa)
    
    context = {
        'form': form,
        'title': 'Nova Comissão'
    }
    
    return render(request, 'cadastros/comissao/comissao_form.html', context)


@login_required
def comissao_pagar(request, pk):
    """
    Marca comissão como paga
    POST /cadastros/comissoes/<pk>/pagar/
    """
    empresa = request.user.empresa
    
    if not empresa:
        messages.error(request, '❌ Você não está vinculado a nenhuma empresa.')
        return redirect('dashboard:index')
    
    comissao = get_object_or_404(ComissaoVendedor, pk=pk, empresa=empresa)
    
    if comissao.status == 'PENDENTE':
        comissao.status = 'PAGA'
        comissao.data_pagamento = timezone.now().date()
        comissao.save()
        messages.success(
            request, 
            f"✅ Comissão de R$ {comissao.valor_comissao:.2f} marcada como paga!"
        )
    else:
        messages.warning(request, '⚠️ Esta comissão já foi paga.')
    
    return redirect('cadastros:comissao_list')

