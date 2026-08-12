"""
Views para o módulo de Ordens de Serviço Agrícolas
RF-105: Ordens de serviço — plantio, irrigação, aplicação, colheita
RF-115: Controle de custos por talhão e safra
"""

import json

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation

from .models import (
    OrdemServico, OrdemServicoInsumo, CustoTalhao, CustoHoraMaquina,
    TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS,
    EtapaColheita, PushSubscriptionCampo, OSIntervalo,
    OSTransplantio, OSReplantio, OSFuncionario, OSMaquina,
    proximo_numero_corte, idiarn_validator, cultura_atual_talhao,
)
from cadastros.models import Talhao, Safra, SafraCultura, HistoricoTalhao
from .forms import (
    OrdemServicoForm, OSFuncionarioFormSet, OSMaquinaFormSet,
    OrdemServicoInsumoForm, CustoHoraMaquinaForm,
    OSTransplantioForm, OSReplantioForm,
    OSFuncionarioForm, OSMaquinaForm,
)

SUBTIPO_LEGADO_TRANSPLANTE = 'TRANSPLANTE'
SUBTIPO_LEGADO_REPLANTIO = 'REPLANTIO'


def _subtipo_legado(os_obj):
    return os_obj.subtipo_servico.subtipo_legado if os_obj.subtipo_servico_id else ''


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


from estoque.models import MovimentacaoEstoque


def _sort_key(item, key):
    value = item.get(key)
    if value is None:
        return Decimal('0') if key.startswith('total_') or key == 'custo_medio_ha' else ''
    return value


_STATUS_PRIORITY = ('EM_ANDAMENTO', 'ABERTA', 'APROVADA', 'CONCLUIDA', 'CANCELADA')


def _status_principal(ordens):
    """Status mais urgente/ativo para exibição na célula da matriz."""
    if not ordens:
        return None
    statuses = {o.status for o in ordens}
    for s in _STATUS_PRIORITY:
        if s in statuses:
            return s
    return ordens[0].status


def _aplicar_ordenacao_consolidado(dados, campo, direcao, mapa_campos, campo_padrao):
    campo_real = mapa_campos.get(campo, campo_padrao)
    reverse = direcao == 'desc'
    return sorted(dados, key=lambda x: _sort_key(x, campo_real), reverse=reverse)


# ============================================================================
# ORDENS DE SERVIÇO
# ============================================================================

@login_required
def os_list(request):
    """Lista todas as Ordens de Serviço da empresa com estatísticas"""
    empresa = request.user.empresa
    qs = OrdemServico.objects.filter(empresa=empresa).select_related(
        'talhao', 'safra', 'responsavel', 'tipo_servico', 'subtipo_servico', 'modalidade_execucao'
    )

    # Filtros
    status_filter = request.GET.get('status')
    tipo_servico_filter = request.GET.get('tipo_servico')
    talhao_filter = request.GET.get('talhao')
    safra_filter = request.GET.get('safra')
    search = request.GET.get('q', '').strip()

    if status_filter:
        qs = qs.filter(status=status_filter)
    if tipo_servico_filter:
        qs = qs.filter(tipo_servico_id=tipo_servico_filter)
    if talhao_filter:
        qs = qs.filter(talhao_id=talhao_filter)
    if safra_filter:
        qs = qs.filter(safra_id=safra_filter)
    if search:
        qs = qs.filter(
            Q(numero__icontains=search) |
            Q(talhao__nome__icontains=search) |
            Q(responsavel__nome_completo__icontains=search)
        )

    # Estatísticas
    todas = OrdemServico.objects.filter(empresa=empresa)
    stats = {
        'total': todas.count(),
        'abertas': todas.filter(status='ABERTA').count(),
        'aprovadas': todas.filter(status='APROVADA').count(),
        'em_andamento': todas.filter(status='EM_ANDAMENTO').count(),
        'concluidas': todas.filter(status='CONCLUIDA').count(),
        'canceladas': todas.filter(status='CANCELADA').count(),
    }

    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    safras = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')
    tipos_servico = list(TipoServicoOS.objects.filter(
        Q(empresa=empresa) | Q(empresa=None), ativo=True
    ).order_by('ordem', 'nome'))

    view_mode = request.GET.get('view', 'kanban')

    # Matriz: pivot talhão × tipo de serviço
    matrix_rows = []
    matrix_has_sem_tipo = False
    if view_mode == 'matriz':
        from collections import defaultdict
        pivot = defaultdict(lambda: defaultdict(list))
        for os_obj in qs:
            tipo_key = os_obj.tipo_servico_id if os_obj.tipo_servico_id else 0
            pivot[os_obj.talhao_id][tipo_key].append(os_obj)
            if not os_obj.tipo_servico_id:
                matrix_has_sem_tipo = True

        talhao_ids = list(
            qs.values_list('talhao_id', flat=True).distinct()
        )
        talhao_map = {t.id: t for t in Talhao.objects.filter(id__in=talhao_ids)}
        talhoes_na_matriz = sorted(
            [talhao_map[tid] for tid in talhao_ids if tid in talhao_map],
            key=lambda t: t.nome,
        )

        for talhao in talhoes_na_matriz:
            cells = []
            for tipo in tipos_servico:
                ordens_celula = pivot[talhao.id].get(tipo.id, [])
                cells.append({
                    'tipo_id': tipo.id,
                    'ordens': ordens_celula,
                    'status_principal': _status_principal(ordens_celula),
                })
            if matrix_has_sem_tipo:
                ordens_sem_tipo = pivot[talhao.id].get(0, [])
                cells.append({
                    'tipo_id': 0,
                    'ordens': ordens_sem_tipo,
                    'status_principal': _status_principal(ordens_sem_tipo),
                })
            matrix_rows.append({'talhao': talhao, 'cells': cells})

    context = {
        'ordens': qs,
        'stats': stats,
        'talhoes': talhoes,
        'safras': safras,
        'tipos_servico': tipos_servico,
        'status_choices': OrdemServico.STATUS_CHOICES,
        'status_filter': status_filter or '',
        'tipo_servico_filter': tipo_servico_filter or '',
        'talhao_filter': talhao_filter or '',
        'safra_filter': safra_filter or '',
        'search': search,
        'view_mode': view_mode,
        'matrix_rows': matrix_rows,
        'matrix_has_sem_tipo': matrix_has_sem_tipo,
        'matrix_tipos': tipos_servico,
    }
    return render(request, 'cadastros/os/os_list.html', context)


@login_required
def custo_talhao_list(request):
    """Relatório de custos por talhão e safra."""
    empresa = request.user.empresa

    qs = CustoTalhao.objects.filter(empresa=empresa).select_related('os', 'talhao', 'safra')

    talhao_filter = request.GET.get('talhao')
    safra_filter = request.GET.get('safra')
    search = request.GET.get('q', '').strip()
    sort_talhao = request.GET.get('sort_talhao', 'nome')
    dir_talhao = request.GET.get('dir_talhao', 'asc')
    sort_safra = request.GET.get('sort_safra', 'nome')
    dir_safra = request.GET.get('dir_safra', 'asc')

    if talhao_filter:
        qs = qs.filter(talhao_id=talhao_filter)
    if safra_filter:
        qs = qs.filter(safra_id=safra_filter)
    if search:
        qs = qs.filter(
            Q(os__numero__icontains=search) |
            Q(talhao__nome__icontains=search) |
            Q(safra__nome__icontains=search)
        )

    qs = qs.order_by('-data_registro')

    consolidado_talhoes = list(
        qs.values('talhao__nome', 'talhao_id').annotate(
            total_os=Count('id'),
            total_mao_obra=Sum('custo_mao_obra'),
            total_maquinario=Sum('custo_maquinario'),
            total_insumos=Sum('custo_insumos'),
            total_servico=Sum('custo_servico_externo'),
            total_estufa=Sum('custo_estufa'),
            total_area=Sum('area_executada_ha'),
        ).order_by('talhao__nome')
    )

    for item in consolidado_talhoes:
        total_item = (
            (item.get('total_mao_obra') or Decimal('0')) +
            (item.get('total_maquinario') or Decimal('0')) +
            (item.get('total_insumos') or Decimal('0')) +
            (item.get('total_servico') or Decimal('0')) +
            (item.get('total_estufa') or Decimal('0'))
        )
        area_item = item.get('total_area') or Decimal('0')
        item['total_geral'] = total_item
        item['custo_medio_ha'] = (total_item / area_item) if area_item > 0 else Decimal('0')

    consolidado_safras = list(
        qs.values('safra__nome', 'safra__ano', 'safra_id').annotate(
            total_os=Count('id'),
            total_mao_obra=Sum('custo_mao_obra'),
            total_maquinario=Sum('custo_maquinario'),
            total_insumos=Sum('custo_insumos'),
            total_servico=Sum('custo_servico_externo'),
            total_estufa=Sum('custo_estufa'),
            total_area=Sum('area_executada_ha'),
        ).order_by('safra__ano', 'safra__nome')
    )

    for item in consolidado_safras:
        total_item = (
            (item.get('total_mao_obra') or Decimal('0')) +
            (item.get('total_maquinario') or Decimal('0')) +
            (item.get('total_insumos') or Decimal('0')) +
            (item.get('total_servico') or Decimal('0')) +
            (item.get('total_estufa') or Decimal('0'))
        )
        area_item = item.get('total_area') or Decimal('0')
        nome_safra = item.get('safra__nome') or 'Sem safra'
        ano_safra = item.get('safra__ano')
        item['safra_label'] = f'{nome_safra} ({ano_safra})' if ano_safra else nome_safra
        item['total_geral'] = total_item
        item['custo_medio_ha'] = (total_item / area_item) if area_item > 0 else Decimal('0')

    consolidado_talhoes = _aplicar_ordenacao_consolidado(
        consolidado_talhoes,
        sort_talhao,
        dir_talhao,
        {
            'nome': 'talhao__nome',
            'total_os': 'total_os',
            'total_area': 'total_area',
            'total_geral': 'total_geral',
            'custo_medio_ha': 'custo_medio_ha',
        },
        'talhao__nome',
    )

    consolidado_safras = _aplicar_ordenacao_consolidado(
        consolidado_safras,
        sort_safra,
        dir_safra,
        {
            'nome': 'safra_label',
            'total_os': 'total_os',
            'total_area': 'total_area',
            'total_geral': 'total_geral',
            'custo_medio_ha': 'custo_medio_ha',
        },
        'safra_label',
    )

    resumo = qs.aggregate(
        total_mao_obra=Sum('custo_mao_obra'),
        total_maquinario=Sum('custo_maquinario'),
        total_insumos=Sum('custo_insumos'),
        total_servico=Sum('custo_servico_externo'),
        total_estufa=Sum('custo_estufa'),
        total_area=Sum('area_executada_ha'),
    )

    total_geral = (
        (resumo.get('total_mao_obra') or Decimal('0')) +
        (resumo.get('total_maquinario') or Decimal('0')) +
        (resumo.get('total_insumos') or Decimal('0')) +
        (resumo.get('total_servico') or Decimal('0')) +
        (resumo.get('total_estufa') or Decimal('0'))
    )
    total_area = resumo.get('total_area') or Decimal('0')
    custo_medio_ha = (total_geral / total_area) if total_area > 0 else Decimal('0')

    # --- Produção real por talhão (EtapaColheita.total_liquido_kg) ---
    producao_qs = EtapaColheita.objects.filter(os__empresa=empresa)
    if talhao_filter:
        producao_qs = producao_qs.filter(talhao_id=talhao_filter)
    if safra_filter:
        producao_qs = producao_qs.filter(safra_id=safra_filter)
    producao_map = {}
    for p in producao_qs.values('talhao__nome').annotate(total_kg=Sum('total_liquido_kg')):
        producao_map[p['talhao__nome']] = p['total_kg'] or Decimal('0')
    producao_total = sum(producao_map.values()) or Decimal('0')

    # Enriquecer consolidado_talhoes com produção, % e R$/kg
    grande_total = sum(i['total_geral'] for i in consolidado_talhoes) or Decimal('1')
    custo_ha_vals = [i['custo_medio_ha'] for i in consolidado_talhoes if i['custo_medio_ha'] > 0]
    talhao_mais_caro = max(consolidado_talhoes, key=lambda x: x['custo_medio_ha'], default=None)
    talhao_mais_barato = min(
        [i for i in consolidado_talhoes if i['custo_medio_ha'] > 0],
        key=lambda x: x['custo_medio_ha'],
        default=None,
    )
    for item in consolidado_talhoes:
        kg = producao_map.get(item['talhao__nome'])
        item['producao_kg'] = kg
        item['pct_total'] = round(float(item['total_geral'] / grande_total * 100), 1) if grande_total else 0
        item['custo_por_kg'] = (item['total_geral'] / kg).quantize(Decimal('0.01')) if kg else None

    # --- Dados JSON para Chart.js ---
    import json
    chart_labels = json.dumps([i['talhao__nome'] for i in consolidado_talhoes])
    chart_mao_obra = json.dumps([float(i.get('total_mao_obra') or 0) for i in consolidado_talhoes])
    chart_maquinario = json.dumps([float(i.get('total_maquinario') or 0) for i in consolidado_talhoes])
    chart_insumos = json.dumps([float(i.get('total_insumos') or 0) for i in consolidado_talhoes])
    chart_servico = json.dumps([float(i.get('total_servico') or 0) for i in consolidado_talhoes])
    chart_estufa = json.dumps([float(i.get('total_estufa') or 0) for i in consolidado_talhoes])
    resumo_doughnut = json.dumps([
        float(sum(i.get('total_mao_obra') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_maquinario') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_insumos') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_servico') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_estufa') or 0 for i in consolidado_talhoes)),
    ])

    export_format = request.GET.get('export')
    if export_format == 'excel':
        return _exportar_custo_talhao_excel(
            qs,
            consolidado_talhoes,
            consolidado_safras,
            resumo,
            total_geral,
            total_area,
            custo_medio_ha,
        )
    if export_format == 'pdf':
        return _exportar_custo_talhao_pdf(
            empresa,
            qs,
            consolidado_talhoes,
            consolidado_safras,
            resumo,
            total_geral,
            total_area,
            custo_medio_ha,
            talhao_filter,
            safra_filter,
            search,
        )

    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True).order_by('nome')
    safras = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')

    context = {
        'custos': qs,
        'talhoes': talhoes,
        'safras': safras,
        'talhao_filter': talhao_filter or '',
        'safra_filter': safra_filter or '',
        'search': search,
        'sort_talhao': sort_talhao,
        'dir_talhao': dir_talhao,
        'sort_safra': sort_safra,
        'dir_safra': dir_safra,
        'consolidado_talhoes': consolidado_talhoes,
        'consolidado_safras': consolidado_safras,
        'resumo': {
            'total_mao_obra': resumo.get('total_mao_obra') or Decimal('0'),
            'total_maquinario': resumo.get('total_maquinario') or Decimal('0'),
            'total_insumos': resumo.get('total_insumos') or Decimal('0'),
            'total_servico': resumo.get('total_servico') or Decimal('0'),
            'total_estufa': resumo.get('total_estufa') or Decimal('0'),
            'total_geral': total_geral,
            'total_area': total_area,
            'custo_medio_ha': custo_medio_ha,
        },
        'producao_total': producao_total,
        'talhao_mais_caro': talhao_mais_caro,
        'talhao_mais_barato': talhao_mais_barato,
        'chart_labels': chart_labels,
        'chart_mao_obra': chart_mao_obra,
        'chart_maquinario': chart_maquinario,
        'chart_insumos': chart_insumos,
        'chart_servico': chart_servico,
        'chart_estufa': chart_estufa,
        'resumo_doughnut': resumo_doughnut,
    }
    return render(request, 'cadastros/os/custo_talhao_list.html', context)


def _exportar_custo_talhao_excel(
    custos,
    consolidado_talhoes,
    consolidado_safras,
    resumo,
    total_geral,
    total_area,
    custo_medio_ha,
):
    """Exporta relatório de custo por talhão/safra para Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        return HttpResponse('Erro: openpyxl não instalado', status=500)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Custos por OS'

    header_fill = PatternFill(start_color='198754', end_color='198754', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF')
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    ws['A1'] = 'Relatório de Custo por Talhão e Safra'
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:J1')
    ws['A2'] = f'Gerado em: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}'
    ws['A2'].font = Font(italic=True)

    headers = ['OS', 'Talhão', 'Safra', 'Área (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Estufa', 'Total', 'R$/ha']
    for col, label in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col)
        cell.value = label
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    row = 5
    for item in custos:
        ws.cell(row=row, column=1, value=item.os.numero)
        ws.cell(row=row, column=2, value=item.talhao.nome)
        ws.cell(row=row, column=3, value=item.safra.nome if item.safra else '-')
        ws.cell(row=row, column=4, value=float(item.area_executada_ha or 0))
        ws.cell(row=row, column=5, value=float(item.custo_mao_obra or 0))
        ws.cell(row=row, column=6, value=float(item.custo_maquinario or 0))
        ws.cell(row=row, column=7, value=float(item.custo_insumos or 0))
        ws.cell(row=row, column=8, value=float(item.custo_servico_externo or 0))
        ws.cell(row=row, column=9, value=float(item.custo_estufa or 0))
        ws.cell(row=row, column=10, value=float(item.custo_total or 0))
        ws.cell(row=row, column=11, value=float(item.custo_por_hectare or 0))
        for col in range(1, 12):
            ws.cell(row=row, column=col).border = border
        row += 1

    resumo_row = row + 1
    ws.cell(row=resumo_row, column=1, value='Resumo').font = Font(bold=True)
    ws.cell(row=resumo_row + 1, column=1, value='Mão de Obra')
    ws.cell(row=resumo_row + 1, column=2, value=float(resumo.get('total_mao_obra') or 0))
    ws.cell(row=resumo_row + 2, column=1, value='Maquinário')
    ws.cell(row=resumo_row + 2, column=2, value=float(resumo.get('total_maquinario') or 0))
    ws.cell(row=resumo_row + 3, column=1, value='Insumos')
    ws.cell(row=resumo_row + 3, column=2, value=float(resumo.get('total_insumos') or 0))
    ws.cell(row=resumo_row + 4, column=1, value='Serviço Externo')
    ws.cell(row=resumo_row + 4, column=2, value=float(resumo.get('total_servico') or 0))
    ws.cell(row=resumo_row + 5, column=1, value='Total Geral')
    ws.cell(row=resumo_row + 5, column=2, value=float(total_geral or 0))
    ws.cell(row=resumo_row + 6, column=1, value='Área Total (ha)')
    ws.cell(row=resumo_row + 6, column=2, value=float(total_area or 0))
    ws.cell(row=resumo_row + 7, column=1, value='Custo Médio/ha')
    ws.cell(row=resumo_row + 7, column=2, value=float(custo_medio_ha or 0))

    ws2 = wb.create_sheet('Consolidado Talhão')
    headers2 = ['Talhão', 'Qtd OS', 'Área Total (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total Geral', 'R$/ha']
    for col, label in enumerate(headers2, start=1):
        cell = ws2.cell(row=1, column=col)
        cell.value = label
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    row2 = 2
    for item in consolidado_talhoes:
        ws2.cell(row=row2, column=1, value=item.get('talhao__nome') or '-')
        ws2.cell(row=row2, column=2, value=int(item.get('total_os') or 0))
        ws2.cell(row=row2, column=3, value=float(item.get('total_area') or 0))
        ws2.cell(row=row2, column=4, value=float(item.get('total_mao_obra') or 0))
        ws2.cell(row=row2, column=5, value=float(item.get('total_maquinario') or 0))
        ws2.cell(row=row2, column=6, value=float(item.get('total_insumos') or 0))
        ws2.cell(row=row2, column=7, value=float(item.get('total_servico') or 0))
        ws2.cell(row=row2, column=8, value=float(item.get('total_geral') or 0))
        ws2.cell(row=row2, column=9, value=float(item.get('custo_medio_ha') or 0))
        for col in range(1, 10):
            ws2.cell(row=row2, column=col).border = border
        row2 += 1

    ws3 = wb.create_sheet('Consolidado Safra')
    headers3 = ['Safra', 'Qtd OS', 'Área Total (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total Geral', 'R$/ha']
    for col, label in enumerate(headers3, start=1):
        cell = ws3.cell(row=1, column=col)
        cell.value = label
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    row3 = 2
    for item in consolidado_safras:
        ws3.cell(row=row3, column=1, value=item.get('safra_label') or 'Sem safra')
        ws3.cell(row=row3, column=2, value=int(item.get('total_os') or 0))
        ws3.cell(row=row3, column=3, value=float(item.get('total_area') or 0))
        ws3.cell(row=row3, column=4, value=float(item.get('total_mao_obra') or 0))
        ws3.cell(row=row3, column=5, value=float(item.get('total_maquinario') or 0))
        ws3.cell(row=row3, column=6, value=float(item.get('total_insumos') or 0))
        ws3.cell(row=row3, column=7, value=float(item.get('total_servico') or 0))
        ws3.cell(row=row3, column=8, value=float(item.get('total_geral') or 0))
        ws3.cell(row=row3, column=9, value=float(item.get('custo_medio_ha') or 0))
        for col in range(1, 10):
            ws3.cell(row=row3, column=col).border = border
        row3 += 1

    widths_ws = {1: 15, 2: 20, 3: 18, 4: 12, 5: 14, 6: 14, 7: 14, 8: 16, 9: 14, 10: 14}
    for col, width in widths_ws.items():
        ws.column_dimensions[chr(64 + col)].width = width

    widths_ws2 = {1: 20, 2: 10, 3: 14, 4: 14, 5: 14, 6: 14, 7: 16, 8: 14, 9: 12}
    for col, width in widths_ws2.items():
        ws2.column_dimensions[chr(64 + col)].width = width

    widths_ws3 = {1: 24, 2: 10, 3: 14, 4: 14, 5: 14, 6: 14, 7: 16, 8: 14, 9: 12}
    for col, width in widths_ws3.items():
        ws3.column_dimensions[chr(64 + col)].width = width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = (
        f'attachment; filename="custo_talhao_safra_{timezone.localtime().strftime("%d_%m_%Y")}.xlsx"'
    )
    wb.save(response)
    return response


def _exportar_custo_talhao_pdf(
    empresa,
    custos,
    consolidado_talhoes,
    consolidado_safras,
    resumo,
    total_geral,
    total_area,
    custo_medio_ha,
    talhao_filter,
    safra_filter,
    search,
):
    """Exporta relatório de custo por talhão/safra para PDF."""
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
    except ImportError:
        return HttpResponse('Erro: reportlab não instalado', status=500)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="custo_talhao_safra_{timezone.localtime().strftime("%d_%m_%Y")}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=landscape(A4), leftMargin=1.2 * cm, rightMargin=1.2 * cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleCustom',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#198754'),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'SubtitleCustom',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#555555'),
    )

    story = []
    story.append(Paragraph('Relatório de Custo por Talhão e Safra', title_style))
    story.append(Paragraph(f'Empresa: {empresa.nome}', subtitle_style))
    story.append(Paragraph(f'Gerado em: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}', subtitle_style))

    filtros = [
        f'Talhão: {talhao_filter or "Todos"}',
        f'Safra: {safra_filter or "Todas"}',
        f'Busca: {search or "-"}',
    ]
    story.append(Paragraph(' | '.join(filtros), subtitle_style))
    story.append(Spacer(1, 0.4 * cm))

    resumo_data = [
        ['Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Área Total (ha)', 'Custo Médio/ha', 'Total Geral'],
        [
            f"R$ {float(resumo.get('total_mao_obra') or 0):,.2f}",
            f"R$ {float(resumo.get('total_maquinario') or 0):,.2f}",
            f"R$ {float(resumo.get('total_insumos') or 0):,.2f}",
            f"R$ {float(resumo.get('total_servico') or 0):,.2f}",
            f"{float(total_area or 0):,.4f}",
            f"R$ {float(custo_medio_ha or 0):,.2f}",
            f"R$ {float(total_geral or 0):,.2f}",
        ],
    ]
    resumo_table = Table(resumo_data, colWidths=[4.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm, 4.0 * cm])
    resumo_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#F3F8F5')),
    ]))
    story.append(resumo_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph('Consolidado por Talhão', ParagraphStyle('Sub1', parent=styles['Heading3'], alignment=TA_LEFT)))
    cons_data = [['Talhão', 'Qtd OS', 'Área (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total', 'R$/ha']]
    for item in consolidado_talhoes:
        cons_data.append([
            item.get('talhao__nome') or '-',
            str(item.get('total_os') or 0),
            f"{float(item.get('total_area') or 0):,.4f}",
            f"R$ {float(item.get('total_mao_obra') or 0):,.2f}",
            f"R$ {float(item.get('total_maquinario') or 0):,.2f}",
            f"R$ {float(item.get('total_insumos') or 0):,.2f}",
            f"R$ {float(item.get('total_servico') or 0):,.2f}",
            f"R$ {float(item.get('total_geral') or 0):,.2f}",
            f"R$ {float(item.get('custo_medio_ha') or 0):,.2f}",
        ])
    if len(cons_data) == 1:
        cons_data.append(['-', '0', '0,0000', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00'])

    cons_table = Table(cons_data, repeatRows=1)
    cons_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0D6EFD')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ]))
    story.append(cons_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph('Consolidado por Safra', ParagraphStyle('Sub3', parent=styles['Heading3'], alignment=TA_LEFT)))
    cons_safra_data = [['Safra', 'Qtd OS', 'Área (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total', 'R$/ha']]
    for item in consolidado_safras:
        cons_safra_data.append([
            item.get('safra_label') or 'Sem safra',
            str(item.get('total_os') or 0),
            f"{float(item.get('total_area') or 0):,.4f}",
            f"R$ {float(item.get('total_mao_obra') or 0):,.2f}",
            f"R$ {float(item.get('total_maquinario') or 0):,.2f}",
            f"R$ {float(item.get('total_insumos') or 0):,.2f}",
            f"R$ {float(item.get('total_servico') or 0):,.2f}",
            f"R$ {float(item.get('total_geral') or 0):,.2f}",
            f"R$ {float(item.get('custo_medio_ha') or 0):,.2f}",
        ])
    if len(cons_safra_data) == 1:
        cons_safra_data.append(['-', '0', '0,0000', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00'])

    cons_safra_table = Table(cons_safra_data, repeatRows=1)
    cons_safra_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6F42C1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
    ]))
    story.append(cons_safra_table)
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph('Detalhamento por OS', ParagraphStyle('Sub2', parent=styles['Heading3'], alignment=TA_LEFT)))
    det_data = [['OS', 'Talhão', 'Safra', 'Área', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total', 'R$/ha']]
    for item in custos:
        det_data.append([
            item.os.numero,
            item.talhao.nome,
            item.safra.nome if item.safra else '-',
            f"{float(item.area_executada_ha or 0):,.4f}",
            f"R$ {float(item.custo_mao_obra or 0):,.2f}",
            f"R$ {float(item.custo_maquinario or 0):,.2f}",
            f"R$ {float(item.custo_insumos or 0):,.2f}",
            f"R$ {float(item.custo_servico_externo or 0):,.2f}",
            f"R$ {float(item.custo_total or 0):,.2f}",
            f"R$ {float(item.custo_por_hectare or 0):,.2f}",
        ])
    if len(det_data) == 1:
        det_data.append(['-', '-', '-', '0,0000', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00', 'R$ 0,00'])

    det_table = Table(det_data, repeatRows=1)
    det_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(det_table)

    doc.build(story)
    return response


@login_required
def os_create(request):
    """Cria nova Ordem de Serviço com funcionários e máquinas"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST, request.FILES, empresa=empresa)
        func_formset = OSFuncionarioFormSet(request.POST, prefix='func')
        maq_formset = OSMaquinaFormSet(request.POST, prefix='maq')
        transplantio_form = OSTransplantioForm(request.POST, prefix='transplantio', empresa=empresa)
        replantio_form = OSReplantioForm(request.POST, prefix='replantio', empresa=empresa)

        # Limita querysets por empresa antes da validacao.
        _enrich_formset(func_formset, empresa)
        _enrich_formset(maq_formset, empresa)

        subtipo_legado = ''
        if form.data.get('subtipo_servico'):
            subtipo_legado = SubtipoServicoOS.objects.filter(
                pk=form.data.get('subtipo_servico')
            ).values_list('subtipo_legado', flat=True).first() or ''

        precisa_transplantio = subtipo_legado == SUBTIPO_LEGADO_TRANSPLANTE
        precisa_replantio = subtipo_legado == SUBTIPO_LEGADO_REPLANTIO

        form_valido = form.is_valid()

        extras_validos = True
        if precisa_transplantio and not transplantio_form.data.get('transplantio-lote_muda'):
            transplantio_form.add_error('lote_muda', 'Selecione o lote de mudas para o transplantio.')
            extras_validos = False
        elif precisa_transplantio and not transplantio_form.is_valid():
            extras_validos = False
        elif precisa_transplantio and form_valido:
            lote_muda = transplantio_form.cleaned_data.get('lote_muda')
            safra_cultura = form.cleaned_data.get('safra_cultura')
            if lote_muda and safra_cultura and lote_muda.cultura_id != safra_cultura.cultura_id:
                transplantio_form.add_error('lote_muda', (
                    f'A muda selecionada é de {lote_muda.cultura.nome}, mas a cultura da '
                    f'safra escolhida é {safra_cultura.cultura.nome}.'
                ))
                extras_validos = False
        if precisa_replantio and not replantio_form.data.get('replantio-quantidade'):
            replantio_form.add_error('quantidade', 'Informe a quantidade replantada.')
            extras_validos = False
        elif precisa_replantio and not replantio_form.is_valid():
            extras_validos = False

        if form_valido and func_formset.is_valid() and maq_formset.is_valid() and extras_validos:
            os_obj = form.save(commit=False)
            os_obj.empresa = empresa
            os_obj.solicitante = request.user
            os_obj.cadastrado_por = request.user
            os_obj.historico_talhao = HistoricoTalhao.objects.filter(
                talhao=os_obj.talhao, data_colheita__isnull=True
            ).order_by('-data_plantio').first()
            os_obj.save()

            func_formset.instance = os_obj
            func_formset.save()

            maq_formset.instance = os_obj
            maq_formset.save()

            if precisa_transplantio:
                transplantio = transplantio_form.save(commit=False)
                transplantio.os = os_obj
                transplantio.full_clean()
                transplantio.save()
            if precisa_replantio:
                replantio = replantio_form.save(commit=False)
                replantio.os = os_obj
                replantio.save()

            messages.success(request, f'Ordem de Serviço {os_obj.numero} criada com sucesso!')
            return redirect('operacoes_campo:os_detail', pk=os_obj.pk)
    else:
        form_initial = {}
        transplantio_initial = {}

        lote_muda_id = request.GET.get('lote_muda')
        if lote_muda_id:
            from estufas.models import LoteMuda
            lote_muda = LoteMuda.objects.filter(
                empresa=empresa, pk=lote_muda_id, status='PRONTO'
            ).first()
            if lote_muda:
                subtipo_transplante = SubtipoServicoOS.objects.filter(
                    subtipo_legado=SUBTIPO_LEGADO_TRANSPLANTE, ativo=True
                ).filter(Q(empresa=empresa) | Q(empresa=None)).select_related('tipo_servico').first()
                if subtipo_transplante:
                    form_initial['tipo_servico'] = subtipo_transplante.tipo_servico_id
                    form_initial['subtipo_servico'] = subtipo_transplante.pk
                transplantio_initial['lote_muda'] = lote_muda.pk
                transplantio_initial['quantidade_transplantada'] = lote_muda.quantidade_disponivel

        form = OrdemServicoForm(empresa=empresa, initial=form_initial)
        func_formset = OSFuncionarioFormSet(prefix='func')
        maq_formset = OSMaquinaFormSet(prefix='maq')
        transplantio_form = OSTransplantioForm(prefix='transplantio', empresa=empresa, initial=transplantio_initial)
        replantio_form = OSReplantioForm(prefix='replantio', empresa=empresa)

    # Enrich formsets with empresa context for querysets
    _enrich_formset(func_formset, empresa)
    _enrich_formset(maq_formset, empresa)

    context = {
        'form': form,
        'func_formset': func_formset,
        'maq_formset': maq_formset,
        'transplantio_form': transplantio_form,
        'replantio_form': replantio_form,
        'titulo': 'Nova Ordem de Serviço',
        'action': 'Criar',
    }
    return render(request, 'cadastros/os/os_form.html', context)


def _enrich_formset(formset, empresa):
    """Reaplica empresa nos querysets dos formulários do formset"""
    for form in formset.forms:
        if hasattr(form, 'fields'):
            if 'funcionario' in form.fields:
                from rh.models import Funcionario
                form.fields['funcionario'].queryset = Funcionario.objects.filter(
                    empresa=empresa, ativo=True
                )
            if 'veiculo' in form.fields:
                from frota.models import Vehicle
                form.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa)
            if 'operador' in form.fields:
                from rh.models import Funcionario
                form.fields['operador'].queryset = Funcionario.objects.filter(
                    empresa=empresa, ativo=True
                )
            if 'custo_hora_config' in form.fields:
                form.fields['custo_hora_config'].queryset = CustoHoraMaquina.objects.filter(
                    empresa=empresa, ativo=True
                )


@login_required
def os_detail(request, pk):
    """Detalhes da OS com breakdown de custos"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    funcionarios = os_obj.funcionarios_os.select_related('funcionario').all()
    maquinas = os_obj.maquinas_os.select_related('veiculo', 'operador').all()
    intervalos = os_obj.intervalos.select_related('funcionario').order_by('inicio')

    # Custo MO: mesma lógica de CustoTalhao.recalcular()
    # Intervalos do portal têm prioridade; alocações manuais complementam apenas quem não tem intervalo
    intervalos_fechados = [iv for iv in intervalos if iv.fim is not None]
    workers_com_intervalo = {iv.funcionario_id for iv in intervalos_fechados}
    custo_intervalos = sum(iv.custo_calculado for iv in intervalos_fechados)
    custo_mo = custo_intervalos + sum(
        f.custo_calculado for f in funcionarios
        if f.funcionario_id not in workers_com_intervalo
    )

    custo_maq = sum(m.custo_calculado for m in maquinas)
    custo_serv = os_obj.valor_servico_externo or Decimal('0')

    transplantio_obj = getattr(os_obj, 'transplantio', None)
    replantio_obj = getattr(os_obj, 'replantio', None)
    custo_estufa = (
        (transplantio_obj.custo_transferido if transplantio_obj else Decimal('0'))
        + (replantio_obj.custo_adicional if replantio_obj else Decimal('0'))
    )

    insumos_os = os_obj.insumos_os.select_related('produto', 'unidade_medida', 'movimentacao').all()

    # Custo de insumos (prioriza os itens diretos da OS)
    custo_ins = Decimal('0')
    if insumos_os.exists():
        custo_ins = sum((i.custo_total for i in insumos_os), Decimal('0'))
    elif os_obj.requisicao:
        for item in os_obj.requisicao.itens.all():
            if item.custo_estimado and item.quantidade_atendida:
                custo_ins += item.custo_estimado * item.quantidade_atendida

    custo_total = custo_mo + custo_maq + custo_ins + custo_serv + custo_estufa
    area = os_obj.area_executada_ha
    custo_ha = (custo_total / area).quantize(Decimal('0.01')) if area else Decimal('0')

    movimentacoes_os = MovimentacaoEstoque.objects.filter(
        empresa=empresa,
        documento=os_obj.numero,
        origem='OS_DIRETA',
        tipo='SAIDA',
        status='EXECUTADO',
    ).select_related('produto', 'unidade_medida').order_by('-data_execucao', '-id')

    try:
        custo_talhao_obj = os_obj.custo_talhao
    except Exception:
        custo_talhao_obj = None

    # Tipo legado para detectar colheita
    tipo_legado = ''
    if os_obj.tipo_servico_id:
        tipo_legado = os_obj.tipo_servico.tipo_legado or ''
    elif os_obj.tipo:
        tipo_legado = os_obj.tipo

    # Etapas de colheita (se aplicável)
    etapas_colheita = []
    total_colheita_kg = Decimal('0')
    if tipo_legado == 'COLHEITA':
        from operacoes_campo.models import EtapaColheita
        etapas_colheita = EtapaColheita.objects.filter(os=os_obj).order_by('numero_etapa')
        total_colheita_kg = sum((e.total_liquido_kg or Decimal('0')) for e in etapas_colheita)

    tem_intervalo_aberto = any(iv.fim is None for iv in intervalos)
    maquinas_sem_horimetro_final = [
        m for m in maquinas
        if m.horimetro_inicial is not None and m.horimetro_final is None
    ]
    maquinas_pendentes_horimetro = [
        m for m in maquinas
        if m.horimetro_inicial is None or m.horimetro_final is None
    ]

    context = {
        'os': os_obj,
        'funcionarios': funcionarios,
        'maquinas': maquinas,
        'custo_mo': custo_mo,
        'custo_maq': custo_maq,
        'custo_ins': custo_ins,
        'custo_serv': custo_serv,
        'custo_estufa': custo_estufa,
        'custo_total': custo_total,
        'custo_ha': custo_ha,
        'custo_talhao_obj': custo_talhao_obj,
        'insumos_os': insumos_os,
        'movimentacoes_os': movimentacoes_os,
        'tipo_legado': tipo_legado,
        'etapas_colheita': etapas_colheita,
        'total_colheita_kg': total_colheita_kg,
        'tem_intervalo_aberto': tem_intervalo_aberto,
        'intervalos': intervalos,
        'intervalos_fechados': intervalos_fechados,
        'custo_intervalos': custo_intervalos,
        'workers_com_intervalo': workers_com_intervalo,
        'maquinas_sem_horimetro_final': maquinas_sem_horimetro_final,
        'maquinas_pendentes_horimetro': maquinas_pendentes_horimetro,
        'transplantio_obj': transplantio_obj,
        'replantio_obj': replantio_obj,
    }
    return render(request, 'cadastros/os/os_detail.html', context)


@login_required
@require_POST
def os_recalcular_custos(request, pk):
    """
    Recalcula CustoTalhao de uma OS concluída.
    Fecha intervalos abertos, preenche hora_inicio/hora_fim ausentes
    usando data_inicio/data_fim da OS, depois chama CustoTalhao.recalcular().
    """
    from django.utils import timezone as tz
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status != 'CONCLUIDA':
        messages.error(request, 'Só é possível recalcular custos de OS concluídas.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    data_fim = os_obj.data_fim or tz.now()
    data_fim_local = tz.localtime(data_fim)

    # Fecha OSIntervalo abertos (necessário para custo_intervalos no recalcular)
    os_obj.intervalos.filter(fim__isnull=True).update(fim=data_fim)

    # Backfill hora_inicio para trabalhadores sem horário de entrada
    data_inicio = os_obj.data_inicio or data_fim
    data_inicio_local = tz.localtime(data_inicio)
    os_obj.funcionarios_os.filter(hora_inicio__isnull=True).update(
        hora_inicio=data_inicio_local.time(),
        data_execucao=data_inicio_local.date(),
    )

    # Backfill hora_fim para todos os trabalhadores sem horário de saída
    os_obj.funcionarios_os.filter(hora_fim__isnull=True).update(
        hora_fim=data_fim_local.time(),
    )

    try:
        custo_obj, _ = CustoTalhao.objects.get_or_create(
            os=os_obj,
            defaults={
                'empresa': empresa,
                'talhao': os_obj.talhao,
                'safra': os_obj.safra,
            },
        )
        custo_obj.recalcular()
        messages.success(request, 'Custos recalculados com sucesso.')
    except Exception as e:
        messages.error(request, f'Erro ao recalcular: {e}')

    return redirect('operacoes_campo:os_detail', pk=pk)


@login_required
@require_POST
def os_pausar_admin(request, pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status != 'EM_ANDAMENTO':
        messages.warning(request, 'Não é possível pausar esta OS.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    agora = timezone.now()
    atualizados = os_obj.intervalos.filter(fim__isnull=True).update(fim=agora)
    if atualizados:
        messages.info(request, f'OS pausada — {atualizados} intervalo(s) de trabalho encerrado(s).')
    else:
        messages.warning(request, 'Nenhum intervalo aberto encontrado.')
    return redirect('operacoes_campo:os_detail', pk=pk)


@login_required
@require_POST
def os_retomar_admin(request, pk):
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status != 'EM_ANDAMENTO':
        messages.warning(request, 'Não é possível retomar esta OS.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if os_obj.intervalos.filter(fim__isnull=True).exists():
        messages.warning(request, 'Esta OS já está em andamento.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    # Recria intervalos para todos os funcionários que já trabalharam nesta OS
    fechados_ids = set(os_obj.intervalos.filter(fim__isnull=False).values_list('funcionario_id', flat=True))
    abertos_ids  = set(os_obj.intervalos.filter(fim__isnull=True).values_list('funcionario_id', flat=True))
    retomar_ids  = fechados_ids - abertos_ids

    if not retomar_ids:
        messages.warning(request, 'Nenhum funcionário com intervalo anterior encontrado. Retome pelo portal do campo.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    agora = timezone.now()
    for fid in retomar_ids:
        OSIntervalo.objects.create(os=os_obj, funcionario_id=fid, inicio=agora)

    messages.success(request, f'OS retomada — {len(retomar_ids)} intervalo(s) de trabalho reaberto(s).')
    return redirect('operacoes_campo:os_detail', pk=pk)


@login_required
def os_insumo_add(request, pk):
    """Adiciona um insumo diretamente na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    ajax = _is_ajax(request)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        if ajax:
            return JsonResponse({'success': False, 'error': 'Não é possível adicionar insumos em uma OS concluída ou cancelada.'}, status=400)
        messages.error(request, 'Não é possível adicionar insumos em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OrdemServicoInsumoForm(request.POST, empresa=empresa, os=os_obj)
        if form.is_valid():
            item = form.save(commit=False)
            item.empresa = empresa
            item.os = os_obj
            item.save()
            if ajax:
                return JsonResponse({'success': True})
            messages.success(request, 'Insumo adicionado à OS com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OrdemServicoInsumoForm(empresa=empresa, os=os_obj)

    template = 'cadastros/os/os_insumo_form_fields.html' if ajax else 'cadastros/os/os_insumo_form.html'
    return render(request, template, {
        'os': os_obj,
        'form': form,
        'titulo': f'Adicionar insumo - {os_obj.numero}',
        'action': 'Adicionar',
        'is_modal': ajax,
        'action_url': request.path if ajax else None,
    })


@login_required
def os_insumo_edit(request, pk, insumo_pk):
    """Edita um insumo lançado na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    insumo = get_object_or_404(OrdemServicoInsumo, pk=insumo_pk, os=os_obj, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar insumos em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OrdemServicoInsumoForm(request.POST, instance=insumo, empresa=empresa, os=os_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insumo da OS atualizado com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OrdemServicoInsumoForm(instance=insumo, empresa=empresa, os=os_obj)

    return render(request, 'cadastros/os/os_insumo_form.html', {
        'os': os_obj,
        'form': form,
        'insumo': insumo,
        'titulo': f'Editar insumo - {os_obj.numero}',
        'action': 'Salvar',
    })


@login_required
def os_insumo_delete(request, pk, insumo_pk):
    """Remove um item de insumo da OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    insumo = get_object_or_404(OrdemServicoInsumo, pk=insumo_pk, os=os_obj, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível remover insumos em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo removido da OS com sucesso.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    return render(request, 'cadastros/os/os_insumo_confirm_delete.html', {
        'os': os_obj,
        'insumo': insumo,
    })


@login_required
def os_funcionario_add(request, pk):
    """Aloca manualmente um funcionário na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    ajax = _is_ajax(request)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        if ajax:
            return JsonResponse({'success': False, 'error': 'Não é possível adicionar mão de obra em uma OS concluída ou cancelada.'}, status=400)
        messages.error(request, 'Não é possível adicionar mão de obra em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OSFuncionarioForm(request.POST, empresa=empresa)
        form.fields['funcionario'].required = True
        if form.is_valid():
            item = form.save(commit=False)
            item.os = os_obj
            item.save()
            if ajax:
                return JsonResponse({'success': True})
            messages.success(request, 'Funcionário adicionado à OS com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OSFuncionarioForm(empresa=empresa)
        form.fields['funcionario'].required = True

    template = 'cadastros/os/os_funcionario_form_fields.html' if ajax else 'cadastros/os/os_funcionario_form.html'
    return render(request, template, {
        'os': os_obj,
        'form': form,
        'titulo': f'Adicionar mão de obra - {os_obj.numero}',
        'action': 'Adicionar',
        'is_modal': ajax,
        'action_url': request.path if ajax else None,
    })


@login_required
def os_funcionario_edit(request, pk, funcionario_pk):
    """Edita uma alocação manual de funcionário na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    funcionario_os = get_object_or_404(OSFuncionario, pk=funcionario_pk, os=os_obj)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar mão de obra em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OSFuncionarioForm(request.POST, instance=funcionario_os, empresa=empresa)
        form.fields['funcionario'].required = True
        if form.is_valid():
            form.save()
            messages.success(request, 'Mão de obra da OS atualizada com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OSFuncionarioForm(instance=funcionario_os, empresa=empresa)
        form.fields['funcionario'].required = True

    return render(request, 'cadastros/os/os_funcionario_form.html', {
        'os': os_obj,
        'form': form,
        'funcionario_os': funcionario_os,
        'titulo': f'Editar mão de obra - {os_obj.numero}',
        'action': 'Salvar',
    })


@login_required
def os_funcionario_delete(request, pk, funcionario_pk):
    """Remove uma alocação manual de funcionário da OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    funcionario_os = get_object_or_404(OSFuncionario, pk=funcionario_pk, os=os_obj)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível remover mão de obra em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        funcionario_os.delete()
        messages.success(request, 'Funcionário removido da OS com sucesso.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    return render(request, 'cadastros/os/os_funcionario_confirm_delete.html', {
        'os': os_obj,
        'funcionario_os': funcionario_os,
    })


@login_required
def os_maquina_add(request, pk):
    """Aloca manualmente uma máquina/veículo na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    ajax = _is_ajax(request)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        if ajax:
            return JsonResponse({'success': False, 'error': 'Não é possível adicionar maquinário em uma OS concluída ou cancelada.'}, status=400)
        messages.error(request, 'Não é possível adicionar maquinário em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OSMaquinaForm(request.POST, empresa=empresa)
        form.fields['veiculo'].required = True
        if form.is_valid():
            item = form.save(commit=False)
            item.os = os_obj
            item.save()
            if ajax:
                return JsonResponse({'success': True})
            messages.success(request, 'Máquina adicionada à OS com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OSMaquinaForm(empresa=empresa)
        form.fields['veiculo'].required = True

    template = 'cadastros/os/os_maquina_form_fields.html' if ajax else 'cadastros/os/os_maquina_form.html'
    return render(request, template, {
        'os': os_obj,
        'form': form,
        'titulo': f'Adicionar maquinário - {os_obj.numero}',
        'action': 'Adicionar',
        'is_modal': ajax,
        'action_url': request.path if ajax else None,
    })


@login_required
def os_maquina_edit(request, pk, maquina_pk):
    """Edita uma alocação manual de máquina na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    maquina_os = get_object_or_404(OSMaquina, pk=maquina_pk, os=os_obj)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar maquinário em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        form = OSMaquinaForm(request.POST, instance=maquina_os, empresa=empresa)
        form.fields['veiculo'].required = True
        if form.is_valid():
            form.save()
            messages.success(request, 'Maquinário da OS atualizado com sucesso.')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OSMaquinaForm(instance=maquina_os, empresa=empresa)
        form.fields['veiculo'].required = True

    return render(request, 'cadastros/os/os_maquina_form.html', {
        'os': os_obj,
        'form': form,
        'maquina_os': maquina_os,
        'titulo': f'Editar maquinário - {os_obj.numero}',
        'action': 'Salvar',
    })


@login_required
def os_maquina_delete(request, pk, maquina_pk):
    """Remove uma alocação manual de máquina da OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    maquina_os = get_object_or_404(OSMaquina, pk=maquina_pk, os=os_obj)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível remover maquinário em uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    if request.method == 'POST':
        maquina_os.delete()
        messages.success(request, 'Máquina removida da OS com sucesso.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    return render(request, 'cadastros/os/os_maquina_confirm_delete.html', {
        'os': os_obj,
        'maquina_os': maquina_os,
    })


@login_required
def os_update(request, pk):
    """Edita uma Ordem de Serviço"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar uma OS concluída ou cancelada.')
        return redirect('operacoes_campo:os_detail', pk=pk)

    transplantio_instance = getattr(os_obj, 'transplantio', None)
    replantio_instance = getattr(os_obj, 'replantio', None)

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST, request.FILES, instance=os_obj, empresa=empresa)
        func_formset = OSFuncionarioFormSet(request.POST, instance=os_obj, prefix='func')
        maq_formset = OSMaquinaFormSet(request.POST, instance=os_obj, prefix='maq')
        transplantio_form = OSTransplantioForm(request.POST, prefix='transplantio', empresa=empresa, instance=transplantio_instance)
        replantio_form = OSReplantioForm(request.POST, prefix='replantio', empresa=empresa, instance=replantio_instance)

        subtipo_legado = ''
        if form.data.get('subtipo_servico'):
            subtipo_legado = SubtipoServicoOS.objects.filter(
                pk=form.data.get('subtipo_servico')
            ).values_list('subtipo_legado', flat=True).first() or ''

        precisa_transplantio = subtipo_legado == SUBTIPO_LEGADO_TRANSPLANTE
        precisa_replantio = subtipo_legado == SUBTIPO_LEGADO_REPLANTIO

        form_valido = form.is_valid()

        extras_validos = True
        if precisa_transplantio and not transplantio_form.data.get('transplantio-lote_muda') and not transplantio_instance:
            transplantio_form.add_error('lote_muda', 'Selecione o lote de mudas para o transplantio.')
            extras_validos = False
        elif precisa_transplantio and not transplantio_form.is_valid():
            extras_validos = False
        elif precisa_transplantio and form_valido:
            lote_muda = transplantio_form.cleaned_data.get('lote_muda')
            safra_cultura = form.cleaned_data.get('safra_cultura')
            if lote_muda and safra_cultura and lote_muda.cultura_id != safra_cultura.cultura_id:
                transplantio_form.add_error('lote_muda', (
                    f'A muda selecionada é de {lote_muda.cultura.nome}, mas a cultura da '
                    f'safra escolhida é {safra_cultura.cultura.nome}.'
                ))
                extras_validos = False
        if precisa_replantio and not replantio_form.data.get('replantio-quantidade') and not replantio_instance:
            replantio_form.add_error('quantidade', 'Informe a quantidade replantada.')
            extras_validos = False
        elif precisa_replantio and not replantio_form.is_valid():
            extras_validos = False

        if form_valido and func_formset.is_valid() and maq_formset.is_valid() and extras_validos:
            form.save()
            func_formset.save()
            maq_formset.save()

            if precisa_transplantio and transplantio_form.has_changed():
                transplantio = transplantio_form.save(commit=False)
                transplantio.os = os_obj
                transplantio.full_clean()
                transplantio.save()
            if precisa_replantio and replantio_form.has_changed():
                replantio = replantio_form.save(commit=False)
                replantio.os = os_obj
                replantio.save()

            messages.success(request, f'OS {os_obj.numero} atualizada com sucesso!')
            return redirect('operacoes_campo:os_detail', pk=pk)
    else:
        form = OrdemServicoForm(instance=os_obj, empresa=empresa)
        func_formset = OSFuncionarioFormSet(instance=os_obj, prefix='func')
        maq_formset = OSMaquinaFormSet(instance=os_obj, prefix='maq')
        transplantio_form = OSTransplantioForm(prefix='transplantio', empresa=empresa, instance=transplantio_instance)
        replantio_form = OSReplantioForm(prefix='replantio', empresa=empresa, instance=replantio_instance)

    _enrich_formset(func_formset, empresa)
    _enrich_formset(maq_formset, empresa)

    context = {
        'form': form,
        'func_formset': func_formset,
        'maq_formset': maq_formset,
        'transplantio_form': transplantio_form,
        'replantio_form': replantio_form,
        'os': os_obj,
        'titulo': f'Editar OS {os_obj.numero}',
        'action': 'Salvar',
    }
    return render(request, 'cadastros/os/os_form.html', context)


@login_required
def os_delete(request, pk):
    """Exclui (cancela) uma Ordem de Serviço"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if os_obj.status == 'CONCLUIDA':
            messages.error(request, 'Não é possível excluir uma OS concluída.')
            return redirect('operacoes_campo:os_detail', pk=pk)
        numero = os_obj.numero
        os_obj.delete()
        messages.success(request, f'OS {numero} excluída com sucesso.')
        return redirect('operacoes_campo:os_list')

    context = {'os': os_obj}
    return render(request, 'cadastros/os/os_confirm_delete.html', context)


@login_required
def os_aprovar(request, pk):
    """Aprova uma Ordem de Serviço (ABERTA → APROVADA)"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if os_obj.status != 'ABERTA':
            messages.error(request, 'Somente OS abertas podem ser aprovadas.')
        elif os_obj.tipo_legado_efetivo == 'PLANTIO':
            messages.error(request, 'OS de plantio exige o IDIARN — aprove pela tela de detalhe da OS.')
        else:
            os_obj.status = 'APROVADA'
            os_obj.aprovador = request.user
            os_obj.data_aprovacao = timezone.now()
            os_obj.save()
            messages.success(request, f'OS {os_obj.numero} aprovada!')
            # Notifica o responsável pela execução via push
            if os_obj.responsavel_id:
                _enviar_push_os(os_obj.responsavel, os_obj)
        return redirect('operacoes_campo:os_detail', pk=pk)

    return redirect('operacoes_campo:os_detail', pk=pk)


@login_required
def os_aprovar_plantio(request, pk):
    """
    Aprova uma OS de Plantio (ABERTA → APROVADA) exigindo o IDIARN — número
    de controle obrigatório do ciclo, emitido por órgão externo. Segue o
    mesmo padrão de modal usado em `os_horimetro_pendente`.
    """
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    template = 'cadastros/os/os_aprovar_plantio_form.html'

    if request.method == 'POST':
        if os_obj.status != 'ABERTA':
            return JsonResponse({'success': False, 'error': 'Somente OS abertas podem ser aprovadas.'})

        idiarn = (request.POST.get('idiarn') or '').strip()
        if not idiarn:
            return render(request, template, {'os': os_obj, 'erro': 'Informe o IDIARN para aprovar a OS de plantio.'})
        try:
            idiarn_validator(idiarn)
        except ValidationError as e:
            return render(request, template, {'os': os_obj, 'erro': '; '.join(e.messages)})

        os_obj.idiarn = idiarn
        os_obj.status = 'APROVADA'
        os_obj.aprovador = request.user
        os_obj.data_aprovacao = timezone.now()
        os_obj.save()

        if os_obj.responsavel_id:
            _enviar_push_os(os_obj.responsavel, os_obj)

        return JsonResponse({'success': True, 'redirect': reverse('operacoes_campo:os_detail', args=[pk])})

    return render(request, template, {'os': os_obj})


@login_required
def os_iniciar(request, pk):
    """Inicia a execução (APROVADA → EM_ANDAMENTO)"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if os_obj.status != 'APROVADA':
            messages.error(request, 'Somente OS aprovadas podem ser iniciadas.')
        else:
            tipo_legado = os_obj.tipo_legado_efetivo

            if tipo_legado == 'PLANTIO':
                if not os_obj.safra_id:
                    messages.error(request, 'Para iniciar uma OS de plantio, selecione a safra vinculada.')
                    return redirect('operacoes_campo:os_detail', pk=pk)

                if not os_obj.safra_cultura_id:
                    messages.error(request, 'Selecione a cultura da safra para iniciar o plantio.')
                    return redirect('operacoes_campo:os_detail', pk=pk)

                subtipo_legado = os_obj.subtipo_servico.subtipo_legado if os_obj.subtipo_servico_id else ''
                transplantio = getattr(os_obj, 'transplantio', None)
                if subtipo_legado == SUBTIPO_LEGADO_TRANSPLANTE and transplantio:
                    if transplantio.quantidade_transplantada > transplantio.lote_muda.quantidade_disponivel:
                        messages.error(
                            request,
                            f'O lote {transplantio.lote_muda.codigo_lote} não tem mais '
                            f'{transplantio.quantidade_transplantada} mudas disponíveis — outra OS pode '
                            'ter consumido o saldo enquanto esta ficava em aberto. Ajuste a quantidade '
                            'do transplantio antes de iniciar.'
                        )
                        return redirect('operacoes_campo:os_detail', pk=pk)

            os_obj.status = 'EM_ANDAMENTO'
            os_obj.data_inicio = timezone.now()
            os_obj.save()

            # Aviso não-bloqueante: máquinas sem horímetro inicial
            maquinas_sem_hini = os_obj.maquinas_os.filter(horimetro_inicial__isnull=True)
            if maquinas_sem_hini.exists():
                nomes = ', '.join(str(m.veiculo) for m in maquinas_sem_hini)
                messages.warning(request, f'Registre o horímetro inicial: {nomes}')

            if tipo_legado == 'PLANTIO':
                try:
                    historico = os_obj.talhao.iniciar_cultivo(
                        cultura=os_obj.safra_cultura.cultura,
                        data_plantio=timezone.localdate(),
                        safra_cultura=os_obj.safra_cultura,
                        idiarn=os_obj.idiarn,
                    )
                except ValidationError as e:
                    os_obj.status = 'APROVADA'
                    os_obj.data_inicio = None
                    os_obj.save()
                    messages.error(request, '; '.join(e.messages) if hasattr(e, 'messages') else str(e))
                    return redirect('operacoes_campo:os_detail', pk=pk)
                if historico and not os_obj.historico_talhao_id:
                    os_obj.historico_talhao = historico
                    os_obj.save(update_fields=['historico_talhao'])
            messages.success(request, f'OS {os_obj.numero} iniciada!')
        return redirect('operacoes_campo:os_detail', pk=pk)

    return redirect('operacoes_campo:os_detail', pk=pk)


@login_required
def os_horimetro_pendente(request, pk):
    """
    Popup exibido ao encerrar a OS quando há veículos com horímetro
    inicial e/ou final não preenchidos, permitindo completá-los antes
    de seguir para a tela de conclusão.
    """
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    maquinas = os_obj.maquinas_os.select_related('veiculo').all()
    template = 'cadastros/os/os_horimetro_pendente_form.html'

    if request.method == 'POST':
        erro = None
        try:
            with transaction.atomic():
                for maquina in maquinas:
                    inicial_raw = request.POST.get(f'horimetro_inicial_{maquina.id}', '').strip()
                    final_raw = request.POST.get(f'horimetro_final_{maquina.id}', '').strip()
                    if not inicial_raw and not final_raw:
                        continue
                    if inicial_raw:
                        maquina.horimetro_inicial = Decimal(inicial_raw.replace(',', '.'))
                    if final_raw:
                        maquina.horimetro_final = Decimal(final_raw.replace(',', '.'))
                    maquina.full_clean()
                    maquina.save()
        except InvalidOperation:
            erro = 'Informe valores numéricos válidos para o horímetro.'
        except ValidationError as e:
            erro = '; '.join(e.messages) if hasattr(e, 'messages') else str(e)

        if erro:
            return render(request, template, {'os': os_obj, 'maquinas': maquinas, 'erro': erro})
        return JsonResponse({'success': True, 'redirect': reverse('operacoes_campo:os_concluir', args=[pk])})

    return render(request, template, {'os': os_obj, 'maquinas': maquinas})


@login_required
def os_concluir(request, pk):
    """
    Conclui uma OS (EM_ANDAMENTO → CONCLUIDA)
    RN-03: Exige foto de evidência
    Gera CustoTalhao automaticamente
    """
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if os_obj.status not in ('APROVADA', 'EM_ANDAMENTO'):
            messages.error(request, 'A OS não pode ser concluída no status atual.')
            return redirect('operacoes_campo:os_detail', pk=pk)

        foto = request.FILES.get('foto_evidencia')
        if not foto and not os_obj.foto_evidencia:
            messages.error(request, 'Evidência fotográfica é obrigatória para concluir a OS (RN-03).')
            return redirect('operacoes_campo:os_detail', pk=pk)

        # Bloqueia se alguma máquina tem horímetro inicial mas falta o final
        pendentes_hfim = os_obj.maquinas_os.filter(
            horimetro_inicial__isnull=False, horimetro_final__isnull=True
        )
        if pendentes_hfim.exists():
            nomes = ', '.join(str(m.veiculo) for m in pendentes_hfim)
            messages.error(request, f'Preencha o horímetro final antes de concluir: {nomes}')
            return redirect('operacoes_campo:os_detail', pk=pk)

        # Se houver insumos lançados na OS, exige ao menos uma quantidade aplicada > 0.
        insumos_os = os_obj.insumos_os.all()
        if insumos_os.exists() and not insumos_os.filter(quantidade_aplicada__gt=0).exists():
            messages.error(request, 'Informe quantidade aplicada maior que zero em ao menos um item de insumo.')
            return redirect('operacoes_campo:os_detail', pk=pk)

        # Validação de saldo por produto (somando todos os itens aplicados da OS).
        consumo_por_produto = {}
        for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto'):
            produto_id = item.produto_id
            consumo_por_produto[produto_id] = consumo_por_produto.get(produto_id, Decimal('0')) + (item.quantidade_aplicada or Decimal('0'))

        from estoque.disponibilidade import reservas_por_produto

        reservas = reservas_por_produto(empresa, excluir_os_id=os_obj.id)
        produtos_sem_saldo = []
        produtos_validados = set()
        for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto'):
            if item.produto_id in produtos_validados:
                continue
            produtos_validados.add(item.produto_id)
            disponivel = Decimal(item.produto.estoque_atual or 0) - reservas.get(item.produto_id, Decimal('0'))
            consumo = consumo_por_produto.get(item.produto_id, Decimal('0'))
            if disponivel < consumo:
                produtos_sem_saldo.append(
                    f"{item.produto.nome} (disponível: {disponivel}, necessário: {consumo})"
                )

        if produtos_sem_saldo:
            messages.error(
                request,
                'Saldo insuficiente para concluir a OS. Ajuste os itens: ' + '; '.join(sorted(set(produtos_sem_saldo)))
            )
            return redirect('operacoes_campo:os_detail', pk=pk)

        try:
            with transaction.atomic():
                if foto:
                    os_obj.foto_evidencia = foto

                # Gera a movimentação de saída dos itens aplicados na OS como PENDENTE.
                # A baixa efetiva do estoque é feita manualmente pelo responsável do
                # almoxarifado (tela de Movimentações de Estoque > Executar).
                for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto', 'unidade_medida'):
                    movimentacao = MovimentacaoEstoque.objects.create(
                        tipo='SAIDA',
                        origem='OS_DIRETA',
                        status='PENDENTE',
                        empresa=empresa,
                        produto=item.produto,
                        unidade_medida=item.unidade_medida,
                        quantidade=item.quantidade_aplicada,
                        documento=os_obj.numero,
                        requisitante=os_obj.solicitante,
                        aprovador=os_obj.aprovador,
                        data_movimentacao=timezone.now(),
                        observacao=f'OS {os_obj.numero} - Item: {item.produto.nome}'
                    )
                    item.movimentacao = movimentacao
                    item.save(update_fields=['movimentacao'])

                agora_conclusao = timezone.now()
                agora_local = timezone.localtime(agora_conclusao)

                # Fecha todos os OSIntervalo abertos
                os_obj.intervalos.filter(fim__isnull=True).update(fim=agora_conclusao)

                # Backfill hora_inicio para trabalhadores sem horário de entrada
                data_inicio = os_obj.data_inicio or agora_conclusao
                data_inicio_local = timezone.localtime(data_inicio)
                os_obj.funcionarios_os.filter(hora_inicio__isnull=True).update(
                    hora_inicio=data_inicio_local.time(),
                    data_execucao=data_inicio_local.date(),
                )

                # Backfill hora_fim para todos os trabalhadores sem horário de saída
                os_obj.funcionarios_os.filter(hora_fim__isnull=True).update(
                    hora_fim=agora_local.time(),
                )

                # Backfill data_execucao das máquinas sem data
                os_obj.maquinas_os.filter(data_execucao__isnull=True).update(
                    data_execucao=data_inicio_local.date()
                )

                os_obj.status = 'CONCLUIDA'
                os_obj.data_fim = agora_conclusao
                os_obj.save()

                # Gera / atualiza CustoTalhao
                custo_obj, _ = CustoTalhao.objects.get_or_create(
                    os=os_obj,
                    defaults={
                        'empresa': empresa,
                        'talhao': os_obj.talhao,
                        'safra': os_obj.safra,
                    }
                )
                custo_obj.recalcular()

                # Transplantio: só consome o lote de mudas quando a OS é efetivamente concluída
                transplantio_obj = getattr(os_obj, 'transplantio', None)
                if transplantio_obj:
                    transplantio_obj.marcar_lote_se_esgotado()

                # Integração automática: Caderno de Campo
                if request.POST.get('criar_registro_caderno'):
                    from operacoes_campo.models import RegistroCadernoCampo, RegistroCadernoCampoInsumo
                    _TIPO_MAP = {
                        'PREPARO_SOLO': 'PREPARO_SOLO',
                        'PLANTIO': 'PLANTIO',
                        'IRRIGACAO': 'IRRIGACAO',
                        'ADUBACAO': 'ADUBACAO',
                        'PULV_MECANICA': 'APLICACAO_DEFENSIVO',
                        'PULV_COSTAL': 'APLICACAO_DEFENSIVO',
                        'COLHEITA': 'COLHEITA',
                        'MANUTENCAO': 'MANUTENCAO',
                    }
                    _tl = ''
                    if os_obj.tipo_servico_id:
                        _tl = os_obj.tipo_servico.tipo_legado or ''
                    elif os_obj.tipo:
                        _tl = os_obj.tipo
                    tipo_atividade_caderno = _TIPO_MAP.get(_tl, 'OUTRO')

                    if not RegistroCadernoCampo.objects.filter(os=os_obj).exists():
                        registro = RegistroCadernoCampo.objects.create(
                            empresa=empresa,
                            talhao=os_obj.talhao,
                            safra=os_obj.safra,
                            os=os_obj,
                            data_atividade=timezone.localdate(),
                            tipo_atividade=tipo_atividade_caderno,
                            atividade=os_obj.descricao_servico,
                            responsavel=request.user,
                            cadastrado_por=request.user,
                            observacoes=os_obj.observacoes or '',
                        )
                        from produtos.models import ProdutoDefensivoCultura
                        cultura_caderno = cultura_atual_talhao(os_obj.talhao, os_obj.safra)
                        for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto', 'unidade_medida', 'praga'):
                            carencia_dias = None
                            if item.praga_id and cultura_caderno:
                                dc = ProdutoDefensivoCultura.objects.filter(
                                    produto=item.produto, cultura=cultura_caderno, praga=item.praga,
                                ).first()
                                if dc:
                                    carencia_dias = dc.carencia
                            receituario_aprovado = item.receituarios.filter(status='APROVADO').order_by('-id').first()
                            RegistroCadernoCampoInsumo.objects.create(
                                registro=registro,
                                produto=item.produto,
                                praga=item.praga,
                                quantidade=item.quantidade_aplicada,
                                unidade_medida=item.unidade_medida,
                                carencia_dias=carencia_dias,
                                receituario_numero=receituario_aprovado.numero if receituario_aprovado else '',
                            )

        except Exception as e:
            messages.error(request, f'Erro ao concluir OS: {str(e)}')
            return redirect('operacoes_campo:os_detail', pk=pk)

        _msg = f'OS {os_obj.numero} concluída! Custo total: R$ {custo_obj.custo_total:.2f}'
        if request.POST.get('criar_registro_caderno'):
            _msg += ' · Registro criado no Caderno de Campo.'
        if insumos_os.filter(quantidade_aplicada__gt=0).exists():
            _msg += ' · Insumos aguardando baixa pelo almoxarifado (Estoque > Movimentações).'
        messages.success(request, _msg)

        pendentes = [
            item.produto.nome
            for item in insumos_os.filter(praga__isnull=False).select_related('produto')
            if not item.receituarios.filter(status='APROVADO').exists()
        ]
        if pendentes:
            messages.warning(
                request,
                'Atenção: os seguintes defensivos foram aplicados sem um Receituário Agronômico aprovado — '
                'emita e aprove o receituário para manter o registro completo: ' + ', '.join(pendentes)
            )
        return redirect('operacoes_campo:os_detail', pk=pk)

    context = {'os': os_obj}
    return render(request, 'cadastros/os/os_concluir.html', context)


# ============================================================================
# CUSTO/HORA DE MÁQUINAS
# ============================================================================

@login_required
def custo_maquina_list(request):
    """Lista configurações de custo/hora de máquinas"""
    empresa = request.user.empresa
    configs = CustoHoraMaquina.objects.filter(empresa=empresa).select_related('veiculo').order_by(
        '-data_referencia'
    )
    context = {'configs': configs}
    return render(request, 'cadastros/os/custo_maquina_list.html', context)


@login_required
def custo_maquina_create(request):
    """Cria nova configuração de custo/hora"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = CustoHoraMaquinaForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.cadastrado_por = request.user
            obj.save()
            messages.success(request, 'Configuração de custo/hora criada com sucesso!')
            return redirect('operacoes_campo:custo_maquina_list')
    else:
        form = CustoHoraMaquinaForm(empresa=empresa)

    context = {'form': form, 'titulo': 'Nova Configuração de Custo/Hora', 'action': 'Criar'}
    return render(request, 'cadastros/os/custo_maquina_form.html', context)


@login_required
def custo_maquina_update(request, pk):
    """Edita configuração de custo/hora"""
    empresa = request.user.empresa
    obj = get_object_or_404(CustoHoraMaquina, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = CustoHoraMaquinaForm(request.POST, instance=obj, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configuração atualizada com sucesso!')
            return redirect('operacoes_campo:custo_maquina_list')
    else:
        form = CustoHoraMaquinaForm(instance=obj, empresa=empresa)

    context = {'form': form, 'obj': obj, 'titulo': 'Editar Configuração de Custo/Hora', 'action': 'Salvar'}
    return render(request, 'cadastros/os/custo_maquina_form.html', context)


# ============================================================================
# AJAX: CLASSIFICAÇÃO ESTRUTURADA DE OS
# ============================================================================

@login_required
def ajax_opcoes_servico(request):
    """
    Retorna subtípos e modalidades para um tipo de serviço selecionado.
    Usado na tela de criação/edição de OS para população dinâmica dos combos.
    GET ?tipo_id=<id>
    """
    empresa = request.user.empresa
    tipo_id = request.GET.get('tipo_id')

    if not tipo_id:
        return JsonResponse({'subtipos': [], 'modalidades': [], 'tipo_legado': ''})

    try:
        tipo = TipoServicoOS.objects.get(pk=tipo_id)
    except TipoServicoOS.DoesNotExist:
        return JsonResponse({'subtipos': [], 'modalidades': [], 'tipo_legado': ''})

    # Verifica que o tipo pertence à empresa ou é global
    if tipo.empresa_id and tipo.empresa_id != empresa.pk:
        return JsonResponse({'subtipos': [], 'modalidades': [], 'tipo_legado': ''})

    subtipos = list(
        SubtipoServicoOS.objects.filter(
            tipo_servico=tipo, ativo=True
        ).filter(
            Q(empresa=empresa) | Q(empresa=None)
        ).order_by('ordem', 'nome').values('id', 'nome', 'subtipo_legado')
    )

    modalidades = list(
        ModalidadeExecucaoOS.objects.filter(
            ativo=True
        ).filter(
            Q(empresa=empresa) | Q(empresa=None)
        ).order_by('ordem', 'nome').values('id', 'nome')
    )

    return JsonResponse({'subtipos': subtipos, 'modalidades': modalidades, 'tipo_legado': tipo.tipo_legado or ''})


@login_required
def ajax_opcoes_talhao(request):
    """
    Retorna safras vinculadas a um talhão e sua cultura atual.
    Usado na tela de criação/edição de OS para auto-preenchimento.
    GET ?talhao_id=<id>
    """
    empresa = request.user.empresa
    talhao_id = request.GET.get('talhao_id')

    if not talhao_id:
        return JsonResponse({'safras': [], 'cultura': None})

    try:
        talhao = Talhao.objects.select_related('cultura_atual').get(pk=talhao_id, empresa=empresa)
    except Talhao.DoesNotExist:
        return JsonResponse({'safras': [], 'cultura': None})

    # Um talhão pertence a no máximo 1 cultura ativa por safra (atribuição feita no
    # cadastro da safra) — cada SafraCultura aqui já corresponde à safra + cultura certas.
    culturas_ativas = list(talhao.culturas_safra.filter(
        safra__fazenda__empresa=empresa,
        status__in=['PLANEJADA', 'EM_ANDAMENTO']
    ).select_related('safra', 'cultura').order_by('-safra__ano', 'safra__nome'))

    safras = [
        {
            'id': sc.safra_id,
            'nome': sc.safra.nome_display,
            'ano': sc.safra.ano,
            'culturas': [{'id': sc.id, 'cultura_id': sc.cultura_id, 'nome': sc.cultura.nome}],
        }
        for sc in culturas_ativas
    ]

    # Cultura: campo direto no talhão OU derivada da (única) cultura da safra mais recente
    cultura = None
    if talhao.cultura_atual_id:
        cultura = {'id': talhao.cultura_atual_id, 'nome': talhao.cultura_atual.nome}
    elif culturas_ativas:
        cultura = {'id': culturas_ativas[0].cultura_id, 'nome': culturas_ativas[0].cultura.nome}

    return JsonResponse({
        'safras': safras,
        'cultura': cultura,
        'area_hac': str(talhao.area_hac),
    })


@login_required
def ajax_culturas_por_safra(request):
    """
    Retorna as culturas (SafraCultura) atribuídas a uma safra, independente de talhão.
    Usado na tela de OS quando o usuário escolhe a Safra diretamente (sem ter
    selecionado um Talhão ainda) — mostra todas as culturas da safra, não só a
    que porventura já esteja associada a algum talhão específico.
    GET ?safra_id=<id>
    """
    empresa = request.user.empresa
    safra_id = request.GET.get('safra_id')

    if not safra_id:
        return JsonResponse({'culturas': []})

    culturas = list(
        SafraCultura.objects.filter(
            safra_id=safra_id, safra__fazenda__empresa=empresa,
            status__in=['PLANEJADA', 'EM_ANDAMENTO'],
        ).select_related('cultura').order_by('cultura__nome')
    )
    return JsonResponse({
        'culturas': [{'id': sc.id, 'cultura_id': sc.cultura_id, 'nome': sc.cultura.nome} for sc in culturas]
    })


@login_required
def ajax_talhoes_por_safra_cultura(request):
    """
    Retorna os talhões atribuídos a uma SafraCultura (definidos no cadastro da safra).
    Usado na tela de OS para sugerir/filtrar o campo Talhão ao escolher a cultura da safra.
    GET ?safra_cultura_id=<id>
    """
    empresa = request.user.empresa
    safra_cultura_id = request.GET.get('safra_cultura_id')

    if not safra_cultura_id:
        return JsonResponse({'talhoes': []})

    try:
        sc = SafraCultura.objects.select_related('safra').get(
            pk=safra_cultura_id, safra__fazenda__empresa=empresa
        )
    except SafraCultura.DoesNotExist:
        return JsonResponse({'talhoes': []})

    talhoes = list(sc.talhoes.filter(ativo=True).values('id', 'nome', 'codigo').order_by('codigo'))
    return JsonResponse({'talhoes': talhoes})


@login_required
def ajax_numero_corte(request):
    """
    Prévia do próximo Número do Corte para uma OS de Colheita: conta as OS de
    Colheita já registradas para o talhão (e safra, se informada) e retorna
    contagem + 1. O valor final é sempre recalculado no servidor ao salvar
    (OrdemServicoForm.clean); este endpoint só alimenta o preview em tela.
    GET ?talhao_id=<id>&safra_id=<id opcional>&os_id=<id opcional, para edição>
    """
    empresa = request.user.empresa
    talhao_id = request.GET.get('talhao_id')
    safra_id = request.GET.get('safra_id')
    os_id = request.GET.get('os_id')

    if not talhao_id:
        return JsonResponse({'numero_corte': None})

    try:
        talhao = Talhao.objects.get(pk=talhao_id, empresa=empresa)
    except Talhao.DoesNotExist:
        return JsonResponse({'numero_corte': None})

    safra = None
    if safra_id:
        safra = Safra.objects.filter(pk=safra_id, fazenda__empresa=empresa).first()

    numero_corte = proximo_numero_corte(talhao, safra, excluir_pk=os_id or None)
    return JsonResponse({'numero_corte': numero_corte})


@login_required
def ajax_produto_info(request):
    """GET ?produto_id=X — retorna unidade_medida e preco_custo para auto-fill no insumo da OS."""
    produto_id = request.GET.get('produto_id')
    empresa = request.user.empresa
    if not produto_id:
        return JsonResponse({'error': 'produto_id required'}, status=400)
    try:
        from produtos.models import Produto
        produto = (
            Produto.objects
            .select_related('unidade_medida')
            .filter(pk=produto_id, lotes__armazem__empresa=empresa)
            .first()
        )
        if not produto:
            return JsonResponse({'error': 'not found'}, status=404)
        return JsonResponse({
            'unidade_medida_id': produto.unidade_medida_id,
            'unidade_medida_sigla': produto.unidade_medida.sigla if produto.unidade_medida else '',
            'preco_custo': str(produto.preco_custo or '0'),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def ajax_recomendacao_defensivo(request):
    """GET ?praga_id=X&os_id=Y — retorna, ranqueados, os defensivos cadastrados
    (ProdutoDefensivoCultura) para a praga/cultura da OS, com dose sugerida
    (dosagem da bula × área executada) e alerta se o produto for proibido em
    algum país de destino cadastrado na cultura da safra. Só sugere produtos
    com lote em estoque — mesmo critério do campo `produto` do formulário de
    insumo, para não recomendar algo que o form depois rejeita."""
    from produtos.models import ProdutoDefensivoCultura

    empresa = request.user.empresa
    praga_id = request.GET.get('praga_id')
    os_id = request.GET.get('os_id')
    if not praga_id or not os_id:
        return JsonResponse({'error': 'praga_id e os_id são obrigatórios'}, status=400)

    from cadastros.models import Praga
    praga = get_object_or_404(Praga, pk=praga_id, empresa=empresa)
    os_obj = get_object_or_404(OrdemServico, pk=os_id, empresa=empresa)

    cultura = cultura_atual_talhao(os_obj.talhao, os_obj.safra)
    if not cultura:
        return JsonResponse({'sem_cultura': True, 'recomendacoes': []})

    area = os_obj.area_executada_ha or os_obj.talhao.area_hac or Decimal('0')
    paises_destino = set()
    if os_obj.safra_id:
        safra_cultura = os_obj.safra.culturas.filter(cultura=cultura).first()
        if safra_cultura:
            paises_destino = {p.lower() for p in safra_cultura.get_paises_destino_list()}

    qs = (
        ProdutoDefensivoCultura.objects
        .filter(
            praga=praga, cultura=cultura, produto__categoria__empresa=empresa, produto__ativo=True,
            produto__lotes__armazem__empresa=empresa,
        )
        .distinct()
        .select_related('produto', 'unidade_dosagem')
        .order_by('ordem_recomendacao', '-efetividade_pct')
    )

    recomendacoes = []
    for item in qs:
        dose_media = (item.dosagem_minima + item.dosagem_maxima) / 2
        quantidade_sugerida = (dose_media * area).quantize(Decimal('0.001')) if area else None

        paises_proibidos = item.produto.get_paises_proibidos_list()
        alerta_pais = next(
            (pp for pp in paises_proibidos if pp.lower() in paises_destino),
            None,
        )

        recomendacoes.append({
            'produto_id': item.produto_id,
            'produto_nome': item.produto.nome,
            'ordem': item.ordem_recomendacao,
            'efetividade_pct': item.efetividade_pct,
            'custo_relativo': item.custo_relativo,
            'dosagem_minima': str(item.dosagem_minima),
            'dosagem_maxima': str(item.dosagem_maxima),
            'unidade_dosagem_id': item.unidade_dosagem_id,
            'unidade_dosagem_sigla': item.unidade_dosagem.sigla if item.unidade_dosagem else '',
            'carencia': item.carencia,
            'quantidade_sugerida': str(quantidade_sugerida) if quantidade_sugerida is not None else None,
            'alerta_pais_proibido': alerta_pais,
        })

    sem_estoque = False
    if not recomendacoes:
        sem_estoque = ProdutoDefensivoCultura.objects.filter(
            praga=praga, cultura=cultura, produto__categoria__empresa=empresa, produto__ativo=True,
        ).exists()

    return JsonResponse({
        'sem_cultura': False,
        'area_referencia': str(area),
        'recomendacoes': recomendacoes,
        'sem_estoque': sem_estoque,
    })


# ============================================================================
# PAINEL DE DELEGAÇÃO
# ============================================================================

@login_required
def os_painel_delegacao(request):
    """Kanban de delegação: atribui OS a funcionários com portal ativo."""
    from rh.models import Funcionario

    empresa = request.user.empresa
    qs = OrdemServico.objects.filter(
        empresa=empresa
    ).exclude(status='CANCELADA').select_related(
        'talhao', 'safra', 'responsavel', 'tipo_servico'
    ).order_by('data_prevista', '-data_cadastro')

    # Filtros opcionais
    funcionario_filter = request.GET.get('funcionario')
    safra_filter = request.GET.get('safra')
    if funcionario_filter:
        qs = qs.filter(responsavel_id=funcionario_filter)
    if safra_filter:
        qs = qs.filter(safra_id=safra_filter)

    funcionarios = Funcionario.objects.filter(
        empresa=empresa, ativo=True, portal_ativo=True
    ).order_by('nome_completo')
    safras = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')

    grupos = {
        'nao_atribuidas': [o for o in qs if not o.responsavel_id and o.status == 'ABERTA'],
        'aguardando':     [o for o in qs if o.responsavel_id and o.status in ('ABERTA', 'APROVADA')],
        'em_andamento':   [o for o in qs if o.status == 'EM_ANDAMENTO'],
        'concluidas':     [o for o in qs if o.status == 'CONCLUIDA'],
    }

    return render(request, 'cadastros/os/os_delegacao.html', {
        'grupos': grupos,
        'funcionarios': funcionarios,
        'safras': safras,
        'funcionario_filter': funcionario_filter or '',
        'safra_filter': safra_filter or '',
    })


@login_required
@require_POST
def os_atribuir_responsavel(request, pk):
    """AJAX: atribui responsável a uma OS e dispara push notification se configurado."""
    from rh.models import Funcionario
    from operacoes_campo.models import PushSubscriptionCampo

    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    funcionario_id = request.POST.get('funcionario_id')
    antigo_responsavel = os_obj.responsavel

    if funcionario_id:
        try:
            func = Funcionario.objects.get(pk=funcionario_id, empresa=empresa, ativo=True)
            os_obj.responsavel = func
            if os_obj.status == 'ABERTA':
                os_obj.status = 'APROVADA'
                os_obj.data_aprovacao = timezone.now()
                os_obj.aprovador = request.user
                os_obj.save(update_fields=['responsavel', 'status', 'data_aprovacao', 'aprovador'])
            else:
                os_obj.save(update_fields=['responsavel'])

            # Disparar push notification para o novo responsável
            _enviar_push_os(func, os_obj)

            return JsonResponse({'ok': True, 'responsavel': func.nome_completo, 'status': os_obj.status})
        except Funcionario.DoesNotExist:
            return JsonResponse({'ok': False, 'error': 'Funcionário não encontrado'}, status=404)
    else:
        os_obj.responsavel = None
        os_obj.save(update_fields=['responsavel'])
        return JsonResponse({'ok': True, 'responsavel': None, 'status': os_obj.status})


def _enviar_push_os(funcionario, os_obj):
    """Envia push notification Web Push para o funcionário delegado."""
    from django.conf import settings
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return

    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_email = getattr(settings, 'VAPID_EMAIL', '')
    if not private_key:
        return

    subs = PushSubscriptionCampo.objects.filter(funcionario=funcionario, ativo=True)
    payload = json.dumps({
        'title': f'Nova OS: {os_obj.numero}',
        'body': f'{os_obj.descricao_servico} — {os_obj.talhao.nome}',
        'url': f'/portal/campo/os/{os_obj.pk}/',
    })

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={'sub': vapid_email},
            )
        except Exception:
            sub.ativo = False
            sub.save(update_fields=['ativo'])
