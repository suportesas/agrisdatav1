"""Views do módulo Caderno de Campo Digital (RF-111)."""
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import (
    RegistroCadernoCampoForm,
    RegistroCadernoCampoFuncionarioForm,
    RegistroCadernoCampoInsumoForm,
)
from .models import (
    RegistroCadernoCampo, RegistroCadernoCampoFuncionario, RegistroCadernoCampoInsumo,
)
from cadastros.models import Talhao, Safra


@login_required
def caderno_campo_list(request):
    empresa = request.user.empresa
    qs = RegistroCadernoCampo.objects.filter(empresa=empresa).select_related(
        'talhao', 'safra', 'responsavel'
    )

    talhao_id = request.GET.get('talhao')
    safra_id = request.GET.get('safra')
    tipo = request.GET.get('tipo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if talhao_id:
        qs = qs.filter(talhao_id=talhao_id)
    if safra_id:
        qs = qs.filter(safra_id=safra_id)
    if tipo:
        qs = qs.filter(tipo_atividade=tipo)
    if data_inicio:
        qs = qs.filter(data_atividade__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_atividade__lte=data_fim)

    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True)
    safras = Safra.objects.filter(fazenda__empresa=empresa)

    total = qs.count()
    paginator = Paginator(qs.order_by('-data_atividade'), 20)
    page = request.GET.get('page', 1)
    try:
        registros_page = paginator.page(page)
    except Exception:
        registros_page = paginator.page(1)

    context = {
        'registros': registros_page,
        'talhoes': talhoes,
        'safras': safras,
        'talhao_selecionado': talhao_id,
        'safra_selecionada': safra_id,
        'tipo_selecionado': tipo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'tipo_choices': RegistroCadernoCampo.TIPO_ATIVIDADE_CHOICES,
        'total': total,
        'title': 'Caderno de Campo',
    }
    return render(request, 'cadastros/caderno_campo/caderno_campo_list.html', context)


@login_required
def caderno_campo_create(request):
    if request.method == 'POST':
        form = RegistroCadernoCampoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = request.user.empresa
            obj.cadastrado_por = request.user
            obj.save()
            messages.success(request, 'Registro do caderno de campo criado com sucesso.')
            return redirect('operacoes_campo:caderno_campo_detail', pk=obj.pk)
    else:
        form = RegistroCadernoCampoForm(user=request.user)
    return render(request, 'cadastros/caderno_campo/caderno_campo_form.html', {
        'form': form,
        'title': 'Novo Registro — Caderno de Campo',
    })


@login_required
def caderno_campo_detail(request, pk):
    obj = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    insumo_form = RegistroCadernoCampoInsumoForm(empresa=request.user.empresa)
    func_form = RegistroCadernoCampoFuncionarioForm(user=request.user)
    return render(request, 'cadastros/caderno_campo/caderno_campo_detail.html', {
        'obj': obj,
        'insumo_form': insumo_form,
        'func_form': func_form,
        'title': f'Caderno — {obj.talhao.nome} — {obj.data_atividade.strftime("%d/%m/%Y")}',
    })


@login_required
def caderno_campo_update(request, pk):
    obj = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = RegistroCadernoCampoForm(request.POST, request.FILES, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registro atualizado com sucesso.')
            return redirect('operacoes_campo:caderno_campo_detail', pk=obj.pk)
    else:
        form = RegistroCadernoCampoForm(instance=obj, user=request.user)
    return render(request, 'cadastros/caderno_campo/caderno_campo_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Registro — Caderno de Campo',
    })


@login_required
def caderno_campo_delete(request, pk):
    obj = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Registro excluído.')
        return redirect('operacoes_campo:caderno_campo_list')
    return render(request, 'cadastros/caderno_campo/caderno_campo_confirm_delete.html', {'obj': obj})


@login_required
def caderno_campo_insumo_add(request, pk):
    registro = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = RegistroCadernoCampoInsumoForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            insumo = form.save(commit=False)
            insumo.registro = registro
            insumo.save()
            if is_ajax:
                html = render_to_string(
                    'cadastros/caderno_campo/_insumo_row.html',
                    {'insumo': insumo, 'registro': registro},
                    request=request,
                )
                return JsonResponse({'html': html, 'ok': True})
            messages.success(request, 'Insumo adicionado.')
        else:
            if is_ajax:
                return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
            messages.error(request, 'Erro ao adicionar insumo.')
    return redirect('operacoes_campo:caderno_campo_detail', pk=pk)


@login_required
def caderno_campo_insumo_delete(request, pk, insumo_pk):
    registro = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    insumo = get_object_or_404(RegistroCadernoCampoInsumo, pk=insumo_pk, registro=registro)
    if request.method == 'POST':
        insumo.delete()
        messages.success(request, 'Insumo removido.')
    return redirect('operacoes_campo:caderno_campo_detail', pk=pk)


@login_required
def caderno_campo_funcionario_add(request, pk):
    registro = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = RegistroCadernoCampoFuncionarioForm(request.POST, user=request.user)
        if form.is_valid():
            func = form.save(commit=False)
            func.registro = registro
            try:
                func.save()
                messages.success(request, 'Funcionário adicionado.')
            except Exception:
                messages.error(request, 'Este funcionário já está vinculado a este registro.')
        else:
            messages.error(request, 'Erro ao adicionar funcionário.')
    return redirect('operacoes_campo:caderno_campo_detail', pk=pk)


@login_required
def caderno_campo_funcionario_delete(request, pk, func_pk):
    registro = get_object_or_404(RegistroCadernoCampo, pk=pk, empresa=request.user.empresa)
    func = get_object_or_404(RegistroCadernoCampoFuncionario, pk=func_pk, registro=registro)
    if request.method == 'POST':
        func.delete()
        messages.success(request, 'Funcionário removido.')
    return redirect('operacoes_campo:caderno_campo_detail', pk=pk)


@login_required
def caderno_campo_pdf(request):
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph, PageBreak

    empresa = request.user.empresa
    qs = RegistroCadernoCampo.objects.filter(empresa=empresa).select_related(
        'talhao', 'safra', 'responsavel'
    ).prefetch_related('insumos_utilizados__produto', 'insumos_utilizados__unidade_medida')

    talhao_id = request.GET.get('talhao')
    safra_id = request.GET.get('safra')
    if talhao_id:
        qs = qs.filter(talhao_id=talhao_id)
    if safra_id:
        qs = qs.filter(safra_id=safra_id)

    qs = qs.order_by('data_atividade')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=14,
        textColor=colors.HexColor('#1B5E20'), alignment=TA_CENTER, spaceAfter=10,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Heading2'], fontSize=10,
        textColor=colors.HexColor('#1B5E20'), spaceBefore=10, spaceAfter=4,
    )
    small_style = ParagraphStyle(
        'Small', parent=styles['Normal'], fontSize=8,
    )

    story = []
    story.append(Paragraph('CADERNO DE CAMPO DIGITAL — GLOBALG.A.P.', title_style))
    story.append(Paragraph(f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', small_style))
    story.append(Spacer(1, 0.2 * inch))

    if not qs.exists():
        story.append(Paragraph('Nenhum registro encontrado para os filtros selecionados.', styles['Normal']))
    else:
        for reg in qs:
            story.append(Paragraph(
                f'{reg.data_atividade.strftime("%d/%m/%Y")} — {reg.get_tipo_atividade_display()} — {reg.talhao.nome}',
                section_style
            ))
            info = [
                ['Talhão', reg.talhao.nome, 'Safra', str(reg.safra) if reg.safra else '—'],
                ['Atividade', reg.atividade, 'Responsável',
                 reg.responsavel.get_full_name() if reg.responsavel else '—'],
                ['Temperatura', f'{reg.temperatura}°C' if reg.temperatura else '—',
                 'Umidade', f'{reg.umidade}%' if reg.umidade else '—'],
                ['Cond. Tempo', reg.get_condicao_tempo_display() if reg.condicao_tempo else '—', '', ''],
            ]
            tbl = Table(info, colWidths=[1.2 * inch, 2.6 * inch, 1.2 * inch, 2.2 * inch])
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
                ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#E8F5E9')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(tbl)

            insumos = reg.insumos_utilizados.all()
            if insumos.exists():
                story.append(Spacer(1, 0.08 * inch))
                ins_data = [['Produto', 'Quantidade', 'Unidade', 'Receituário', 'Carência']]
                for ins in insumos:
                    ins_data.append([
                        str(ins.produto),
                        str(ins.quantidade),
                        str(ins.unidade_medida),
                        ins.receituario_numero or '—',
                        f'{ins.carencia_dias} dias' if ins.carencia_dias else '—',
                    ])
                itbl = Table(ins_data, colWidths=[2.2 * inch, 1 * inch, 1 * inch, 1.5 * inch, 1.5 * inch])
                itbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 7.5),
                    ('GRID', (0, 0), (-1, -1), 0.4, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(itbl)

            if reg.observacoes:
                story.append(Spacer(1, 0.04 * inch))
                story.append(Paragraph(f'<b>Obs:</b> {reg.observacoes}', small_style))

            story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="caderno_campo_{datetime.now().strftime("%d%m%Y")}.pdf"'
    )
    return response
