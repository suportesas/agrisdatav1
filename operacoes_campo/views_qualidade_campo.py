"""Views do módulo Qualidade de Campo (RF-108)."""
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from core.pagination import paginate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from django.db.models import Q

from operacoes_campo.forms import InspecaoQualidadeCampoForm
from operacoes_campo.models import InspecaoQualidadeCampo, OrdemServico, TipoServicoOS


@login_required
def qualidade_campo_list(request):
    empresa = request.user.empresa
    qs = InspecaoQualidadeCampo.objects.filter(empresa=empresa).select_related(
        'talhao', 'safra', 'responsavel'
    )

    talhao_id = request.GET.get('talhao')
    safra_id = request.GET.get('safra')
    resultado = request.GET.get('resultado')
    tipo = request.GET.get('tipo')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if talhao_id:
        qs = qs.filter(talhao_id=talhao_id)
    if safra_id:
        qs = qs.filter(safra_id=safra_id)
    if resultado:
        qs = qs.filter(resultado=resultado)
    if tipo:
        qs = qs.filter(tipo_inspecao=tipo)
    if data_inicio:
        qs = qs.filter(data_inspecao__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_inspecao__lte=data_fim)

    from cadastros.models import Talhao, Safra
    talhoes = Talhao.objects.filter(empresa=empresa, ativo=True)
    safras = Safra.objects.filter(fazenda__empresa=empresa)

    total = qs.count()
    inspecoes_page, per_page, per_page_options = paginate(request, qs.order_by('-data_inspecao'))

    context = {
        'inspecoes': inspecoes_page,
        'talhoes': talhoes,
        'safras': safras,
        'talhao_selecionado': talhao_id,
        'safra_selecionada': safra_id,
        'resultado_selecionado': resultado,
        'tipo_selecionado': tipo,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'resultado_choices': InspecaoQualidadeCampo.RESULTADO_CHOICES,
        'tipo_choices': InspecaoQualidadeCampo.TIPO_CHOICES,
        'title': 'Qualidade de Campo',
        'total': total,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/qualidade_campo/qualidade_campo_list.html', context)


@login_required
def qualidade_campo_create(request):
    if request.method == 'POST':
        form = InspecaoQualidadeCampoForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            empresa = request.user.empresa
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.cadastrado_por = request.user
            tipo_outro = TipoServicoOS.objects.filter(
                Q(empresa=empresa) | Q(empresa=None), tipo_legado='OUTRO', ativo=True
            ).order_by('empresa').first()
            obj.os = OrdemServico.objects.create(
                empresa=empresa,
                tipo_servico=tipo_outro,
                talhao=obj.talhao,
                safra=obj.safra,
                responsavel=obj.responsavel,
                data_prevista=obj.data_inspecao,
                observacoes='OS gerada automaticamente pela inspeção de qualidade de campo.',
                cadastrado_por=request.user,
            )
            obj.save()
            messages.success(request, 'Inspeção de qualidade registrada com sucesso.')
            return redirect('operacoes_campo:qualidade_campo_detail', pk=obj.pk)
    else:
        form = InspecaoQualidadeCampoForm(user=request.user)
    return render(request, 'cadastros/qualidade_campo/qualidade_campo_form.html', {
        'form': form,
        'title': 'Nova Inspeção de Qualidade',
    })


@login_required
def qualidade_campo_detail(request, pk):
    obj = get_object_or_404(InspecaoQualidadeCampo, pk=pk, empresa=request.user.empresa)
    historico = InspecaoQualidadeCampo.objects.filter(
        empresa=request.user.empresa,
        talhao=obj.talhao,
    ).exclude(pk=pk).order_by('-data_inspecao')[:10]
    return render(request, 'cadastros/qualidade_campo/qualidade_campo_detail.html', {
        'obj': obj,
        'historico': historico,
        'title': f'Inspeção — {obj.talhao.nome}',
    })


@login_required
def qualidade_campo_update(request, pk):
    obj = get_object_or_404(InspecaoQualidadeCampo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = InspecaoQualidadeCampoForm(request.POST, request.FILES, instance=obj, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inspeção atualizada com sucesso.')
            return redirect('operacoes_campo:qualidade_campo_detail', pk=obj.pk)
    else:
        form = InspecaoQualidadeCampoForm(instance=obj, user=request.user)
    return render(request, 'cadastros/qualidade_campo/qualidade_campo_form.html', {
        'form': form,
        'obj': obj,
        'title': 'Editar Inspeção de Qualidade',
    })


@login_required
def qualidade_campo_delete(request, pk):
    obj = get_object_or_404(InspecaoQualidadeCampo, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Inspeção excluída.')
        return redirect('operacoes_campo:qualidade_campo_list')
    return render(request, 'cadastros/qualidade_campo/qualidade_campo_confirm_delete.html', {'obj': obj})


@login_required
def qualidade_campo_pdf(request, pk):
    from datetime import datetime

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle, Paragraph

    obj = get_object_or_404(InspecaoQualidadeCampo, pk=pk, empresa=request.user.empresa)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=15,
        textColor=colors.HexColor('#1B5E20'), alignment=TA_CENTER, spaceAfter=10,
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#555555'),
    )

    story = []
    story.append(Paragraph('RELATÓRIO DE INSPEÇÃO DE QUALIDADE DE CAMPO', title_style))
    story.append(Spacer(1, 0.2 * inch))

    resultado_cores = {
        'APROVADO': colors.HexColor('#28a745'),
        'APROVADO_COM_RESSALVA': colors.HexColor('#ffc107'),
        'REPROVADO': colors.HexColor('#dc3545'),
    }

    info = [
        ['Talhão', obj.talhao.nome, 'Data', obj.data_inspecao.strftime('%d/%m/%Y')],
        ['Safra', str(obj.safra) if obj.safra else '—', 'Tipo', obj.get_tipo_inspecao_display()],
        ['Responsável', obj.responsavel.nome_completo if obj.responsavel else '—',
         'Resultado', obj.get_resultado_display()],
        ['Estágio', obj.estagio_cultura or '—', 'Coloração', obj.get_coloracao_display() if obj.coloracao else '—'],
    ]
    tbl = Table(info, colWidths=[1.4 * inch, 2.4 * inch, 1.4 * inch, 2.0 * inch])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#E8F5E9')),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.2 * inch))

    params = [['Parâmetro', 'Valor']]
    if obj.brix is not None:
        params.append(['Brix (°Bx)', f'{obj.brix}'])
    if obj.peso_medio_fruto_g is not None:
        params.append(['Peso Médio Fruto (g)', f'{obj.peso_medio_fruto_g}'])
    if obj.percentual_defeitos is not None:
        params.append(['% Defeitos', f'{obj.percentual_defeitos}%'])
    if obj.previsao_colheita_dias is not None:
        params.append(['Previsão Colheita (dias)', str(obj.previsao_colheita_dias)])

    if len(params) > 1:
        story.append(Paragraph('<b>Parâmetros Técnicos</b>', label_style))
        story.append(Spacer(1, 0.1 * inch))
        ptbl = Table(params, colWidths=[3 * inch, 4.2 * inch])
        ptbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(ptbl)
        story.append(Spacer(1, 0.2 * inch))

    if obj.observacoes:
        story.append(Paragraph('<b>Observações</b>', label_style))
        story.append(Spacer(1, 0.05 * inch))
        story.append(Paragraph(obj.observacoes, styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(
        f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")} | Agrisdata Salutaris',
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=7,
                       textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="qualidade_campo_{obj.pk}_{obj.data_inspecao.strftime("%d%m%Y")}.pdf"'
    )
    return response
