"""
Views para o módulo de Ordens de Serviço Agrícolas
RF-105: Ordens de serviço — plantio, irrigação, aplicação, colheita
RF-115: Controle de custos por talhão e safra
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from decimal import Decimal

from .models import (
    OrdemServico, OrdemServicoInsumo, CustoTalhao, CustoHoraMaquina,
    Talhao, Safra, TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS,
    EtapaColheita,
)
from .forms import (
    OrdemServicoForm, OSFuncionarioFormSet, OSMaquinaFormSet,
    OrdemServicoInsumoForm, CustoHoraMaquinaForm,
)
from estoque.models import MovimentacaoEstoque


def _sort_key(item, key):
    value = item.get(key)
    if value is None:
        return Decimal('0') if key.startswith('total_') or key == 'custo_medio_ha' else ''
    return value


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
    tipos_servico = TipoServicoOS.objects.filter(
        Q(empresa=empresa) | Q(empresa=None), ativo=True
    ).order_by('ordem', 'nome')

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
            total_area=Sum('area_executada_ha'),
        ).order_by('talhao__nome')
    )

    for item in consolidado_talhoes:
        total_item = (
            (item.get('total_mao_obra') or Decimal('0')) +
            (item.get('total_maquinario') or Decimal('0')) +
            (item.get('total_insumos') or Decimal('0')) +
            (item.get('total_servico') or Decimal('0'))
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
            total_area=Sum('area_executada_ha'),
        ).order_by('safra__ano', 'safra__nome')
    )

    for item in consolidado_safras:
        total_item = (
            (item.get('total_mao_obra') or Decimal('0')) +
            (item.get('total_maquinario') or Decimal('0')) +
            (item.get('total_insumos') or Decimal('0')) +
            (item.get('total_servico') or Decimal('0'))
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
        total_area=Sum('area_executada_ha'),
    )

    total_geral = (
        (resumo.get('total_mao_obra') or Decimal('0')) +
        (resumo.get('total_maquinario') or Decimal('0')) +
        (resumo.get('total_insumos') or Decimal('0')) +
        (resumo.get('total_servico') or Decimal('0'))
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
    resumo_doughnut = json.dumps([
        float(sum(i.get('total_mao_obra') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_maquinario') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_insumos') or 0 for i in consolidado_talhoes)),
        float(sum(i.get('total_servico') or 0 for i in consolidado_talhoes)),
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

    headers = ['OS', 'Talhão', 'Safra', 'Área (ha)', 'Mão de Obra', 'Maquinário', 'Insumos', 'Serviço Externo', 'Total', 'R$/ha']
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
        ws.cell(row=row, column=9, value=float(item.custo_total or 0))
        ws.cell(row=row, column=10, value=float(item.custo_por_hectare or 0))
        for col in range(1, 11):
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

        # Limita querysets por empresa antes da validacao.
        _enrich_formset(func_formset, empresa)
        _enrich_formset(maq_formset, empresa)

        if form.is_valid() and func_formset.is_valid() and maq_formset.is_valid():
            os_obj = form.save(commit=False)
            os_obj.empresa = empresa
            os_obj.solicitante = request.user
            os_obj.cadastrado_por = request.user
            os_obj.save()

            func_formset.instance = os_obj
            func_formset.save()

            maq_formset.instance = os_obj
            maq_formset.save()

            messages.success(request, f'Ordem de Serviço {os_obj.numero} criada com sucesso!')
            return redirect('cadastros:os_detail', pk=os_obj.pk)
    else:
        form = OrdemServicoForm(empresa=empresa)
        func_formset = OSFuncionarioFormSet(prefix='func')
        maq_formset = OSMaquinaFormSet(prefix='maq')

    # Enrich formsets with empresa context for querysets
    _enrich_formset(func_formset, empresa)
    _enrich_formset(maq_formset, empresa)

    context = {
        'form': form,
        'func_formset': func_formset,
        'maq_formset': maq_formset,
        'titulo': 'Nova Ordem de Serviço',
        'action': 'Criar',
    }
    return render(request, 'cadastros/os/os_form.html', context)


def _enrich_formset(formset, empresa):
    """Reaplica empresa nos querysets dos formulários do formset"""
    for form in formset.forms:
        if hasattr(form, 'fields'):
            if 'funcionario' in form.fields:
                from .models import Funcionario
                form.fields['funcionario'].queryset = Funcionario.objects.filter(
                    empresa=empresa, ativo=True
                )
            if 'veiculo' in form.fields:
                from cadastros.models import Vehicle
                form.fields['veiculo'].queryset = Vehicle.objects.filter(empresa=empresa)
            if 'operador' in form.fields:
                from .models import Funcionario
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

    custo_mo = sum(f.custo_calculado for f in funcionarios)
    custo_maq = sum(m.custo_calculado for m in maquinas)
    custo_serv = os_obj.valor_servico_externo or Decimal('0')
    insumos_os = os_obj.insumos_os.select_related('produto', 'unidade_medida').all()

    # Custo de insumos (prioriza os itens diretos da OS)
    custo_ins = Decimal('0')
    if insumos_os.exists():
        custo_ins = sum((i.custo_total for i in insumos_os), Decimal('0'))
    elif os_obj.requisicao:
        for item in os_obj.requisicao.itens.all():
            if item.custo_estimado and item.quantidade_atendida:
                custo_ins += item.custo_estimado * item.quantidade_atendida

    custo_total = custo_mo + custo_maq + custo_ins + custo_serv
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
        from .models import EtapaColheita
        etapas_colheita = EtapaColheita.objects.filter(os=os_obj).order_by('numero_etapa')
        total_colheita_kg = sum((e.total_liquido_kg or Decimal('0')) for e in etapas_colheita)

    context = {
        'os': os_obj,
        'funcionarios': funcionarios,
        'maquinas': maquinas,
        'custo_mo': custo_mo,
        'custo_maq': custo_maq,
        'custo_ins': custo_ins,
        'custo_serv': custo_serv,
        'custo_total': custo_total,
        'custo_ha': custo_ha,
        'custo_talhao_obj': custo_talhao_obj,
        'insumos_os': insumos_os,
        'movimentacoes_os': movimentacoes_os,
        'tipo_legado': tipo_legado,
        'etapas_colheita': etapas_colheita,
        'total_colheita_kg': total_colheita_kg,
    }
    return render(request, 'cadastros/os/os_detail.html', context)


@login_required
def os_insumo_add(request, pk):
    """Adiciona um insumo diretamente na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível adicionar insumos em uma OS concluída ou cancelada.')
        return redirect('cadastros:os_detail', pk=pk)

    if request.method == 'POST':
        form = OrdemServicoInsumoForm(request.POST, empresa=empresa)
        if form.is_valid():
            item = form.save(commit=False)
            item.empresa = empresa
            item.os = os_obj
            item.save()
            messages.success(request, 'Insumo adicionado à OS com sucesso.')
            return redirect('cadastros:os_detail', pk=pk)
    else:
        form = OrdemServicoInsumoForm(empresa=empresa)

    return render(request, 'cadastros/os/os_insumo_form.html', {
        'os': os_obj,
        'form': form,
        'titulo': f'Adicionar insumo - {os_obj.numero}',
        'action': 'Adicionar',
    })


@login_required
def os_insumo_edit(request, pk, insumo_pk):
    """Edita um insumo lançado na OS."""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)
    insumo = get_object_or_404(OrdemServicoInsumo, pk=insumo_pk, os=os_obj, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar insumos em uma OS concluída ou cancelada.')
        return redirect('cadastros:os_detail', pk=pk)

    if request.method == 'POST':
        form = OrdemServicoInsumoForm(request.POST, instance=insumo, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Insumo da OS atualizado com sucesso.')
            return redirect('cadastros:os_detail', pk=pk)
    else:
        form = OrdemServicoInsumoForm(instance=insumo, empresa=empresa)

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
        return redirect('cadastros:os_detail', pk=pk)

    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo removido da OS com sucesso.')
        return redirect('cadastros:os_detail', pk=pk)

    return render(request, 'cadastros/os/os_insumo_confirm_delete.html', {
        'os': os_obj,
        'insumo': insumo,
    })


@login_required
def os_update(request, pk):
    """Edita uma Ordem de Serviço"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if os_obj.status in ('CONCLUIDA', 'CANCELADA'):
        messages.error(request, 'Não é possível editar uma OS concluída ou cancelada.')
        return redirect('cadastros:os_detail', pk=pk)

    if request.method == 'POST':
        form = OrdemServicoForm(request.POST, request.FILES, instance=os_obj, empresa=empresa)
        func_formset = OSFuncionarioFormSet(request.POST, instance=os_obj, prefix='func')
        maq_formset = OSMaquinaFormSet(request.POST, instance=os_obj, prefix='maq')

        if form.is_valid() and func_formset.is_valid() and maq_formset.is_valid():
            form.save()
            func_formset.save()
            maq_formset.save()
            messages.success(request, f'OS {os_obj.numero} atualizada com sucesso!')
            return redirect('cadastros:os_detail', pk=pk)
    else:
        form = OrdemServicoForm(instance=os_obj, empresa=empresa)
        func_formset = OSFuncionarioFormSet(instance=os_obj, prefix='func')
        maq_formset = OSMaquinaFormSet(instance=os_obj, prefix='maq')

    _enrich_formset(func_formset, empresa)
    _enrich_formset(maq_formset, empresa)

    context = {
        'form': form,
        'func_formset': func_formset,
        'maq_formset': maq_formset,
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
            return redirect('cadastros:os_detail', pk=pk)
        numero = os_obj.numero
        os_obj.delete()
        messages.success(request, f'OS {numero} excluída com sucesso.')
        return redirect('cadastros:os_list')

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
        else:
            os_obj.status = 'APROVADA'
            os_obj.aprovador = request.user
            os_obj.data_aprovacao = timezone.now()
            os_obj.save()
            messages.success(request, f'OS {os_obj.numero} aprovada!')
        return redirect('cadastros:os_detail', pk=pk)

    return redirect('cadastros:os_detail', pk=pk)


@login_required
def os_iniciar(request, pk):
    """Inicia a execução (APROVADA → EM_ANDAMENTO)"""
    empresa = request.user.empresa
    os_obj = get_object_or_404(OrdemServico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        if os_obj.status != 'APROVADA':
            messages.error(request, 'Somente OS aprovadas podem ser iniciadas.')
        else:
            tipo_legado = ''
            if os_obj.tipo_servico_id:
                tipo_legado = os_obj.tipo_servico.tipo_legado or ''
            elif os_obj.tipo:
                tipo_legado = os_obj.tipo

            if tipo_legado == 'PLANTIO':
                if not os_obj.safra_id:
                    messages.error(request, 'Para iniciar uma OS de plantio, selecione a safra vinculada.')
                    return redirect('cadastros:os_detail', pk=pk)

                if not os_obj.safra.cultura_id:
                    messages.error(request, 'A safra vinculada não possui cultura definida para iniciar o plantio.')
                    return redirect('cadastros:os_detail', pk=pk)

                talhao = os_obj.talhao
                cultura_safra = os_obj.safra.cultura
                if (
                    talhao.cultura_atual_id
                    and talhao.cultura_atual_id != cultura_safra.id
                    and talhao.status in ('PLANTADO', 'COLHEITA')
                ):
                    messages.error(
                        request,
                        f'O talhão já está com cultivo ativo de {talhao.cultura_atual.nome}. '
                        'Encerre o cultivo atual antes de iniciar um novo plantio.'
                    )
                    return redirect('cadastros:os_detail', pk=pk)

            os_obj.status = 'EM_ANDAMENTO'
            os_obj.data_inicio = timezone.now()
            os_obj.save()

            if tipo_legado == 'PLANTIO':
                os_obj.talhao.iniciar_cultivo(
                    cultura=os_obj.safra.cultura,
                    data_plantio=timezone.localdate(),
                )
            messages.success(request, f'OS {os_obj.numero} iniciada!')
        return redirect('cadastros:os_detail', pk=pk)

    return redirect('cadastros:os_detail', pk=pk)


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
            return redirect('cadastros:os_detail', pk=pk)

        foto = request.FILES.get('foto_evidencia')
        if not foto and not os_obj.foto_evidencia:
            messages.error(request, 'Evidência fotográfica é obrigatória para concluir a OS (RN-03).')
            return redirect('cadastros:os_detail', pk=pk)

        # Se houver insumos lançados na OS, exige ao menos uma quantidade aplicada > 0.
        insumos_os = os_obj.insumos_os.all()
        if insumos_os.exists() and not insumos_os.filter(quantidade_aplicada__gt=0).exists():
            messages.error(request, 'Informe quantidade aplicada maior que zero em ao menos um item de insumo.')
            return redirect('cadastros:os_detail', pk=pk)

        # Validação de saldo por produto (somando todos os itens aplicados da OS).
        consumo_por_produto = {}
        for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto'):
            produto_id = item.produto_id
            consumo_por_produto[produto_id] = consumo_por_produto.get(produto_id, Decimal('0')) + (item.quantidade_aplicada or Decimal('0'))

        produtos_sem_saldo = []
        for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto'):
            saldo = getattr(item.produto, 'estoque_atual', None)
            consumo = consumo_por_produto.get(item.produto_id, Decimal('0'))
            if saldo is not None and saldo < consumo:
                produtos_sem_saldo.append(
                    f"{item.produto.nome} (saldo: {saldo}, necessário: {consumo})"
                )

        if produtos_sem_saldo:
            messages.error(
                request,
                'Saldo insuficiente para concluir a OS. Ajuste os itens: ' + '; '.join(sorted(set(produtos_sem_saldo)))
            )
            return redirect('cadastros:os_detail', pk=pk)

        try:
            with transaction.atomic():
                if foto:
                    os_obj.foto_evidencia = foto

                # Baixa de estoque dos itens aplicados na OS.
                for item in insumos_os.filter(quantidade_aplicada__gt=0).select_related('produto', 'unidade_medida'):
                    MovimentacaoEstoque.objects.create(
                        tipo='SAIDA',
                        origem='OS_DIRETA',
                        status='EXECUTADO',
                        empresa=empresa,
                        produto=item.produto,
                        unidade_medida=item.unidade_medida,
                        quantidade=item.quantidade_aplicada,
                        documento=os_obj.numero,
                        requisitante=os_obj.solicitante,
                        aprovador=os_obj.aprovador,
                        executado_por=request.user,
                        data_movimentacao=timezone.now(),
                        data_execucao=timezone.now(),
                        observacao=f'OS {os_obj.numero} - Item: {item.produto.nome}'
                    )

                os_obj.status = 'CONCLUIDA'
                os_obj.data_fim = timezone.now()
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
        except Exception as e:
            messages.error(request, f'Erro ao concluir OS: {str(e)}')
            return redirect('cadastros:os_detail', pk=pk)

        messages.success(
            request,
            f'OS {os_obj.numero} concluída! Custo total: R$ {custo_obj.custo_total:.2f}'
        )
        return redirect('cadastros:os_detail', pk=pk)

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
            return redirect('cadastros:custo_maquina_list')
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
            return redirect('cadastros:custo_maquina_list')
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
        return JsonResponse({'subtipos': [], 'modalidades': []})

    try:
        tipo = TipoServicoOS.objects.get(pk=tipo_id)
    except TipoServicoOS.DoesNotExist:
        return JsonResponse({'subtipos': [], 'modalidades': []})

    # Verifica que o tipo pertence à empresa ou é global
    if tipo.empresa_id and tipo.empresa_id != empresa.pk:
        return JsonResponse({'subtipos': [], 'modalidades': []})

    subtipos = list(
        SubtipoServicoOS.objects.filter(
            tipo_servico=tipo, ativo=True
        ).filter(
            Q(empresa=empresa) | Q(empresa=None)
        ).order_by('ordem', 'nome').values('id', 'nome')
    )

    modalidades = list(
        ModalidadeExecucaoOS.objects.filter(
            ativo=True
        ).filter(
            Q(empresa=empresa) | Q(empresa=None)
        ).order_by('ordem', 'nome').values('id', 'nome')
    )

    return JsonResponse({'subtipos': subtipos, 'modalidades': modalidades})


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

    # Retorna apenas safras PLANEJADA ou EM_ANDAMENTO vinculadas a este talhão
    safras = list(
        talhao.safras.filter(
            fazenda__empresa=empresa,
            status__in=['PLANEJADA', 'EM_ANDAMENTO']
        ).order_by('-ano', 'nome').values('id', 'nome', 'ano', 'cultura__nome')
    )
    
    # Monta nome da safra no mesmo padrão do modelo Safra.__str__()
    for s in safras:
        if not s['nome']:
            s['nome'] = f"Safra {s['ano']} - {s['cultura__nome']}"

    # Retorna a cultura atual do talhão (se houver)
    cultura = None
    if talhao.cultura_atual:
        cultura = {'id': talhao.cultura_atual_id, 'nome': talhao.cultura_atual.nome}

    return JsonResponse({'safras': safras, 'cultura': cultura})
