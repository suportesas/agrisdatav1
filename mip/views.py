"""
Views para o módulo de Monitoramento MIP (Manejo Integrado de Pragas)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from decimal import Decimal
from django.utils import timezone

from .models import (
    MonitoramentoMIP, PragaNoMonitoramento, PontoMonitoramento,
    EstagioDesenvolvimento,
)
from .forms import (
    MonitoramentoMIPForm, PragaNoMonitoramentoForm,
    PontoMonitoramentoForm, EstagioDesenvolvimentoForm
)
from cadastros.models import Praga, Talhao, Safra


# ============================================================================
# ESTÁGIOS DE DESENVOLVIMENTO DE PRAGAS
# ============================================================================

@login_required
def estagio_list(request):
    empresa = request.user.empresa
    estagios = EstagioDesenvolvimento.objects.filter(
        empresa=empresa
    ).select_related('praga').order_by('praga', 'ordem_ciclo')

    praga_id = request.GET.get('praga')
    if praga_id:
        estagios = estagios.filter(praga_id=praga_id)

    tipo_estagio = request.GET.get('tipo')
    if tipo_estagio:
        estagios = estagios.filter(tipo_estagio=tipo_estagio)

    paginator = Paginator(estagios, 25)
    page = request.GET.get('page')
    estagios = paginator.get_page(page)

    pragas = Praga.objects.filter(empresa=empresa, ativa=True)
    fases_criticas = EstagioDesenvolvimento.objects.filter(
        empresa=empresa, eh_fase_critica=True
    ).count()
    pragas_count = pragas.count()

    return render(request, 'cadastros/monitoramento_mip/estagio_list.html', {
        'estagios': estagios,
        'pragas': pragas,
        'praga_id': praga_id,
        'tipo_estagio': tipo_estagio,
        'fases_criticas': fases_criticas,
        'pragas_count': pragas_count,
    })


@login_required
def estagio_create(request):
    empresa = request.user.empresa

    if request.method == 'POST':
        form = EstagioDesenvolvimentoForm(request.POST, empresa=empresa)
        if form.is_valid():
            estagio = form.save(commit=False)
            estagio.empresa = empresa
            estagio.save()
            messages.success(request, f'Estágio "{estagio}" criado com sucesso!')
            return redirect('mip:estagio_list')
    else:
        form = EstagioDesenvolvimentoForm(empresa=empresa)

    return render(request, 'cadastros/monitoramento_mip/estagio_form.html', {
        'form': form,
        'titulo': 'Novo Estágio de Desenvolvimento',
    })


@login_required
def estagio_update(request, pk):
    empresa = request.user.empresa
    estagio = get_object_or_404(EstagioDesenvolvimento, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = EstagioDesenvolvimentoForm(request.POST, instance=estagio, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Estágio "{estagio}" atualizado com sucesso!')
            return redirect('mip:estagio_list')
    else:
        form = EstagioDesenvolvimentoForm(instance=estagio, empresa=empresa)

    return render(request, 'cadastros/monitoramento_mip/estagio_form.html', {
        'form': form,
        'estagio': estagio,
        'titulo': 'Editar Estágio de Desenvolvimento',
    })


@login_required
def estagio_delete(request, pk):
    empresa = request.user.empresa
    estagio = get_object_or_404(EstagioDesenvolvimento, pk=pk, empresa=empresa)

    if request.method == 'POST':
        estagio.delete()
        messages.success(request, 'Estágio deletado com sucesso!')
        return redirect('mip:estagio_list')

    return render(request, 'cadastros/monitoramento_mip/estagio_confirm_delete.html', {
        'estagio': estagio,
    })


# ============================================================================
# MONITORAMENTO MIP
# ============================================================================

@login_required
def monitoramento_mip_list(request):
    empresa = request.user.empresa
    monitoramentos = MonitoramentoMIP.objects.filter(
        empresa=empresa
    ).select_related(
        'talhao', 'safra', 'cultura', 'responsavel'
    ).order_by('-data_monitoramento')

    talhao_id = request.GET.get('talhao')
    status = request.GET.get('status')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    if talhao_id:
        monitoramentos = monitoramentos.filter(talhao_id=talhao_id)
    if status:
        monitoramentos = monitoramentos.filter(status=status)
    if data_inicio:
        monitoramentos = monitoramentos.filter(data_monitoramento__gte=data_inicio)
    if data_fim:
        monitoramentos = monitoramentos.filter(data_monitoramento__lte=data_fim)

    paginator = Paginator(monitoramentos, 15)
    page = request.GET.get('page')
    monitoramentos = paginator.get_page(page)

    talhoes = Talhao.objects.filter(area__fazenda__empresa=empresa).distinct()

    return render(request, 'cadastros/monitoramento_mip/monitoramento_mip_list.html', {
        'monitoramentos': monitoramentos,
        'talhoes': talhoes,
        'talhao_id': talhao_id,
        'status': status,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })


@login_required
def monitoramento_mip_create(request):
    empresa = request.user.empresa

    if request.method == 'POST':
        form = MonitoramentoMIPForm(
            request.POST, request.FILES,
            user=request.user, empresa=empresa
        )
        if form.is_valid():
            try:
                monitoramento = form.save(commit=False)
                monitoramento.empresa = empresa
                monitoramento.criado_por = request.user
                monitoramento.status = 'COMPLETO'

                if monitoramento.talhao and not monitoramento.cultura:
                    culturas_safra = list(monitoramento.safra.culturas.all()) if monitoramento.safra else []
                    if len(culturas_safra) == 1:
                        monitoramento.cultura = culturas_safra[0].cultura
                    elif monitoramento.talhao.cultura_atual:
                        monitoramento.cultura = monitoramento.talhao.cultura_atual

                monitoramento.save()

                messages.success(
                    request,
                    f'✅ Monitoramento {monitoramento.numero} criado com sucesso! '
                    f'Safra: {monitoramento.safra.nome}, '
                    f'Cultura: {monitoramento.cultura.nome}. '
                    'Agora registre as pragas encontradas.'
                )
                return redirect('mip:monitoramento_mip_detail', pk=monitoramento.pk)
            except Exception as e:
                messages.error(request, f'❌ Erro ao criar monitoramento: {str(e)}')
                return render(request, 'cadastros/monitoramento_mip/monitoramento_mip_form.html', {'form': form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'❌ {field}: {error}')
    else:
        form = MonitoramentoMIPForm(user=request.user, empresa=empresa)

    return render(request, 'cadastros/monitoramento_mip/monitoramento_mip_form.html', {
        'form': form,
        'titulo': 'Novo Monitoramento MIP',
    })


@login_required
def monitoramento_mip_detail(request, pk):
    empresa = request.user.empresa
    monitoramento = get_object_or_404(MonitoramentoMIP, pk=pk, empresa=empresa)

    pragas_detectadas = monitoramento.pragas_detectadas.all().select_related(
        'praga', 'estagio_principal'
    )

    total_pragas = pragas_detectadas.count()
    pragas_com_defensivo = pragas_detectadas.filter(resultado_acao='RECOMENDA_DEFENSIVO')
    pragas_recomenda_defensivo = pragas_com_defensivo.count()

    return render(request, 'cadastros/monitoramento_mip/monitoramento_mip_detail.html', {
        'monitoramento': monitoramento,
        'pragas_detectadas': pragas_detectadas,
        'pragas_com_defensivo': pragas_com_defensivo,
        'total_pragas': total_pragas,
        'pragas_recomenda_defensivo': pragas_recomenda_defensivo,
    })


@login_required
def monitoramento_mip_add_praga(request, pk):
    empresa = request.user.empresa
    monitoramento = get_object_or_404(MonitoramentoMIP, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = PragaNoMonitoramentoForm(
            request.POST, monitoramento=monitoramento, empresa=empresa
        )
        if form.is_valid():
            praga_mon = form.save(commit=False)
            praga_mon.monitoramento = monitoramento

            praga_mon.incidencia_percentual = (
                (praga_mon.quantidade_pontos_com_praga /
                 monitoramento.quantidade_pontos) * 100
            )

            praga_mon.ned_valor = Decimal('5.0')
            praga_mon.ned_atingido = praga_mon.incidencia_percentual >= praga_mon.ned_valor

            if praga_mon.ned_atingido:
                praga_mon.resultado_acao = 'RECOMENDA_DEFENSIVO'
            else:
                praga_mon.resultado_acao = 'MONITORAR'

            praga_mon.save()

            messages.success(
                request,
                f'Praga "{praga_mon.praga.nome_comum}" registrada com sucesso! '
                f'Incidência: {praga_mon.incidencia_percentual:.1f}% - '
                f'Ação: {praga_mon.get_resultado_acao_display()}'
            )
            return redirect('mip:monitoramento_mip_detail', pk=monitoramento.pk)
    else:
        form = PragaNoMonitoramentoForm(monitoramento=monitoramento, empresa=empresa)

    return render(request, 'cadastros/monitoramento_mip/praga_form.html', {
        'form': form,
        'monitoramento': monitoramento,
        'titulo': 'Adicionar Praga ao Monitoramento',
    })


@login_required
def monitoramento_mip_praga_detail(request, pk):
    empresa = request.user.empresa
    praga_mon = get_object_or_404(
        PragaNoMonitoramento, pk=pk, monitoramento__empresa=empresa
    )
    monitoramento = praga_mon.monitoramento
    pontos = praga_mon.pontos.all().order_by('numero_ponto')

    return render(request, 'cadastros/monitoramento_mip/praga_detail.html', {
        'monitoramento': monitoramento,
        'praga_mon': praga_mon,
        'pontos': pontos,
    })


@login_required
def monitoramento_mip_praga_edit(request, pk):
    empresa = request.user.empresa
    praga_mon = get_object_or_404(
        PragaNoMonitoramento, pk=pk, monitoramento__empresa=empresa
    )
    monitoramento = praga_mon.monitoramento

    if request.method == 'POST':
        form = PragaNoMonitoramentoForm(
            request.POST, instance=praga_mon,
            monitoramento=monitoramento, empresa=empresa
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Praga atualizada com sucesso!')
            return redirect('mip:monitoramento_mip_detail', pk=monitoramento.pk)
    else:
        form = PragaNoMonitoramentoForm(
            instance=praga_mon, monitoramento=monitoramento, empresa=empresa
        )

    return render(request, 'cadastros/monitoramento_mip/praga_form.html', {
        'form': form,
        'monitoramento': monitoramento,
        'praga_mon': praga_mon,
        'editing': True,
    })


@login_required
def monitoramento_mip_praga_delete(request, pk):
    empresa = request.user.empresa
    praga_mon = get_object_or_404(
        PragaNoMonitoramento, pk=pk, monitoramento__empresa=empresa
    )
    monitoramento = praga_mon.monitoramento

    if request.method == 'POST':
        praga_mon.delete()
        messages.success(request, 'Praga removida do monitoramento.')
        return redirect('mip:monitoramento_mip_detail', pk=monitoramento.pk)

    return render(request, 'cadastros/monitoramento_mip/praga_confirm_delete.html', {
        'praga_mon': praga_mon,
        'monitoramento': monitoramento,
    })


@login_required
def monitoramento_mip_add_ponto(request, pk):
    empresa = request.user.empresa
    praga_mon = get_object_or_404(
        PragaNoMonitoramento, pk=pk, monitoramento__empresa=empresa
    )
    monitoramento = praga_mon.monitoramento

    proxima_numero = praga_mon.pontos.count() + 1

    if proxima_numero > 20:
        messages.error(request, 'Máximo de 20 pontos já foi atingido!')
        return redirect('mip:monitoramento_mip_praga_detail', pk=praga_mon.pk)

    if request.method == 'POST':
        form = PontoMonitoramentoForm(request.POST, request.FILES)
        if form.is_valid():
            ponto = form.save(commit=False)
            ponto.praga_monitoramento = praga_mon
            ponto.numero_ponto = proxima_numero
            ponto.save()
            messages.success(request, f'Ponto {ponto.numero_ponto} registrado com sucesso!')
            return redirect('mip:monitoramento_mip_praga_detail', pk=praga_mon.pk)
    else:
        form = PontoMonitoramentoForm()
        form.fields['numero_ponto'].initial = proxima_numero

    return render(request, 'cadastros/monitoramento_mip/ponto_form.html', {
        'form': form,
        'monitoramento': monitoramento,
        'praga_mon': praga_mon,
        'numero_ponto': proxima_numero,
        'titulo': f'Registrar Ponto {proxima_numero}/20',
    })


# ============================================================================
# AJAX ENDPOINTS
# ============================================================================

@login_required
def ajax_get_estagios_praga(request):
    empresa = request.user.empresa
    praga_id = request.GET.get('praga_id')

    if not praga_id:
        return JsonResponse({'estagios': []})

    estagios = EstagioDesenvolvimento.objects.filter(
        empresa=empresa, praga_id=praga_id, ativo=True
    ).values('id', 'tipo_estagio', 'descricao', 'ordem_ciclo').order_by('ordem_ciclo')

    return JsonResponse({'estagios': list(estagios), 'sucesso': True})


@login_required
def ajax_get_pragas_cultura(request):
    empresa = request.user.empresa

    pragas = Praga.objects.filter(
        empresa=empresa, ativa=True
    ).values('id', 'nome_comum', 'nome_cientifico').order_by('nome_comum')

    return JsonResponse({'pragas': list(pragas), 'sucesso': True})


@login_required
def ajax_calcular_incidencia(request):
    pontos_com_praga = int(request.GET.get('pontos_com_praga', 0))
    quantidade_pontos = int(request.GET.get('quantidade_pontos', 20))

    if quantidade_pontos == 0:
        return JsonResponse({'incidencia': 0, 'erro': 'Quantidade de pontos inválida'})

    incidencia = (pontos_com_praga / quantidade_pontos) * 100
    return JsonResponse({'incidencia': round(incidencia, 2), 'sucesso': True})


# ============================================================================
# PDF EXPORT
# ============================================================================

@login_required
def monitoramento_mip_pdf(request, pk):
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from datetime import datetime

    empresa = request.user.empresa
    monitoramento = get_object_or_404(MonitoramentoMIP, pk=pk, empresa=empresa)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="MIP_{monitoramento.numero}_{datetime.now().strftime("%d%m%Y")}.pdf"'
    )

    doc = SimpleDocTemplate(response, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'],
        fontSize=16, textColor=colors.HexColor('#1B5E20'),
        spaceAfter=12, alignment=TA_CENTER,
    )
    header_style = ParagraphStyle(
        'CustomHeader', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=6,
    )

    story.append(Paragraph(
        f'<b>RELATÓRIO DE MONITORAMENTO MIP</b><br/><b>{monitoramento.numero}</b>',
        title_style
    ))
    story.append(Spacer(1, 0.3*inch))

    info_data = [
        ['Talhão:', monitoramento.talhao.nome if monitoramento.talhao else '-'],
        ['Cultura:', str(monitoramento.cultura) if monitoramento.cultura else '-'],
        ['Responsável:', monitoramento.responsavel.get_full_name() if monitoramento.responsavel else '-'],
        ['Data:', monitoramento.data_monitoramento.strftime('%d/%m/%Y')],
        ['Status:', monitoramento.get_status_display()],
    ]

    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8F5E9')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), TA_LEFT),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    if monitoramento.temperatura_media or monitoramento.umidade_media:
        story.append(Paragraph('<b>Condições Climáticas</b>', styles['Heading2']))
        clima_data = [
            ['Temperatura:', f'{monitoramento.temperatura_media}°C' if monitoramento.temperatura_media else '-'],
            ['Umidade:', f'{monitoramento.umidade_media}%' if monitoramento.umidade_media else '-'],
            ['Velocidade Vento:', f'{monitoramento.velocidade_vento_media} km/h' if monitoramento.velocidade_vento_media else '-'],
            ['Condições:', monitoramento.get_condicoes_tempo_display() if monitoramento.condicoes_tempo else '-'],
        ]
        clima_table = Table(clima_data, colWidths=[2*inch, 4*inch])
        clima_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E3F2FD')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), TA_LEFT),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(clima_table)
        story.append(Spacer(1, 0.2*inch))

    pragas = PragaNoMonitoramento.objects.filter(monitoramento=monitoramento)
    if pragas.exists():
        story.append(Paragraph('<b>Pragas Detectadas</b>', styles['Heading2']))
        pragas_data = [['Praga', 'Incidência', 'Severidade', 'NED', 'Ação Recomendada']]
        for praga in pragas:
            pragas_data.append([
                praga.praga.nome[:25],
                f'{praga.incidencia_percentual:.1f}%',
                f'Nível {praga.severidade}',
                'Atingido' if praga.ned_atingido else 'Não',
                praga.get_resultado_acao_display()[:15],
            ])
        pragas_table = Table(pragas_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1*inch, 1.5*inch])
        pragas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), TA_CENTER),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F1F8E9')]),
        ]))
        story.append(pragas_table)
    else:
        story.append(Paragraph('<i>Nenhuma praga detectada neste monitoramento</i>', styles['Normal']))

    story.append(Spacer(1, 0.2*inch))

    if monitoramento.observacoes_gerais:
        story.append(Paragraph('<b>Observações</b>', styles['Heading2']))
        story.append(Paragraph(monitoramento.observacoes_gerais.replace('\n', '<br/>'), styles['Normal']))

    story.append(Spacer(1, 0.3*inch))
    footer_text = f'Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")} | Agrisdata'
    story.append(Paragraph(f'<i><font size=8>{footer_text}</font></i>', header_style))

    doc.build(story)
    return response


# ============================================================================
# CADASTRO EM LOTE DE ESTÁGIOS
# ============================================================================

@login_required
def estagio_cadastro_em_lote(request):
    empresa = request.user.empresa

    pragas = Praga.objects.filter(empresa=empresa, ativa=True).order_by('nome_comum')

    praga_id = request.GET.get('praga') or request.POST.get('praga')
    praga_selecionada = None
    estagios = []

    if praga_id:
        try:
            praga_selecionada = pragas.get(pk=praga_id)
            estagios = EstagioDesenvolvimento.objects.filter(
                empresa=empresa, praga=praga_selecionada
            ).order_by('ordem_ciclo')
        except Praga.DoesNotExist:
            pass

    return render(request, 'cadastros/monitoramento_mip/estagio_cadastro_em_lote.html', {
        'pragas': pragas,
        'praga_selecionada': praga_selecionada,
        'estagios': estagios,
    })


@login_required
def ajax_adicionar_estagio(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    empresa = request.user.empresa

    try:
        praga_id = request.POST.get('praga_id')
        tipo_estagio = request.POST.get('tipo_estagio')
        duracao_minima = request.POST.get('duracao_minima_dias')
        duracao_maxima = request.POST.get('duracao_maxima_dias')
        ordem_ciclo = request.POST.get('ordem_ciclo')
        descricao = request.POST.get('descricao', '')
        eh_fase_critica = request.POST.get('eh_fase_critica') == 'true'
        ativo = request.POST.get('ativo', 'true') == 'true'

        if not praga_id or not tipo_estagio or not ordem_ciclo:
            return JsonResponse({'success': False, 'error': 'Campos obrigatórios não preenchidos'})

        praga = get_object_or_404(Praga, pk=praga_id, empresa=empresa)

        estagio = EstagioDesenvolvimento.objects.create(
            empresa=empresa,
            praga=praga,
            tipo_estagio=tipo_estagio,
            descricao=descricao,
            duracao_minima_dias=int(duracao_minima) if duracao_minima else None,
            duracao_maxima_dias=int(duracao_maxima) if duracao_maxima else None,
            ordem_ciclo=int(ordem_ciclo),
            eh_fase_critica=eh_fase_critica,
            ativo=ativo,
        )

        return JsonResponse({
            'success': True,
            'id': estagio.id,
            'tipo_estagio': tipo_estagio,
            'get_tipo_estagio_display': estagio.get_tipo_estagio_display(),
            'descricao': estagio.descricao or '',
            'duracao_minima_dias': estagio.duracao_minima_dias,
            'duracao_maxima_dias': estagio.duracao_maxima_dias,
            'ordem_ciclo': estagio.ordem_ciclo,
            'eh_fase_critica': estagio.eh_fase_critica,
            'ativo': estagio.ativo,
            'observacoes': estagio.observacoes or '',
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def ajax_carregar_estagios(request):
    empresa = request.user.empresa
    praga_id = request.GET.get('praga_id')

    if not praga_id:
        return JsonResponse({'estagios': []})

    try:
        praga = Praga.objects.get(pk=praga_id, empresa=empresa)
        estagios = EstagioDesenvolvimento.objects.filter(
            empresa=empresa, praga=praga
        ).order_by('ordem_ciclo').values(
            'id', 'tipo_estagio', 'descricao', 'duracao_minima_dias',
            'duracao_maxima_dias', 'ordem_ciclo', 'eh_fase_critica', 'ativo'
        )

        estagios_data = []
        for e in estagios:
            estagios_data.append({
                'id': e['id'],
                'tipo': dict(EstagioDesenvolvimento.TIPO_ESTAGIO_CHOICES).get(e['tipo_estagio'], ''),
                'descricao': e['descricao'],
                'duracao': f"{e['duracao_minima_dias'] or '?'}-{e['duracao_maxima_dias'] or '?'} dias",
                'ordem': e['ordem_ciclo'],
                'critico': e['eh_fase_critica'],
                'ativo': e['ativo'],
            })

        return JsonResponse({'estagios': estagios_data})
    except Praga.DoesNotExist:
        return JsonResponse({'estagios': []})


@login_required
def ajax_deletar_estagio(request, pk):
    empresa = request.user.empresa
    estagio = get_object_or_404(EstagioDesenvolvimento, pk=pk, empresa=empresa)
    estagio.delete()
    return JsonResponse({'success': True, 'message': 'Estágio deletado com sucesso'})


@login_required
def ajax_buscar_talhoes(request):
    empresa = request.user.empresa
    termo = request.GET.get('q', '').strip()

    if not termo:
        return JsonResponse({'talhoes': []})

    talhoes = Talhao.objects.filter(
        area__fazenda__empresa=empresa, ativo=True
    ).filter(
        Q(codigo__icontains=termo) |
        Q(nome__icontains=termo) |
        Q(area__nome__icontains=termo)
    ).select_related('area', 'fazenda', 'cultura_atual').distinct()[:20]

    resultado = []
    for talhao in talhoes:
        safras_ativas = talhao.safras.filter(
            culturas__status__in=['PLANEJADA', 'EM_ANDAMENTO']
        ).prefetch_related('culturas__cultura').distinct().order_by('-ano')

        safra_ativa = safras_ativas.first()
        culturas_safra_ativa = list(safra_ativa.culturas.all()) if safra_ativa else []

        cultura_id = None
        cultura_nome = None

        if len(culturas_safra_ativa) == 1:
            cultura_id = culturas_safra_ativa[0].cultura.id
            cultura_nome = culturas_safra_ativa[0].cultura.nome
        elif talhao.cultura_atual:
            cultura_id = talhao.cultura_atual.id
            cultura_nome = talhao.cultura_atual.nome

        resultado.append({
            'id': talhao.id,
            'codigo': talhao.codigo,
            'nome': talhao.nome,
            'area': talhao.area.nome,
            'fazenda': talhao.fazenda.nome,
            'display': f"{talhao.fazenda.nome} - {talhao.area.nome} - {talhao.nome}",
            'simples': f"{talhao.area.nome} - {talhao.nome}",
            'cultura_id': cultura_id,
            'cultura_nome': cultura_nome,
            'safras_ativas': [
                {
                    'id': safra.id,
                    'nome': str(safra),
                    'ano': safra.ano,
                    'culturas': [
                        {'id': sc.cultura_id, 'nome': sc.cultura.nome, 'status': sc.get_status_display()}
                        for sc in safra.culturas.all()
                    ],
                }
                for safra in safras_ativas
            ]
        })

    return JsonResponse({'talhoes': resultado})


@login_required
def ajax_talhao_info(request, talhao_id):
    empresa = request.user.empresa
    try:
        talhao = Talhao.objects.select_related(
            'area', 'fazenda', 'cultura_atual'
        ).get(pk=talhao_id, area__fazenda__empresa=empresa, ativo=True)
    except Talhao.DoesNotExist:
        return JsonResponse({'error': 'Talhão não encontrado'}, status=404)

    safras_ativas = talhao.safras.filter(
        culturas__status__in=['PLANEJADA', 'EM_ANDAMENTO']
    ).prefetch_related('culturas__cultura').distinct().order_by('-ano')

    cultura_id = None
    cultura_nome = None
    safra_id_auto = None

    if safras_ativas.exists():
        primeira_safra = safras_ativas.first()
        culturas_primeira_safra = list(primeira_safra.culturas.all())
        if len(culturas_primeira_safra) == 1:
            cultura_id = culturas_primeira_safra[0].cultura.id
            cultura_nome = culturas_primeira_safra[0].cultura.nome
        if safras_ativas.count() == 1:
            safra_id_auto = primeira_safra.id
    elif talhao.cultura_atual:
        cultura_id = talhao.cultura_atual.id
        cultura_nome = talhao.cultura_atual.nome

    return JsonResponse({
        'talhao_id': talhao.id,
        'talhao_nome': talhao.nome,
        'cultura_id': cultura_id,
        'cultura_nome': cultura_nome,
        'safra_id_auto': safra_id_auto,
        'safras_ativas': [
            {
                'id': s.id,
                'nome': str(s),
                'culturas': [
                    {'id': sc.cultura_id, 'nome': sc.cultura.nome, 'status': sc.get_status_display()}
                    for sc in s.culturas.all()
                ],
            }
            for s in safras_ativas
        ],
    })
