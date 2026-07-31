"""Views do módulo Frota: combustível, manutenção, pedágios, margem, telemetria."""
import csv
import io
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from core.pagination import paginate
from django.db.models import Sum, Count, Avg
from django.forms import inlineformset_factory
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    AbastecimentoImportForm,
    AbastecimentoVeiculoForm,
    ManutencaoVeiculoForm,
    ManutencaoItemForm,
    PedagioVeiculoForm,
    TelemetriaVeiculoForm,
    ViagemFrotaForm,
)
from .models import (
    AbastecimentoVeiculo,
    AlertaManutencao,
    ManutencaoItem,
    ManutencaoVeiculo,
    Motorista,
    PedagioVeiculo,
    TelemetriaVeiculo,
    Vehicle,
    VehicleDocument,
    VehiclePlate,
)
from cadastros.models import Viagem


# ──────────────────────────────────────────────────────────────────────────────
# COMBOBOX UNIFICADO (Select2 AJAX paginado)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def ajax_buscar_veiculos(request):
    """q vazio retorna a primeira página sem filtro; digitar busca por placa,
    marca, modelo ou descrição."""
    from django.db.models import Q
    from core.select2 import select2_response

    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    qs = Vehicle.objects.filter(empresa=empresa, ativo=True).prefetch_related('plates')
    tipos = [t for t in request.GET.get('tipo', '').split(',') if t]
    if tipos:
        qs = qs.filter(tipo__in=tipos)
    ids = [i for i in request.GET.get('ids', '').split(',') if i]
    if ids:
        qs = qs.filter(pk__in=ids)
    if q:
        qs = qs.filter(
            Q(marca__icontains=q) | Q(modelo__icontains=q) | Q(descricao__icontains=q) |
            Q(plates__placa__icontains=q)
        ).distinct()
    qs = qs.order_by('descricao', 'modelo')

    def serialize(v):
        return {'id': v.pk, 'text': str(v)}

    return select2_response(request, qs, serialize)


@login_required
def ajax_buscar_motoristas(request):
    """q vazio retorna a primeira página sem filtro; digitar busca por nome,
    CPF ou CNH."""
    from django.db.models import Q
    from core.select2 import select2_response

    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    qs = Motorista.objects.filter(empresa=empresa, ativo=True)
    transportadora_id = request.GET.get('transportadora_id')
    if transportadora_id:
        qs = qs.filter(transportadora_id=transportadora_id)
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(cpf__icontains=q) | Q(cnh__icontains=q))
    qs = qs.order_by('nome')

    def serialize(m):
        return {'id': m.pk, 'text': str(m)}

    return select2_response(request, qs, serialize)


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD DE FROTA
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def frota_dashboard(request):
    empresa = request.user.empresa
    hoje = date.today()
    limite_30 = hoje + timedelta(days=30)

    # Documentos vencendo nos próximos 30 dias
    docs_vencendo = VehicleDocument.objects.filter(
        vehicle__empresa=empresa,
        data_validade__gte=hoje,
        data_validade__lte=limite_30,
    ).select_related('vehicle').order_by('data_validade')

    # Documentos já vencidos
    docs_vencidos = VehicleDocument.objects.filter(
        vehicle__empresa=empresa,
        data_validade__lt=hoje,
    ).select_related('vehicle').order_by('data_validade')

    # Alertas de manutenção pendentes
    alertas = AlertaManutencao.objects.filter(
        empresa=empresa, status='PENDENTE'
    ).select_related('vehicle', 'manutencao_origem').order_by('data_alerta')

    # Veículos ativos
    total_veiculos = Vehicle.objects.filter(empresa=empresa, ativo=True).count()

    # Últimos abastecimentos (7 dias)
    abastecimentos_recentes = AbastecimentoVeiculo.objects.filter(
        empresa=empresa, data__gte=hoje - timedelta(days=7)
    ).select_related('vehicle', 'motorista').order_by('-data')[:10]

    # Gasto total de combustível no mês corrente
    gasto_combustivel_mes = AbastecimentoVeiculo.objects.filter(
        empresa=empresa, data__year=hoje.year, data__month=hoje.month
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    # Manutenções abertas
    manutencoes_abertas = ManutencaoVeiculo.objects.filter(
        empresa=empresa, status__in=['ABERTA', 'EM_ANDAMENTO']
    ).select_related('vehicle').count()

    return render(request, 'cadastros/frota/frota_dashboard.html', {
        'title': 'Dashboard de Frota',
        'docs_vencendo': docs_vencendo,
        'docs_vencidos': docs_vencidos,
        'alertas': alertas,
        'total_veiculos': total_veiculos,
        'abastecimentos_recentes': abastecimentos_recentes,
        'gasto_combustivel_mes': gasto_combustivel_mes,
        'manutencoes_abertas': manutencoes_abertas,
    })


# ──────────────────────────────────────────────────────────────────────────────
# ABASTECIMENTOS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def abastecimento_list(request):
    empresa = request.user.empresa
    qs = AbastecimentoVeiculo.objects.filter(empresa=empresa).select_related(
        'vehicle', 'motorista', 'fornecedor'
    )

    vehicle_id = request.GET.get('vehicle')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    tipo = request.GET.get('tipo')

    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)
    if data_inicio:
        qs = qs.filter(data__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)
    if tipo:
        qs = qs.filter(tipo_combustivel=tipo)

    total_litros = qs.aggregate(t=Sum('litros'))['t'] or 0
    total_valor = qs.aggregate(t=Sum('valor_total'))['t'] or 0

    veiculos = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao', 'modelo')

    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data', '-criado_em'))

    return render(request, 'cadastros/frota/abastecimento_list.html', {
        'title': 'Abastecimentos',
        'abastecimentos': page_obj,
        'page_obj': page_obj,
        'total_litros': total_litros,
        'total_valor': total_valor,
        'veiculos': veiculos,
        'tipo_choices': AbastecimentoVeiculo.TIPO_COMBUSTIVEL_CHOICES,
        'vehicle_selecionado': vehicle_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo_selecionado': tipo,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def abastecimento_create(request):
    if request.method == 'POST':
        form = AbastecimentoVeiculoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.criado_por = request.user
            obj.save()
            messages.success(request, 'Abastecimento registrado com sucesso.')
            return redirect('frota:abastecimento_detail', pk=obj.pk)
    else:
        form = AbastecimentoVeiculoForm(user=request.user)
    return render(request, 'cadastros/frota/abastecimento_form.html', {
        'form': form,
        'title': 'Novo Abastecimento',
    })


@login_required
def abastecimento_detail(request, pk):
    obj = get_object_or_404(AbastecimentoVeiculo, pk=pk, empresa=request.user.empresa)
    consumo = obj.consumo_calculado
    return render(request, 'cadastros/frota/abastecimento_detail.html', {
        'obj': obj,
        'consumo': consumo,
        'title': f'Abastecimento — {obj.vehicle}',
    })


@login_required
def abastecimento_update(request, pk):
    obj = get_object_or_404(AbastecimentoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = AbastecimentoVeiculoForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Abastecimento atualizado.')
            return redirect('frota:abastecimento_detail', pk=obj.pk)
    else:
        form = AbastecimentoVeiculoForm(instance=obj, user=request.user)
    return render(request, 'cadastros/frota/abastecimento_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Abastecimento',
    })


@login_required
def abastecimento_delete(request, pk):
    obj = get_object_or_404(AbastecimentoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Abastecimento excluído.')
        return redirect('frota:abastecimento_list')
    return render(request, 'cadastros/frota/abastecimento_confirm_delete.html', {'obj': obj})


@login_required
def abastecimento_gerar_conta_pagar(request, pk):
    """Gera ContaPagar para um abastecimento via POST."""
    obj = get_object_or_404(AbastecimentoVeiculo, pk=pk, empresa=request.user.empresa)
    if obj.conta_pagar:
        messages.warning(request, 'Já existe uma Conta a Pagar gerada para este abastecimento.')
        return redirect('frota:abastecimento_detail', pk=pk)
    if not obj.fornecedor:
        messages.error(request, 'Selecione um fornecedor antes de gerar a Conta a Pagar.')
        return redirect('frota:abastecimento_update', pk=pk)
    from .services_frota import criar_conta_pagar_abastecimento
    try:
        criar_conta_pagar_abastecimento(obj)
        messages.success(request, 'Conta a Pagar gerada com sucesso.')
    except Exception as e:
        messages.error(request, f'Erro ao gerar Conta a Pagar: {e}')
    return redirect('frota:abastecimento_detail', pk=pk)


# ──────────────────────────────────────────────────────────────────────────────
# ABASTECIMENTOS — AJAX & IMPORTAÇÃO
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def api_veiculo_info_abastecimento(request):
    """AJAX: retorna placa atual, tank_capacity, consumo médio e último registro."""
    vehicle_id = request.GET.get('vehicle_id')
    if not vehicle_id:
        return JsonResponse({'error': 'vehicle_id obrigatório'}, status=400)

    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id, empresa=request.user.empresa)
    except Vehicle.DoesNotExist:
        return JsonResponse({'error': 'Veículo não encontrado'}, status=404)

    placa_obj = VehiclePlate.objects.filter(vehicle=vehicle, atual=True).first()
    placa = placa_obj.placa if placa_obj else ''

    ultimo = (
        AbastecimentoVeiculo.objects
        .filter(vehicle=vehicle)
        .order_by('-data', '-criado_em')
        .first()
    )

    return JsonResponse({
        'placa': placa,
        'tank_capacity': str(vehicle.tank_capacity) if vehicle.tank_capacity else None,
        'consumo_medio': str(vehicle.consumo_medio) if vehicle.consumo_medio else None,
        'consumo_unidade': vehicle.consumo_unidade if hasattr(vehicle, 'consumo_unidade') else 'L_KM',
        'ultimo_km': str(ultimo.km_odometro) if ultimo and ultimo.km_odometro else None,
        'ultimo_horimetro': str(ultimo.horimetro) if ultimo and ultimo.horimetro else None,
        'ultimo_abastecimento': ultimo.data.strftime('%d/%m/%Y') if ultimo else None,
    })


@login_required
def abastecimento_importar(request):
    """Importação em massa de abastecimentos via CSV."""
    empresa = request.user.empresa
    resultado = None

    if request.method == 'POST':
        form = AbastecimentoImportForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.cleaned_data['arquivo']
            content = arquivo.read().decode('utf-8-sig', errors='replace')
            reader = csv.DictReader(io.StringIO(content))
            importados, erros = 0, []

            TIPO_MAP = {
                'diesel s10': 'DIESEL_S10', 'diesel s500': 'DIESEL_S500',
                'gasolina': 'GASOLINA', 'etanol': 'ETANOL', 'gnv': 'GNV', 'outro': 'OUTRO',
            }

            for i, row in enumerate(reader, start=2):
                try:
                    placa = (row.get('vehicle_placa') or row.get('placa') or '').strip().upper()
                    plate = VehiclePlate.objects.filter(
                        vehicle__empresa=empresa, placa__iexact=placa
                    ).select_related('vehicle').first()
                    if not plate:
                        erros.append(f"Linha {i}: placa '{placa}' não encontrada")
                        continue

                    tipo_raw = (row.get('tipo_combustivel') or '').strip().lower()
                    tipo = TIPO_MAP.get(tipo_raw, 'OUTRO')

                    AbastecimentoVeiculo.objects.create(
                        empresa=empresa,
                        vehicle=plate.vehicle,
                        data=row.get('data', '').strip(),
                        tipo_combustivel=tipo,
                        litros=Decimal(row.get('litros', '0').replace(',', '.')),
                        preco_por_litro=Decimal(row.get('preco_por_litro', '0').replace(',', '.')),
                        valor_total=Decimal('0'),
                        km_odometro=Decimal(row['km_odometro'].replace(',', '.')) if row.get('km_odometro', '').strip() else None,
                        tanque_cheio=(row.get('tanque_cheio', 'sim').strip().lower() in ('sim', 's', '1', 'true', 'yes')),
                        local_abastecimento=row.get('local', '').strip(),
                        criado_por=request.user,
                    )
                    importados += 1
                except (InvalidOperation, ValueError, Exception) as e:
                    erros.append(f"Linha {i}: {e}")

            resultado = {'importados': importados, 'erros': erros}
            if importados:
                messages.success(request, f'{importados} abastecimento(s) importado(s) com sucesso.')
    else:
        form = AbastecimentoImportForm()

    return render(request, 'cadastros/frota/abastecimento_importar.html', {
        'form': form,
        'title': 'Importar Abastecimentos',
        'resultado': resultado,
    })


@login_required
def abastecimento_download_modelo(request):
    """Retorna CSV modelo para importação."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_abastecimentos.csv"'
    response.write('﻿')  # BOM para Excel
    writer = csv.writer(response)
    writer.writerow(['vehicle_placa', 'data', 'tipo_combustivel', 'litros', 'preco_por_litro', 'km_odometro', 'tanque_cheio', 'local'])
    writer.writerow(['ABC-1234', '2026-01-15', 'Diesel S10', '150', '6.50', '45200', 'sim', 'Posto BR Km 45'])
    return response


# ──────────────────────────────────────────────────────────────────────────────
# MANUTENÇÕES
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def manutencao_list(request):
    empresa = request.user.empresa
    qs = ManutencaoVeiculo.objects.filter(empresa=empresa).select_related('vehicle', 'fornecedor_externo')

    vehicle_id = request.GET.get('vehicle')
    status = request.GET.get('status')
    tipo = request.GET.get('tipo')

    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)
    if status:
        qs = qs.filter(status=status)
    if tipo:
        qs = qs.filter(tipo=tipo)

    alertas_count = AlertaManutencao.objects.filter(empresa=empresa, status='PENDENTE').count()
    veiculos = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao', 'modelo')

    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data_abertura'))

    return render(request, 'cadastros/frota/manutencao_list.html', {
        'title': 'Manutenções',
        'manutencoes': page_obj,
        'page_obj': page_obj,
        'alertas_count': alertas_count,
        'veiculos': veiculos,
        'status_choices': ManutencaoVeiculo.STATUS_CHOICES,
        'tipo_choices': ManutencaoVeiculo.TIPO_CHOICES,
        'vehicle_selecionado': vehicle_id,
        'status_selecionado': status,
        'tipo_selecionado': tipo,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def manutencao_create(request):
    from .models import ManutencaoVeiculo, ManutencaoItem
    ManutencaoItemFormSet = inlineformset_factory(ManutencaoVeiculo, ManutencaoItem, form=ManutencaoItemForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = ManutencaoVeiculoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.criado_por = request.user
            obj.save()
            
            # Processar FormSet de itens
            formset = ManutencaoItemFormSet(request.POST, instance=obj, form_kwargs={'user': request.user})
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Manutenção registrada com sucesso.')
                return redirect('frota:manutencao_detail', pk=obj.pk)
            else:
                # Se formset inválido, re-renderizar com erros
                return render(request, 'cadastros/frota/manutencao_form.html', {
                    'form': form,
                    'formset': formset,
                    'title': 'Nova Manutenção',
                })
        else:
            formset = ManutencaoItemFormSet(form_kwargs={'user': request.user})
            return render(request, 'cadastros/frota/manutencao_form.html', {
                'form': form,
                'formset': formset,
                'title': 'Nova Manutenção',
            })
    else:
        form = ManutencaoVeiculoForm(user=request.user)
        formset = ManutencaoItemFormSet(form_kwargs={'user': request.user})
    
    return render(request, 'cadastros/frota/manutencao_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nova Manutenção',
    })


@login_required
def manutencao_detail(request, pk):
    from .forms import DocumentoManutencaoForm
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    item_form = ManutencaoItemForm(user=request.user)
    doc_form = DocumentoManutencaoForm()
    return render(request, 'cadastros/frota/manutencao_detail.html', {
        'obj': obj,
        'item_form': item_form,
        'doc_form': doc_form,
        'title': f'Manutenção — {obj.vehicle}',
    })


@login_required
def manutencao_documento_add(request, pk):
    from .models import DocumentoManutencao
    from .forms import DocumentoManutencaoForm
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = DocumentoManutencaoForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.manutencao = obj
            doc.enviado_por = request.user
            doc.save()
            messages.success(request, 'Documento anexado com sucesso.')
        else:
            for erros in form.errors.values():
                for erro in erros:
                    messages.error(request, erro)
    return redirect('frota:manutencao_detail', pk=pk)


@login_required
def manutencao_documento_delete(request, pk, doc_pk):
    from .models import DocumentoManutencao
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    doc = get_object_or_404(DocumentoManutencao, pk=doc_pk, manutencao=obj)
    if request.method == 'POST':
        doc.arquivo.delete(save=False)
        doc.delete()
        messages.success(request, 'Documento removido.')
    return redirect('frota:manutencao_detail', pk=pk)


@login_required
def manutencao_update(request, pk):
    from .models import ManutencaoVeiculo, ManutencaoItem
    ManutencaoItemFormSet = inlineformset_factory(ManutencaoVeiculo, ManutencaoItem, form=ManutencaoItemForm, extra=1, can_delete=True)

    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ManutencaoVeiculoForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            obj = form.save()
            
            # Processar FormSet de itens
            formset = ManutencaoItemFormSet(request.POST, instance=obj, form_kwargs={'user': request.user})
            if formset.is_valid():
                formset.save()
                messages.success(request, 'Manutenção atualizada.')
                return redirect('frota:manutencao_detail', pk=obj.pk)
            else:
                # Se formset inválido, re-renderizar com erros
                return render(request, 'cadastros/frota/manutencao_form.html', {
                    'form': form,
                    'formset': formset,
                    'obj': obj,
                    'title': 'Editar Manutenção',
                })
        else:
            formset = ManutencaoItemFormSet(instance=obj, form_kwargs={'user': request.user})
            return render(request, 'cadastros/frota/manutencao_form.html', {
                'form': form,
                'formset': formset,
                'obj': obj,
                'title': 'Editar Manutenção',
            })
    else:
        form = ManutencaoVeiculoForm(instance=obj, user=request.user)
        formset = ManutencaoItemFormSet(instance=obj, form_kwargs={'user': request.user})
    
    return render(request, 'cadastros/frota/manutencao_form.html', {
        'form': form,
        'formset': formset,
        'obj': obj,
        'title': 'Editar Manutenção',
    })


@login_required
def manutencao_delete(request, pk):
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Manutenção excluída.')
        return redirect('frota:manutencao_list')
    return render(request, 'cadastros/frota/manutencao_confirm_delete.html', {'obj': obj})


@login_required
def manutencao_item_add(request, pk):
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = ManutencaoItemForm(request.POST, user=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.manutencao = obj
            item.save()
            # Baixa automática no estoque se for oficina própria e tem lote
            if obj.eh_oficina_propria and item.lote:
                _baixar_estoque_manutencao(item, request.user)
            messages.success(request, 'Item adicionado.')
        else:
            messages.error(request, 'Erro ao adicionar item.')
    return redirect('frota:manutencao_detail', pk=pk)


def _baixar_estoque_manutencao(item, usuario):
    """Gera movimentação de saída no estoque para o item de manutenção."""
    try:
        from estoque.models import MovimentacaoEstoque
        lote = item.lote
        MovimentacaoEstoque.objects.create(
            empresa=lote.empresa,
            lote=lote,
            produto=lote.produto,
            armazem_origem=lote.armazem,
            tipo='SAIDA',
            quantidade=item.quantidade,
            unidade_medida=lote.produto.unidade_medida if hasattr(lote.produto, 'unidade_medida') else None,
            numero=f'MAN-ITEM-{item.pk}',
            descricao=f'Baixa automática — Manutenção #{item.manutencao.pk}: {item.descricao}',
            criado_por=usuario,
        )
    except Exception:
        pass  # Falha silenciosa — não bloqueia o registro da manutenção


@login_required
def manutencao_item_delete(request, pk, item_pk):
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    item = get_object_or_404(ManutencaoItem, pk=item_pk, manutencao=obj)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item removido.')
    return redirect('frota:manutencao_detail', pk=pk)


@login_required
def manutencao_gerar_conta_pagar(request, pk):
    obj = get_object_or_404(ManutencaoVeiculo, pk=pk, empresa=request.user.empresa)
    if obj.conta_pagar:
        messages.warning(request, 'Já existe uma Conta a Pagar para esta manutenção.')
        return redirect('frota:manutencao_detail', pk=pk)
    if not obj.fornecedor_externo:
        messages.error(request, 'Informe o fornecedor externo para gerar a Conta a Pagar.')
        return redirect('frota:manutencao_update', pk=pk)
    from .services_frota import criar_conta_pagar_manutencao
    try:
        criar_conta_pagar_manutencao(obj)
        messages.success(request, 'Conta a Pagar gerada com sucesso.')
    except Exception as e:
        messages.error(request, f'Erro: {e}')
    return redirect('frota:manutencao_detail', pk=pk)


@login_required
def alertas_manutencao_list(request):
    empresa = request.user.empresa
    alertas = AlertaManutencao.objects.filter(empresa=empresa).select_related(
        'vehicle', 'manutencao_origem'
    ).order_by('status', '-data_alerta')
    return render(request, 'cadastros/frota/alertas_manutencao.html', {
        'title': 'Alertas de Manutenção',
        'alertas': alertas,
    })


@login_required
def alerta_resolver(request, pk):
    alerta = get_object_or_404(AlertaManutencao, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        alerta.status = 'RESOLVIDO'
        alerta.save(update_fields=['status'])
        messages.success(request, 'Alerta marcado como resolvido.')
    return redirect('frota:alertas_manutencao_list')


@login_required
def get_lote_produto_data(request):
    """Endpoint AJAX para buscar dados do produto via lote ou placa via vehicle_id."""
    from estoque.models import Lote
    from .models import Vehicle

    vehicle_id = request.GET.get('vehicle_id')
    if vehicle_id:
        try:
            vehicle = Vehicle.objects.get(pk=vehicle_id, empresa=request.user.empresa)
            placa = vehicle.get_current_plate()
            if not placa:
                # Fallback: placa mais recente caso nenhuma esteja marcada como atual
                latest = vehicle.plates.order_by('-vigencia_inicio').first()
                placa = latest.placa if latest else ''
            return JsonResponse({'placa': placa or ''})
        except Vehicle.DoesNotExist:
            return JsonResponse({'placa': ''})

    lote_id = request.GET.get('lote_id')
    if not lote_id:
        return JsonResponse({'error': 'Parâmetro inválido'}, status=400)

    try:
        lote = Lote.objects.select_related('produto', 'unidade_medida').get(
            id=lote_id,
            empresa=request.user.empresa
        )
        return JsonResponse({
            'nome_produto': lote.produto.nome,
            'unidade_medida': lote.unidade_medida.sigla if lote.unidade_medida else '',
            'valor_custo': float(lote.produto.preco_custo or 0),
            'quantidade_disponivel': float(lote.quantidade_atual or 0),
        })
    except Lote.DoesNotExist:
        return JsonResponse({'error': 'Lote não encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def produto_busca(request):
    """Endpoint AJAX para busca de produtos por nome (retorna do cadastro de produtos)."""
    from produtos.models import Produto
    from estoque.models import Lote

    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    produtos = (
        Produto.objects
        .filter(ativo=True, categoria__empresa=empresa, nome__icontains=q)
        .select_related('unidade_medida')
        .order_by('nome')[:20]
    )
    # Carrega lotes disponíveis para preencher lote_id quando houver estoque
    lotes_por_produto = {}
    produto_ids = [p.pk for p in produtos]
    for lote in Lote.objects.filter(empresa=empresa, produto_id__in=produto_ids, quantidade_atual__gt=0).select_related('unidade_medida'):
        if lote.produto_id not in lotes_por_produto:
            lotes_por_produto[lote.produto_id] = lote

    results = []
    for produto in produtos:
        lote = lotes_por_produto.get(produto.pk)
        unidade = lote.unidade_medida.sigla if lote and lote.unidade_medida else (produto.unidade_medida.sigla if produto.unidade_medida else '')
        results.append({
            'nome': produto.nome,
            'lote_id': lote.pk if lote else '',
            'unidade_medida': unidade,
            'valor_custo': float(produto.preco_custo or 0),
            'quantidade_disponivel': float(lote.quantidade_atual or 0) if lote else 0,
        })
    return JsonResponse({'results': results})


# ──────────────────────────────────────────────────────────────────────────────
# PEDÁGIOS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def pedagio_list(request):
    empresa = request.user.empresa
    qs = PedagioVeiculo.objects.filter(empresa=empresa).select_related('vehicle', 'viagem', 'motorista')

    vehicle_id = request.GET.get('vehicle')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)
    if data_inicio:
        qs = qs.filter(data__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)

    total_valor = qs.aggregate(t=Sum('valor'))['t'] or 0
    veiculos = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao', 'modelo')

    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data', '-criado_em'))

    return render(request, 'cadastros/frota/pedagio_list.html', {
        'title': 'Pedágios',
        'pedagios': page_obj,
        'page_obj': page_obj,
        'total_valor': total_valor,
        'veiculos': veiculos,
        'vehicle_selecionado': vehicle_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def pedagio_create(request):
    if request.method == 'POST':
        form = PedagioVeiculoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.criado_por = request.user
            obj.save()
            messages.success(request, 'Pedágio registrado.')
            return redirect('frota:pedagio_list')
    else:
        form = PedagioVeiculoForm(user=request.user)
    return render(request, 'cadastros/frota/pedagio_form.html', {
        'form': form,
        'title': 'Registrar Pedágio',
    })


@login_required
def pedagio_update(request, pk):
    obj = get_object_or_404(PedagioVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = PedagioVeiculoForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Pedágio atualizado.')
            return redirect('frota:pedagio_list')
    else:
        form = PedagioVeiculoForm(instance=obj, user=request.user)
    return render(request, 'cadastros/frota/pedagio_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Pedágio',
    })


@login_required
def pedagio_delete(request, pk):
    obj = get_object_or_404(PedagioVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Pedágio excluído.')
        return redirect('frota:pedagio_list')
    return render(request, 'cadastros/frota/pedagio_confirm_delete.html', {'obj': obj})


# ──────────────────────────────────────────────────────────────────────────────
# VIAGENS (frota)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def viagem_list(request):
    empresa = request.user.empresa
    qs = Viagem.objects.filter(transportadora__empresa=empresa).select_related(
        'transportadora', 'vehicle', 'motorista'
    )

    status = request.GET.get('status')
    if status:
        qs = qs.filter(status=status)

    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data'))

    return render(request, 'cadastros/frota/viagem_list.html', {
        'title': 'Viagens',
        'viagens': page_obj,
        'page_obj': page_obj,
        'status_choices': Viagem.STATUS_CHOICES,
        'status_selecionado': status,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def viagem_create(request):
    if request.method == 'POST':
        form = ViagemFrotaForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save()
            messages.success(request, 'Viagem criada com sucesso.')
            return redirect('frota:viagem_frota_detail', pk=obj.pk)
    else:
        form = ViagemFrotaForm(user=request.user)
    return render(request, 'cadastros/frota/viagem_form.html', {
        'form': form,
        'title': 'Nova Viagem',
    })


@login_required
def viagem_detail(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(Viagem, pk=pk, transportadora__empresa=empresa)
    pedagios = PedagioVeiculo.objects.filter(viagem=obj)

    from .services_frota import calcular_margem_viagem
    margem = calcular_margem_viagem(obj)

    return render(request, 'cadastros/frota/viagem_detail.html', {
        'obj': obj,
        'pedagios': pedagios,
        'margem': margem,
        'title': f'Viagem — {obj.origem} → {obj.destino}',
    })


@login_required
def viagem_update(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(Viagem, pk=pk, transportadora__empresa=empresa)
    if request.method == 'POST':
        form = ViagemFrotaForm(request.POST, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Viagem atualizada.')
            return redirect('frota:viagem_frota_detail', pk=obj.pk)
    else:
        form = ViagemFrotaForm(instance=obj, user=request.user)
    return render(request, 'cadastros/frota/viagem_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Viagem',
    })


@login_required
def viagem_delete(request, pk):
    empresa = request.user.empresa
    obj = get_object_or_404(Viagem, pk=pk, transportadora__empresa=empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Viagem excluída.')
        return redirect('frota:viagem_list')
    return render(request, 'cadastros/frota/viagem_confirm_delete.html', {'obj': obj})


# ──────────────────────────────────────────────────────────────────────────────
# TELEMETRIA
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def telemetria_list(request):
    empresa = request.user.empresa
    qs = TelemetriaVeiculo.objects.filter(empresa=empresa).select_related('vehicle', 'motorista', 'viagem')

    vehicle_id = request.GET.get('vehicle')
    if vehicle_id:
        qs = qs.filter(vehicle_id=vehicle_id)

    veiculos = Vehicle.objects.filter(empresa=empresa, ativo=True).order_by('descricao', 'modelo')

    page_obj, per_page, per_page_options = paginate(request, qs.order_by('-data_hora'))

    return render(request, 'cadastros/frota/telemetria_list.html', {
        'title': 'Telemetria',
        'registros': page_obj,
        'page_obj': page_obj,
        'veiculos': veiculos,
        'vehicle_selecionado': vehicle_id,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def telemetria_create(request):
    if request.method == 'POST':
        form = TelemetriaVeiculoForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.save()
            messages.success(request, 'Registro de telemetria salvo.')
            return redirect('frota:telemetria_list')
    else:
        form = TelemetriaVeiculoForm(user=request.user)
    return render(request, 'cadastros/frota/telemetria_form.html', {
        'form': form,
        'title': 'Novo Registro de Telemetria',
    })


@login_required
def telemetria_mapa(request, vehicle_pk):
    """Exibe mapa Leaflet com os últimos pontos de telemetria de um veículo."""
    empresa = request.user.empresa
    vehicle = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=empresa)
    pontos = TelemetriaVeiculo.objects.filter(
        vehicle=vehicle,
        latitude__isnull=False,
        longitude__isnull=False,
    ).order_by('-data_hora')[:100]

    pontos_json = [
        {
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'label': f"{p.data_hora.strftime('%d/%m %H:%M')} — {p.local_descricao or vehicle.descricao}",
        }
        for p in pontos
    ]

    import json
    return render(request, 'cadastros/frota/telemetria_mapa.html', {
        'vehicle': vehicle,
        'pontos_json': json.dumps(pontos_json),
        'title': f'Mapa — {vehicle}',
    })


@login_required
def telemetria_delete(request, pk):
    obj = get_object_or_404(TelemetriaVeiculo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Registro excluído.')
        return redirect('frota:telemetria_list')
    return render(request, 'cadastros/frota/telemetria_confirm_delete.html', {'obj': obj})


# ──────────────────────────────────────────────────────────────────────────────
# API GPS (endpoint preparado para integração futura)
# ──────────────────────────────────────────────────────────────────────────────

def api_telemetria_ingest(request):
    """Endpoint para receber dados de GPS automaticamente (POST JSON)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    import json
    from django.views.decorators.csrf import csrf_exempt
    try:
        data = json.loads(request.body)
        vehicle_id = data.get('vehicle_id')
        lat = data.get('latitude')
        lng = data.get('longitude')
        speed = data.get('speed_kmh')
        odometer = data.get('odometer_km')

        vehicle = Vehicle.objects.filter(pk=vehicle_id).first()
        if not vehicle:
            return JsonResponse({'error': 'vehicle not found'}, status=404)

        from django.utils import timezone
        TelemetriaVeiculo.objects.create(
            empresa=vehicle.empresa,
            vehicle=vehicle,
            data_hora=timezone.now(),
            latitude=lat,
            longitude=lng,
            velocidade_kmh=speed,
            km_odometro=odometer,
            fonte='GPS',
        )
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
