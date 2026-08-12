"""
Views para Controle de RH
Férias, Afastamentos e Rescisões de Funcionários
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from core.pagination import paginate
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils import timezone
from datetime import date, timedelta
import base64
import io
from uuid import uuid4

from rh.models import (
    Funcionario, FeriasFuncionario, AfastamentoFuncionario,
    RescisaoContrato, VinculoContrato, FuncaoFuncionario, HistoricoFuncionario,
    LaudoRisco, TipoExameASO, SolicitacaoASO, LogEnvioSolicitacaoASO,
    CategoriaRiscoAmbiental,
)
from cadastros.models import Fornecedor
from rh.forms import (
    FeriasFuncionarioForm, AfastamentoFuncionarioForm,
    RescisaoContratoForm, VinculoContratoForm, LaudoRiscoForm, TipoExameASOForm, SolicitacaoASOForm
)


# ============================================================================
# DASHBOARD RH
# ============================================================================

@login_required
def rh_dashboard(request):
    """Dashboard geral de RH"""
    empresa = request.user.empresa

    def enrich_deadline_items(items, field_name, warning_days):
        severity_order = {'overdue': 0, 'urgent': 1, 'warning': 2, 'ok': 3}
        enriched = []
        for item in items:
            target_date = getattr(item, field_name, None)
            if not target_date:
                item.deadline_status = 'ok'
                item.deadline_days = None
            else:
                delta = (target_date - hoje).days
                item.deadline_days = delta
                if delta < 0:
                    item.deadline_status = 'overdue'
                elif delta <= 7:
                    item.deadline_status = 'urgent'
                elif delta <= warning_days:
                    item.deadline_status = 'warning'
                else:
                    item.deadline_status = 'ok'

            if item.deadline_status == 'overdue':
                item.deadline_icon = 'fas fa-circle-xmark'
                item.deadline_badge_class = 'text-bg-danger'
                item.deadline_label = 'Vencido'
            elif item.deadline_status == 'urgent':
                item.deadline_icon = 'fas fa-triangle-exclamation'
                item.deadline_badge_class = 'text-bg-danger'
                item.deadline_label = f'{item.deadline_days} dia(s)'
            elif item.deadline_status == 'warning':
                item.deadline_icon = 'fas fa-clock'
                item.deadline_badge_class = 'text-bg-warning'
                item.deadline_label = f'{item.deadline_days} dia(s)'
            else:
                item.deadline_icon = 'fas fa-check-circle'
                item.deadline_badge_class = 'text-bg-success'
                item.deadline_label = 'Em dia'

            enriched.append(item)
        enriched.sort(key=lambda item: (
            severity_order.get(getattr(item, 'deadline_status', 'ok'), 3),
            getattr(item, 'deadline_days', 9999) if getattr(item, 'deadline_days', None) is not None else 9999,
        ))
        return enriched

    def summarize_status(items):
        return {
            'overdue': sum(1 for item in items if getattr(item, 'deadline_status', '') == 'overdue'),
            'urgent': sum(1 for item in items if getattr(item, 'deadline_status', '') == 'urgent'),
            'warning': sum(1 for item in items if getattr(item, 'deadline_status', '') == 'warning'),
        }
    
    # Estatísticas Gerais
    total_funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        ativo=True
    ).count()
    
    # Férias
    ferias_agendadas = FeriasFuncionario.objects.filter(
        empresa=empresa,
        status='AGENDADA'
    ).count()
    
    ferias_em_gozo = FeriasFuncionario.objects.filter(
        empresa=empresa,
        status='EM_GOZO'
    ).count()
    
    # Próximas férias (próximos 30 dias)
    data_limite = date.today() + timedelta(days=30)
    proximas_ferias = FeriasFuncionario.objects.filter(
        empresa=empresa,
        status='AGENDADA',
        data_inicio__lte=data_limite,
        data_inicio__gte=date.today()
    ).select_related('funcionario').order_by('data_inicio')[:10]
    
    # Afastamentos
    afastamentos_ativos = AfastamentoFuncionario.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).count()
    
    # Afastamentos por tipo
    afastamentos_por_tipo = AfastamentoFuncionario.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).values('tipo_afastamento').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # Afastamentos ativos (lista)
    afastamentos_lista = AfastamentoFuncionario.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).select_related('funcionario').order_by('data_prevista_retorno')[:10]
    
    # Rescisões
    rescisoes_em_processo = RescisaoContrato.objects.filter(
        empresa=empresa,
        status='EM_PROCESSO'
    ).count()
    
    rescisoes_mes = RescisaoContrato.objects.filter(
        empresa=empresa,
        data_desligamento__year=date.today().year,
        data_desligamento__month=date.today().month
    ).count()

    # Vínculos contratuais
    hoje = date.today()
    data_limite_vencimento = hoje + timedelta(days=15)
    data_limite_experiencia = hoje + timedelta(days=30)
    data_limite_laudo = hoje + timedelta(days=30)

    vinculos_ativos = VinculoContrato.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).count()

    vinculos_a_vencer = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        data_fim_prevista__isnull=False,
        data_fim_prevista__gte=hoje,
        data_fim_prevista__lte=data_limite_vencimento,
        data_fim_real__isnull=True,
    ).select_related('funcionario').order_by('data_fim_prevista')[:10]

    vinculos_vencidos_abertos = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        data_fim_prevista__isnull=False,
        data_fim_prevista__lt=hoje,
        data_fim_real__isnull=True,
    ).select_related('funcionario').order_by('data_fim_prevista')[:10]

    experiencias_vencendo = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        periodo_experiencia=True,
        data_fim_experiencia__isnull=False,
        data_fim_experiencia__lte=data_limite_experiencia,
    ).select_related('funcionario', 'funcao').order_by('data_fim_experiencia')[:10]

    contratos_temporarios_vencendo = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        tipo_contrato='TEMPORARIO',
        data_fim_prevista__isnull=False,
        data_fim_prevista__lte=data_limite_vencimento,
        data_fim_real__isnull=True,
    ).select_related('funcionario', 'funcao').order_by('data_fim_prevista')[:10]

    laudos_vencendo = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__lte=data_limite_laudo,
    ).exclude(status='VENCIDO').select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade')[:10]

    experiencias_vencendo = enrich_deadline_items(experiencias_vencendo, 'data_fim_experiencia', 30)
    contratos_temporarios_vencendo = enrich_deadline_items(contratos_temporarios_vencendo, 'data_fim_prevista', 15)
    laudos_vencendo = enrich_deadline_items(laudos_vencendo, 'data_validade', 30)

    experiencias_status = summarize_status(experiencias_vencendo)
    temporarios_status = summarize_status(contratos_temporarios_vencendo)
    laudos_status = summarize_status(laudos_vencendo)

    total_experiencias_vencendo = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        periodo_experiencia=True,
        data_fim_experiencia__isnull=False,
        data_fim_experiencia__lte=data_limite_experiencia,
    ).count()

    total_contratos_temporarios_vencendo = VinculoContrato.objects.filter(
        empresa=empresa,
        status__in=['ATIVO', 'PROGRAMADO'],
        tipo_contrato='TEMPORARIO',
        data_fim_prevista__isnull=False,
        data_fim_prevista__lte=data_limite_vencimento,
        data_fim_real__isnull=True,
    ).count()

    total_laudos_vencendo = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__lte=data_limite_laudo,
    ).count()
    
    context = {
        'total_funcionarios': total_funcionarios,
        'ferias_agendadas': ferias_agendadas,
        'ferias_em_gozo': ferias_em_gozo,
        'proximas_ferias': proximas_ferias,
        'afastamentos_ativos': afastamentos_ativos,
        'afastamentos_por_tipo': afastamentos_por_tipo,
        'afastamentos_lista': afastamentos_lista,
        'rescisoes_em_processo': rescisoes_em_processo,
        'rescisoes_mes': rescisoes_mes,
        'vinculos_ativos': vinculos_ativos,
        'vinculos_a_vencer': vinculos_a_vencer,
        'vinculos_vencidos_abertos': vinculos_vencidos_abertos,
        'experiencias_vencendo': experiencias_vencendo,
        'contratos_temporarios_vencendo': contratos_temporarios_vencendo,
        'laudos_vencendo': laudos_vencendo,
        'total_experiencias_vencendo': total_experiencias_vencendo,
        'total_contratos_temporarios_vencendo': total_contratos_temporarios_vencendo,
        'total_laudos_vencendo': total_laudos_vencendo,
        'experiencias_status': experiencias_status,
        'temporarios_status': temporarios_status,
        'laudos_status': laudos_status,
    }
    
    return render(request, 'cadastros/rh/dashboard.html', context)


# ============================================================================
# FÉRIAS
# ============================================================================

@login_required
def ferias_list(request):
    """Lista todas as férias"""
    empresa = request.user.empresa
    
    ferias = FeriasFuncionario.objects.filter(
        empresa=empresa
    ).select_related('funcionario').order_by('-data_inicio')
    
    # Filtros
    status_filter = request.GET.get('status')
    funcionario_filter = request.GET.get('funcionario')
    busca = request.GET.get('q')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status_filter:
        ferias = ferias.filter(status=status_filter)
    
    if funcionario_filter:
        ferias = ferias.filter(funcionario_id=funcionario_filter)
    
    if busca:
        ferias = ferias.filter(
            Q(funcionario__nome_completo__icontains=busca)
        )
    
    if data_inicio:
        ferias = ferias.filter(data_inicio__gte=data_inicio)
    
    if data_fim:
        ferias = ferias.filter(data_fim__lte=data_fim)
    
    # Paginação
    page_obj, per_page, per_page_options = paginate(request, ferias)

    # Funcionários para filtro
    funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        ativo=True
    ).order_by('nome_completo')

    context = {
        'page_obj': page_obj,
        'funcionarios': funcionarios,
        'status_filter': status_filter,
        'funcionario_filter': funcionario_filter,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    
    return render(request, 'cadastros/rh/ferias_list.html', context)


@login_required
def ferias_previsao_pdf(request):
    """Gera PDF com férias previstas para o mês atual e o mês seguinte."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    empresa = request.user.empresa
    hoje = timezone.now().date()

    inicio_periodo = hoje.replace(day=1)
    if hoje.month == 12:
        inicio_mes_seguinte = date(hoje.year + 1, 1, 1)
    else:
        inicio_mes_seguinte = date(hoje.year, hoje.month + 1, 1)

    if inicio_mes_seguinte.month == 12:
        inicio_mes_apos_proximo = date(inicio_mes_seguinte.year + 1, 1, 1)
    else:
        inicio_mes_apos_proximo = date(inicio_mes_seguinte.year, inicio_mes_seguinte.month + 1, 1)
    fim_periodo = inicio_mes_apos_proximo - timedelta(days=1)

    ferias_previstas = (
        FeriasFuncionario.objects.filter(
            empresa=empresa,
            data_inicio__gte=inicio_periodo,
            data_inicio__lte=fim_periodo,
            status__in=['AGENDADA', 'EM_GOZO'],
        )
        .select_related('funcionario', 'funcionario__funcao')
        .order_by('data_inicio', 'funcionario__nome_completo')
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=42, bottomMargin=36)
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'TituloFeriasPrevistas',
        parent=styles['Heading1'],
        fontSize=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1d4ed8'),
        spaceAfter=8,
    )
    texto_style = ParagraphStyle(
        'TextoFeriasPrevistas',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        spaceAfter=2,
    )

    story = [
        Paragraph('Relatório de Férias Previstas', titulo_style),
        Paragraph(f'Empresa: {empresa.nome}', texto_style),
        Paragraph(
            f'Período considerado: {inicio_periodo.strftime("%d/%m/%Y")} até {fim_periodo.strftime("%d/%m/%Y")}',
            texto_style,
        ),
        Paragraph(f'Gerado em: {timezone.now().strftime("%d/%m/%Y %H:%M")}', texto_style),
        Spacer(1, 0.15 * inch),
    ]

    if ferias_previstas:
        dados = [['Funcionário', 'Função', 'Início', 'Fim', 'Dias', 'Status']]
        for ferias in ferias_previstas:
            dados.append([
                ferias.funcionario.nome_completo,
                getattr(ferias.funcionario.funcao, 'nome', '-') if ferias.funcionario_id else '-',
                ferias.data_inicio.strftime('%d/%m/%Y') if ferias.data_inicio else '-',
                ferias.data_fim.strftime('%d/%m/%Y') if ferias.data_fim else '-',
                str(ferias.dias_ferias or '-'),
                ferias.get_status_display(),
            ])

        tabela = Table(dados, colWidths=[2.25 * inch, 1.45 * inch, 0.85 * inch, 0.85 * inch, 0.5 * inch, 1.0 * inch])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5efff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tabela)
    else:
        story.append(Paragraph('Nenhum funcionário com férias previstas no período informado.', texto_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="ferias_previstas_{inicio_periodo.strftime("%Y%m")}_a_{fim_periodo.strftime("%Y%m")}.pdf"'
    )
    response.write(pdf_bytes)
    return response


@login_required
def ferias_create(request):
    """Criar nova férias"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = FeriasFuncionarioForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            ferias = form.save(commit=False)
            ferias.empresa = empresa
            ferias.cadastrado_por = request.user
            ferias.save()
            messages.success(request, 'Férias cadastradas com sucesso!')
            return redirect('rh:ferias_detail', pk=ferias.pk)
    else:
        form = FeriasFuncionarioForm(empresa=empresa)
    
    return render(request, 'cadastros/rh/ferias_form.html', {
        'form': form,
        'title': 'Cadastrar Férias'
    })


@login_required
def ferias_detail(request, pk):
    """Detalhes de férias"""
    empresa = request.user.empresa
    ferias = get_object_or_404(
        FeriasFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    return render(request, 'cadastros/rh/ferias_detail.html', {
        'ferias': ferias
    })


@login_required
def ferias_update(request, pk):
    """Editar férias"""
    empresa = request.user.empresa
    ferias = get_object_or_404(
        FeriasFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = FeriasFuncionarioForm(
            request.POST,
            request.FILES,
            instance=ferias,
            empresa=empresa
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Férias atualizadas com sucesso!')
            return redirect('rh:ferias_detail', pk=ferias.pk)
    else:
        form = FeriasFuncionarioForm(instance=ferias, empresa=empresa)
    
    return render(request, 'cadastros/rh/ferias_form.html', {
        'form': form,
        'ferias': ferias,
        'title': 'Editar Férias'
    })


@login_required
def ferias_delete(request, pk):
    """Excluir férias"""
    empresa = request.user.empresa
    ferias = get_object_or_404(
        FeriasFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        ferias.delete()
        messages.success(request, 'Férias excluídas com sucesso!')
        return redirect('rh:ferias_list')
    
    return render(request, 'cadastros/rh/ferias_confirm_delete.html', {
        'ferias': ferias
    })


# ============================================================================
# AFASTAMENTOS
# ============================================================================

@login_required
def afastamento_list(request):
    """Lista todos os afastamentos"""
    empresa = request.user.empresa
    
    afastamentos = AfastamentoFuncionario.objects.filter(
        empresa=empresa
    ).select_related('funcionario').order_by('-data_inicio')
    
    # Filtros
    status_filter = request.GET.get('status')
    tipo_filter = request.GET.get('tipo')
    funcionario_filter = request.GET.get('funcionario')
    busca = request.GET.get('q')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status_filter:
        afastamentos = afastamentos.filter(status=status_filter)
    
    if tipo_filter:
        afastamentos = afastamentos.filter(tipo_afastamento=tipo_filter)
    
    if funcionario_filter:
        afastamentos = afastamentos.filter(funcionario_id=funcionario_filter)
    
    if busca:
        afastamentos = afastamentos.filter(
            Q(funcionario__nome_completo__icontains=busca) |
            Q(motivo__icontains=busca)
        )
    
    if data_inicio:
        afastamentos = afastamentos.filter(data_inicio__gte=data_inicio)
    
    if data_fim:
        afastamentos = afastamentos.filter(data_fim__lte=data_fim)
    
    # Paginação
    page_obj, per_page, per_page_options = paginate(request, afastamentos)

    # Funcionários para filtro
    funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        ativo=True
    ).order_by('nome_completo')

    context = {
        'page_obj': page_obj,
        'funcionarios': funcionarios,
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'funcionario_filter': funcionario_filter,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    
    return render(request, 'cadastros/rh/afastamento_list.html', context)


@login_required
def afastamento_create(request):
    """Criar novo afastamento"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = AfastamentoFuncionarioForm(
            request.POST,
            request.FILES,
            empresa=empresa
        )
        if form.is_valid():
            afastamento = form.save(commit=False)
            afastamento.empresa = empresa
            afastamento.cadastrado_por = request.user
            afastamento.save()
            messages.success(request, 'Afastamento cadastrado com sucesso!')
            return redirect('rh:afastamento_detail', pk=afastamento.pk)
    else:
        form = AfastamentoFuncionarioForm(empresa=empresa)
    
    return render(request, 'cadastros/rh/afastamento_form.html', {
        'form': form,
        'title': 'Cadastrar Afastamento'
    })


@login_required
def afastamento_detail(request, pk):
    """Detalhes do afastamento"""
    empresa = request.user.empresa
    afastamento = get_object_or_404(
        AfastamentoFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    return render(request, 'cadastros/rh/afastamento_detail.html', {
        'afastamento': afastamento
    })


@login_required
def afastamento_update(request, pk):
    """Editar afastamento"""
    empresa = request.user.empresa
    afastamento = get_object_or_404(
        AfastamentoFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = AfastamentoFuncionarioForm(
            request.POST,
            request.FILES,
            instance=afastamento,
            empresa=empresa
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Afastamento atualizado com sucesso!')
            return redirect('rh:afastamento_detail', pk=afastamento.pk)
    else:
        form = AfastamentoFuncionarioForm(instance=afastamento, empresa=empresa)
    
    return render(request, 'cadastros/rh/afastamento_form.html', {
        'form': form,
        'afastamento': afastamento,
        'title': 'Editar Afastamento'
    })


@login_required
def afastamento_delete(request, pk):
    """Excluir afastamento"""
    empresa = request.user.empresa
    afastamento = get_object_or_404(
        AfastamentoFuncionario.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        afastamento.delete()
        messages.success(request, 'Afastamento excluído com sucesso!')
        return redirect('rh:afastamento_list')
    
    return render(request, 'cadastros/rh/afastamento_confirm_delete.html', {
        'afastamento': afastamento
    })


# ============================================================================
# VÍNCULOS CONTRATUAIS
# ============================================================================

@login_required
def vinculo_list(request):
    """Lista vínculos contratuais."""
    empresa = request.user.empresa

    vinculos = VinculoContrato.objects.filter(
        empresa=empresa
    ).select_related('funcionario', 'funcao').order_by('-data_inicio')

    status_filter = request.GET.get('status')
    origem_filter = request.GET.get('origem')
    busca = request.GET.get('q')

    if status_filter:
        vinculos = vinculos.filter(status=status_filter)
    if origem_filter:
        vinculos = vinculos.filter(origem=origem_filter)
    if busca:
        vinculos = vinculos.filter(
            Q(funcionario__nome_completo__icontains=busca) |
            Q(matricula__icontains=busca)
        )

    page_obj, per_page, per_page_options = paginate(request, vinculos)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'origem_filter': origem_filter,
        'busca': busca,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/rh/vinculo_list.html', context)


@login_required
def vinculo_create(request):
    """Nova contratação/recontratação via vínculo."""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = VinculoContratoForm(request.POST, empresa=empresa)
        if form.is_valid():
            vinculo = form.save(commit=False)
            vinculo.empresa = empresa
            vinculo.cadastrado_por = request.user

            # Snapshot dos adicionais de risco no momento da contratação
            if vinculo.funcao:
                vinculo.possui_insalubridade = vinculo.funcao.possui_insalubridade
                vinculo.grau_insalubridade = vinculo.funcao.grau_insalubridade or ''
                vinculo.possui_periculosidade = vinculo.funcao.possui_periculosidade
                vinculo.percentual_periculosidade = vinculo.funcao.percentual_periculosidade

            if not vinculo.salario:
                vinculo.salario = vinculo.funcionario.salario

            vinculo.save()

            if vinculo.origem == 'RECONTRATACAO':
                HistoricoFuncionario.objects.create(
                    funcionario=vinculo.funcionario,
                    tipo_evento='RECONTRATACAO',
                    funcao=vinculo.funcao,
                    salario=vinculo.salario,
                    motivo=f'Recontratação registrada via vínculo contratual em {vinculo.data_inicio.strftime("%d/%m/%Y")}.',
                    usuario=request.user,
                )

            # Atualiza status do funcionário com base no vínculo ativo
            funcionario = vinculo.funcionario
            funcionario.ativo = vinculo.status == 'ATIVO'
            funcionario.data_admissao = vinculo.data_inicio
            funcionario.data_demissao = None if funcionario.ativo else funcionario.data_demissao
            if vinculo.funcao:
                funcionario.funcao = vinculo.funcao
            if vinculo.salario:
                funcionario.salario = vinculo.salario
            if vinculo.tipo_contrato:
                funcionario.tipo_contrato = vinculo.tipo_contrato
            funcionario.save()

            messages.success(request, 'Vínculo contratual cadastrado com sucesso!')
            return redirect('rh:vinculo_detail', pk=vinculo.pk)
    else:
        form = VinculoContratoForm(empresa=empresa)

    return render(request, 'cadastros/rh/vinculo_form.html', {
        'form': form,
        'title': 'Nova Contratação / Recontratação'
    })


@login_required
def vinculo_detail(request, pk):
    """Detalhes do vínculo contratual."""
    empresa = request.user.empresa
    vinculo = get_object_or_404(
        VinculoContrato.objects.filter(empresa=empresa).select_related('funcionario', 'funcao'),
        pk=pk
    )
    return render(request, 'cadastros/rh/vinculo_detail.html', {
        'vinculo': vinculo
    })


@login_required
def vinculo_update(request, pk):
    """Editar vínculo contratual."""
    empresa = request.user.empresa
    vinculo = get_object_or_404(VinculoContrato.objects.filter(empresa=empresa), pk=pk)

    if request.method == 'POST':
        form = VinculoContratoForm(request.POST, instance=vinculo, empresa=empresa)
        if form.is_valid():
            vinculo = form.save(commit=False)
            if vinculo.funcao:
                vinculo.possui_insalubridade = vinculo.funcao.possui_insalubridade
                vinculo.grau_insalubridade = vinculo.funcao.grau_insalubridade or ''
                vinculo.possui_periculosidade = vinculo.funcao.possui_periculosidade
                vinculo.percentual_periculosidade = vinculo.funcao.percentual_periculosidade
            vinculo.save()
            messages.success(request, 'Vínculo contratual atualizado com sucesso!')
            return redirect('rh:vinculo_detail', pk=vinculo.pk)
    else:
        form = VinculoContratoForm(instance=vinculo, empresa=empresa)

    return render(request, 'cadastros/rh/vinculo_form.html', {
        'form': form,
        'vinculo': vinculo,
        'title': 'Editar Vínculo Contratual'
    })


# ============================================================================
# LAUDOS DE RISCO
# ============================================================================

@login_required
def laudo_list(request):
    """Lista de laudos de risco ocupacional."""
    empresa = request.user.empresa

    laudos = LaudoRisco.objects.filter(
        empresa=empresa
    ).select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade', '-data_cadastro')

    status_filter = request.GET.get('status')
    tipo_filter = request.GET.get('tipo')
    funcao_filter = request.GET.get('funcao')
    categoria_filter = request.GET.get('categoria')
    busca = request.GET.get('q')

    if status_filter:
        laudos = laudos.filter(status=status_filter)
    if tipo_filter:
        laudos = laudos.filter(tipo_laudo=tipo_filter)
    if funcao_filter:
        laudos = laudos.filter(funcao_id=funcao_filter)
    if categoria_filter:
        laudos = laudos.filter(
            funcao__riscos_ambientais__categoria_id=categoria_filter,
            funcao__riscos_ambientais__ativo=True,
        ).distinct()
    if busca:
        laudos = laudos.filter(
            Q(funcao__nome__icontains=busca) |
            Q(responsavel_tecnico__icontains=busca) |
            Q(numero_art__icontains=busca)
        )

    page_obj, per_page, per_page_options = paginate(request, laudos)

    context = {
        'page_obj': page_obj,
        'funcoes': FuncaoFuncionario.objects.filter(empresa=empresa, ativa=True).order_by('nome'),
        'categorias_risco': CategoriaRiscoAmbiental.objects.filter(empresa=empresa, ativo=True).order_by('nome'),
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'funcao_filter': funcao_filter,
        'categoria_filter': categoria_filter,
        'busca': busca,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/rh/laudo_list.html', context)


@login_required
def laudo_create(request):
    """Cadastro de novo laudo de risco."""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = LaudoRiscoForm(request.POST, request.FILES, empresa=empresa)
        if form.is_valid():
            laudo = form.save(commit=False)
            laudo.empresa = empresa
            laudo.cadastrado_por = request.user
            laudo.save()
            messages.success(request, 'Laudo de risco cadastrado com sucesso!')
            return redirect('rh:laudo_detail', pk=laudo.pk)
    else:
        form = LaudoRiscoForm(empresa=empresa)

    return render(request, 'cadastros/rh/laudo_form.html', {
        'form': form,
        'title': 'Novo Laudo de Risco'
    })


@login_required
def laudo_detail(request, pk):
    """Detalhes de um laudo de risco."""
    empresa = request.user.empresa
    laudo = get_object_or_404(
        LaudoRisco.objects.filter(empresa=empresa).select_related('funcao', 'vinculo', 'vinculo__funcionario'),
        pk=pk
    )

    return render(request, 'cadastros/rh/laudo_detail.html', {
        'laudo': laudo
    })


@login_required
def laudo_update(request, pk):
    """Editar laudo de risco."""
    empresa = request.user.empresa
    laudo = get_object_or_404(LaudoRisco.objects.filter(empresa=empresa), pk=pk)

    if request.method == 'POST':
        form = LaudoRiscoForm(request.POST, request.FILES, instance=laudo, empresa=empresa)
        if form.is_valid():
            laudo = form.save()
            messages.success(request, 'Laudo de risco atualizado com sucesso!')
            return redirect('rh:laudo_detail', pk=laudo.pk)
    else:
        form = LaudoRiscoForm(instance=laudo, empresa=empresa)

    return render(request, 'cadastros/rh/laudo_form.html', {
        'form': form,
        'laudo': laudo,
        'title': 'Editar Laudo de Risco'
    })


# ============================================================================
# TIPOS DE EXAME ASO
# ============================================================================

@login_required
def tipo_exame_aso_list(request):
    """Lista tipos de exame ASO da empresa."""
    empresa = request.user.empresa

    exames = TipoExameASO.objects.filter(empresa=empresa).order_by('ordem', 'nome')

    busca = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip()

    if busca:
        exames = exames.filter(Q(nome__icontains=busca) | Q(codigo__icontains=busca))

    if status == 'ativos':
        exames = exames.filter(ativo=True)
    elif status == 'inativos':
        exames = exames.filter(ativo=False)

    page_obj, per_page, per_page_options = paginate(request, exames)

    context = {
        'page_obj': page_obj,
        'busca': busca,
        'status': status,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/rh/tipo_exame_aso_list.html', context)


@login_required
def tipo_exame_aso_create(request):
    """Cria um novo tipo de exame ASO para a empresa."""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = TipoExameASOForm(request.POST, empresa=empresa)
        if form.is_valid():
            exame = form.save(commit=False)
            exame.empresa = empresa
            exame.save()
            messages.success(request, f'Tipo de exame "{exame.nome}" cadastrado com sucesso!')
            return redirect('rh:tipo_exame_aso_list')
    else:
        form = TipoExameASOForm(empresa=empresa)

    return render(request, 'cadastros/rh/tipo_exame_aso_form.html', {
        'form': form,
        'title': 'Novo Tipo de Exame ASO',
    })


@login_required
def tipo_exame_aso_update(request, pk):
    """Edita um tipo de exame ASO."""
    empresa = request.user.empresa
    exame = get_object_or_404(TipoExameASO, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = TipoExameASOForm(request.POST, instance=exame, empresa=empresa)
        if form.is_valid():
            exame = form.save()
            messages.success(request, f'Tipo de exame "{exame.nome}" atualizado com sucesso!')
            return redirect('rh:tipo_exame_aso_list')
    else:
        form = TipoExameASOForm(instance=exame, empresa=empresa)

    return render(request, 'cadastros/rh/tipo_exame_aso_form.html', {
        'form': form,
        'exame': exame,
        'title': 'Editar Tipo de Exame ASO',
    })


@login_required
def tipo_exame_aso_toggle_ativo(request, pk):
    """Ativa/Inativa tipo de exame ASO sem excluir histórico."""
    if request.method != 'POST':
        messages.error(request, 'Método não permitido para esta ação.')
        return redirect('rh:tipo_exame_aso_list')

    empresa = request.user.empresa
    exame = get_object_or_404(TipoExameASO, pk=pk, empresa=empresa)
    exame.ativo = not exame.ativo
    exame.save(update_fields=['ativo', 'data_atualizacao'])

    if exame.ativo:
        messages.success(request, f'Tipo de exame "{exame.nome}" ativado com sucesso!')
    else:
        messages.warning(request, f'Tipo de exame "{exame.nome}" inativado com sucesso!')

    return redirect('rh:tipo_exame_aso_list')


# ============================================================================
# SOLICITAÇÕES DE ASO
# ============================================================================

def _listar_riscos_ambientais_funcionario(funcionario):
    """Retorna riscos ambientais ativos da função vinculada ao funcionário."""
    if not funcionario or not getattr(funcionario, 'funcao', None):
        return []

    return list(
        funcionario.funcao.riscos_ambientais.filter(ativo=True)
        .select_related('categoria')
        .order_by('categoria__nome', 'agente_especifico')
    )


@login_required
def aso_funcionario_riscos(request, funcionario_id):
    """Endpoint JSON com riscos ambientais ativos da função do funcionário."""
    empresa = request.user.empresa
    funcionario = get_object_or_404(
        Funcionario.objects.filter(empresa=empresa).select_related('funcao'),
        pk=funcionario_id,
    )

    riscos = _listar_riscos_ambientais_funcionario(funcionario)
    data = [
        {
            'categoria': risco.categoria.nome,
            'agente': risco.agente_especifico,
            'intensidade': risco.get_intensidade_display(),
            'epi': risco.epi_obrigatorio or '-',
        }
        for risco in riscos
    ]

    return JsonResponse({
        'ok': True,
        'funcao': funcionario.funcao.nome if funcionario.funcao else '-',
        'riscos': data,
    })


@login_required
def aso_buscar_laboratorio(request):
    """Busca fornecedores para seleção como laboratório no ASO (autocomplete)."""
    q = (request.GET.get('q') or '').strip()
    empresa = request.user.empresa
    qs = Fornecedor.objects.filter(empresa=empresa)
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(nome_fantasia__icontains=q))
    qs = qs.order_by('nome')[:25]
    results = [
        {
            'id': f.pk,
            'label': f.nome_fantasia or f.nome,
            'nome_completo': f.nome,
            'email': f.email,
            'cidade': f.cidade or '',
        }
        for f in qs
    ]
    return JsonResponse({'ok': True, 'results': results})


@login_required
def aso_solicitacao_list(request):
    """Lista solicitações de ASO da empresa."""
    empresa = request.user.empresa

    solicitacoes = SolicitacaoASO.objects.filter(
        empresa=empresa
    ).select_related('funcionario', 'vinculo').prefetch_related('exames').order_by('-data_cadastro')

    busca = (request.GET.get('q') or '').strip()
    status_filter = (request.GET.get('status') or '').strip()
    tipo_filter = (request.GET.get('tipo') or '').strip()
    funcionario_filter = (request.GET.get('funcionario') or '').strip()

    if busca:
        solicitacoes = solicitacoes.filter(
            Q(funcionario__nome_completo__icontains=busca)
            | Q(laboratorio_nome__icontains=busca)
            | Q(trabalhador_whatsapp__icontains=busca)
        )

    if status_filter:
        solicitacoes = solicitacoes.filter(status=status_filter)

    if tipo_filter:
        solicitacoes = solicitacoes.filter(tipo_aso=tipo_filter)

    if funcionario_filter:
        solicitacoes = solicitacoes.filter(funcionario_id=funcionario_filter)

    page_obj, per_page, per_page_options = paginate(request, solicitacoes)

    context = {
        'page_obj': page_obj,
        'funcionarios': Funcionario.objects.filter(empresa=empresa).order_by('nome_completo'),
        'busca': busca,
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'funcionario_filter': funcionario_filter,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    return render(request, 'cadastros/rh/aso_solicitacao_list.html', context)


@login_required
def aso_solicitacao_create(request):
    """Cria solicitação de ASO."""
    empresa = request.user.empresa

    riscos_ambientais_funcao = []

    if request.method == 'POST':
        form = SolicitacaoASOForm(request.POST, empresa=empresa)
        funcionario_id = request.POST.get('funcionario')
        if funcionario_id:
            funcionario = Funcionario.objects.filter(empresa=empresa, pk=funcionario_id).select_related('funcao').first()
            riscos_ambientais_funcao = _listar_riscos_ambientais_funcionario(funcionario)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.empresa = empresa
            solicitacao.cadastrado_por = request.user
            solicitacao.save()
            form.save_m2m()
            messages.success(request, 'Solicitação de ASO cadastrada com sucesso!')
            return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)
    else:
        form = SolicitacaoASOForm(empresa=empresa)

    return render(request, 'cadastros/rh/aso_solicitacao_form.html', {
        'form': form,
        'title': 'Nova Solicitação de ASO',
        'riscos_ambientais_funcao': riscos_ambientais_funcao,
    })


@login_required
def aso_solicitacao_detail(request, pk):
    """Detalhes da solicitação de ASO."""
    empresa = request.user.empresa
    solicitacao = get_object_or_404(
        SolicitacaoASO.objects.filter(empresa=empresa).select_related('funcionario', 'funcionario__funcao', 'vinculo', 'cadastrado_por').prefetch_related('exames'),
        pk=pk,
    )

    riscos_ambientais_funcao = _listar_riscos_ambientais_funcionario(solicitacao.funcionario)

    return render(request, 'cadastros/rh/aso_solicitacao_detail.html', {
        'solicitacao': solicitacao,
        'logs_envio': solicitacao.logs_envio.all()[:20],
        'riscos_ambientais_funcao': riscos_ambientais_funcao,
    })


@login_required
def aso_solicitacao_update(request, pk):
    """Edita solicitação de ASO."""
    empresa = request.user.empresa
    solicitacao = get_object_or_404(SolicitacaoASO, pk=pk, empresa=empresa)

    riscos_ambientais_funcao = _listar_riscos_ambientais_funcionario(solicitacao.funcionario)

    if request.method == 'POST':
        form = SolicitacaoASOForm(request.POST, instance=solicitacao, empresa=empresa)
        funcionario_id = request.POST.get('funcionario')
        if funcionario_id:
            funcionario = Funcionario.objects.filter(empresa=empresa, pk=funcionario_id).select_related('funcao').first()
            riscos_ambientais_funcao = _listar_riscos_ambientais_funcionario(funcionario)
        if form.is_valid():
            # Grava o status anterior antes de salvar
            status_anterior = solicitacao.status
            solicitacao = form.save()
            
            # Verifica se mudou para CONCLUIDO e tenta criar a próxima ASO
            if status_anterior != 'CONCLUIDO' and solicitacao.status == 'CONCLUIDO':
                proxima_aso = solicitacao.gerar_proxima_aso()
                if proxima_aso:
                    messages.success(
                        request,
                        f'Solicitação de ASO atualizada com sucesso! Próxima ASO programada para {proxima_aso.data_prevista_exame.strftime("%d/%m/%Y")}.'
                    )
                else:
                    messages.success(request, 'Solicitação de ASO atualizada com sucesso!')
            else:
                messages.success(request, 'Solicitação de ASO atualizada com sucesso!')
            
            return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)
    else:
        form = SolicitacaoASOForm(instance=solicitacao, empresa=empresa)

    return render(request, 'cadastros/rh/aso_solicitacao_form.html', {
        'form': form,
        'solicitacao': solicitacao,
        'title': 'Editar Solicitação de ASO',
        'riscos_ambientais_funcao': riscos_ambientais_funcao,
    })


@login_required
def aso_solicitacao_assinar(request, pk):
    """Assina eletronicamente uma solicitação de ASO via canvas."""
    empresa = request.user.empresa
    solicitacao = get_object_or_404(SolicitacaoASO, pk=pk, empresa=empresa)

    if request.method == 'POST':
        assinatura_data = (request.POST.get('assinatura_data') or '').strip()
        assinatura_nome = (request.POST.get('assinatura_rh_nome') or '').strip()
        assinatura_upload = request.FILES.get('assinatura_upload')
        modo = request.POST.get('modo_assinatura', 'desenho')

        if not assinatura_nome:
            assinatura_nome = request.user.get_full_name() or request.user.username

        # Valida de acordo com o modo escolhido
        if modo == 'upload' and not assinatura_upload:
            messages.error(request, 'Selecione um arquivo de imagem para a assinatura.')
            return render(request, 'cadastros/rh/aso_solicitacao_assinar.html', {'solicitacao': solicitacao})

        if modo == 'desenho' and not assinatura_data:
            messages.error(request, 'Desenhe a assinatura antes de salvar.')
            return render(request, 'cadastros/rh/aso_solicitacao_assinar.html', {'solicitacao': solicitacao})

        try:
            if modo == 'upload':
                filename = f'assinatura_aso_{solicitacao.pk}_{uuid4().hex[:8]}.png'
                solicitacao.assinatura_rh_imagem.save(filename, assinatura_upload, save=False)
            else:
                if ',' in assinatura_data:
                    _, assinatura_b64 = assinatura_data.split(',', 1)
                else:
                    assinatura_b64 = assinatura_data
                assinatura_bin = base64.b64decode(assinatura_b64)
                filename = f'assinatura_aso_{solicitacao.pk}_{uuid4().hex[:8]}.png'
                solicitacao.assinatura_rh_imagem.save(filename, ContentFile(assinatura_bin), save=False)

            solicitacao.assinatura_rh_nome = assinatura_nome
            solicitacao.assinatura_rh_datahora = timezone.now()
            if solicitacao.status == 'RASCUNHO':
                solicitacao.status = 'ASSINADO'
            solicitacao.save()

            messages.success(request, 'Solicitação assinada com sucesso!')
            return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)
        except Exception:
            messages.error(request, 'Não foi possível processar a assinatura eletrônica.')

    return render(request, 'cadastros/rh/aso_solicitacao_assinar.html', {
        'solicitacao': solicitacao,
    })


def _gerar_pdf_solicitacao_aso(solicitacao, empresa, salvar_arquivo=True):
    """Gera o PDF da solicitacao ASO e opcionalmente salva no model."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=86, bottomMargin=66)
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'TituloASO',
        parent=styles['Heading1'],
        fontSize=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#1d4ed8'),
        spaceAfter=6,
    )

    secao_style = ParagraphStyle(
        'SecaoASO',
        parent=styles['Heading3'],
        fontSize=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor('#111827'),
        spaceAfter=3,
    )

    texto_style = ParagraphStyle(
        'TextoASO',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#374151'),
        spaceAfter=2,
    )

    cnpj = empresa.get_cnpj_formatado() if hasattr(empresa, 'get_cnpj_formatado') else empresa.cnpj
    cidade_uf = ' / '.join(p for p in [empresa.cidade, empresa.uf] if p)
    endereco_partes = [p for p in [empresa.endereco, empresa.bairro, cidade_uf] if p]
    endereco_texto = ', '.join(endereco_partes) if endereco_partes else '-'
    telefone_texto = empresa.telefone or '-'
    cnpj_texto = cnpj or '-'
    rodape_linha1 = f'{empresa.nome} | CNPJ: {cnpj_texto} | Telefone: {telefone_texto}'
    rodape_linha2 = f'Endereço: {endereco_texto}'

    def _texto_ajustado(canvas, text, max_width, font_name='Helvetica', font_size=7):
        canvas.setFont(font_name, font_size)
        if canvas.stringWidth(text, font_name, font_size) <= max_width:
            return text
        suffix = '...'
        while text and canvas.stringWidth(text + suffix, font_name, font_size) > max_width:
            text = text[:-1]
        return text + suffix if text else suffix

    def _desenhar_cabecalho_rodape(canvas, doc_obj):
        canvas.saveState()
        page_width, page_height = A4

        # Cabeçalho com logo da empresa, quando disponível
        logo_x = doc_obj.leftMargin
        logo_y = page_height - 70
        logo_width = 165
        logo_height = 46
        if getattr(empresa, 'logo', None):
            try:
                empresa.logo.open('rb')
                logo_bytes = empresa.logo.read()
                empresa.logo.close()
                if logo_bytes:
                    canvas.drawImage(
                        ImageReader(io.BytesIO(logo_bytes)),
                        logo_x,
                        logo_y,
                        width=logo_width,
                        height=logo_height,
                        preserveAspectRatio=True,
                        anchor='sw',
                        mask='auto',
                    )
            except Exception:
                # Se houver falha na leitura da logo, segue com o PDF sem interromper a geração.
                pass

        # Texto institucional no cabeçalho (lado direito)
        header_right_x = page_width - doc_obj.rightMargin
        canvas.setFillColor(colors.HexColor('#1f2937'))
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawRightString(header_right_x, page_height - 38, _texto_ajustado(
            canvas,
            empresa.nome,
            max_width=220,
            font_name='Helvetica-Bold',
            font_size=10,
        ))
        canvas.setFillColor(colors.HexColor('#6b7280'))
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(header_right_x, page_height - 51, 'Autorização de Exame Médico (ASO)')

        canvas.setStrokeColor(colors.HexColor('#d1d5db'))
        canvas.line(doc_obj.leftMargin, page_height - 68, page_width - doc_obj.rightMargin, page_height - 68)

        # Rodapé com dados da empresa (2 linhas para melhor leitura)
        canvas.line(doc_obj.leftMargin, 50, page_width - doc_obj.rightMargin, 50)
        linha1 = _texto_ajustado(
            canvas,
            rodape_linha1,
            max_width=(page_width - doc_obj.leftMargin - doc_obj.rightMargin),
            font_name='Helvetica-Bold',
            font_size=7,
        )
        linha2 = _texto_ajustado(
            canvas,
            rodape_linha2,
            max_width=(page_width - doc_obj.leftMargin - doc_obj.rightMargin),
            font_name='Helvetica',
            font_size=7,
        )
        centro_x = page_width / 2
        canvas.setFillColor(colors.HexColor('#374151'))
        canvas.setFont('Helvetica-Bold', 7)
        canvas.drawCentredString(centro_x, 38, linha1)
        canvas.setFillColor(colors.HexColor('#4b5563'))
        canvas.setFont('Helvetica', 7)
        canvas.drawCentredString(centro_x, 29, linha2)
        canvas.restoreState()

    story = [
        Paragraph('Autorização de Exame Médico (ASO)', titulo_style),
        Paragraph(f'Empresa: {empresa.nome}', texto_style),
        Paragraph(f'Gerado em: {timezone.now().strftime("%d/%m/%Y %H:%M")}', texto_style),
        Spacer(1, 0.08 * inch),
    ]

    dados_esquerda = [
        ['Funcionário', solicitacao.funcionario.nome_completo],
        ['Função', solicitacao.funcionario.funcao.nome if getattr(solicitacao.funcionario, 'funcao', None) else '-'],
        ['Matrícula', solicitacao.funcionario.matricula or '-'],
        ['Nascimento', solicitacao.funcionario.data_nascimento.strftime('%d/%m/%Y') if solicitacao.funcionario.data_nascimento else '-'],
        ['CPF', solicitacao.funcionario.get_cpf_formatado() if hasattr(solicitacao.funcionario, 'get_cpf_formatado') else (solicitacao.funcionario.cpf or '-')],
        ['RG', solicitacao.funcionario.rg or '-'],
        ['Tipo ASO', solicitacao.get_tipo_aso_display()],
    ]

    # Montar endereço do fornecedor/laboratório com quebra de linha
    endereco_lab = '-'
    if solicitacao.laboratorio_nome:
        try:
            fornecedor = Fornecedor.objects.filter(
                empresa=empresa,
                nome_fantasia=solicitacao.laboratorio_nome
            ).first() or Fornecedor.objects.filter(
                empresa=empresa,
                nome=solicitacao.laboratorio_nome
            ).first()
            
            if fornecedor:
                # Tentar usar endereço padrão se existir
                endereco_padrao = fornecedor.enderecos.filter(padrao=True).first()
                if endereco_padrao:
                    linhas_endereco = []
                    # Linha 1: Logradouro + Número
                    linha1 = ', '.join(p for p in [endereco_padrao.logradouro, endereco_padrao.numero] if p)
                    if linha1:
                        linhas_endereco.append(linha1)
                    # Linha 2: Bairro
                    if endereco_padrao.bairro:
                        linhas_endereco.append(endereco_padrao.bairro)
                    # Linha 3: Cidade / UF
                    cidade_uf = ' / '.join(p for p in [endereco_padrao.cidade, endereco_padrao.uf] if p)
                    if cidade_uf:
                        linhas_endereco.append(cidade_uf)
                    endereco_lab = '\n'.join(linhas_endereco) if linhas_endereco else '-'
                else:
                    # Usar campos de endereço direto do fornecedor
                    linhas_endereco = []
                    # Linha 1: Endereço + Número
                    linha1 = ', '.join(p for p in [fornecedor.endereco, fornecedor.numero] if p)
                    if linha1:
                        linhas_endereco.append(linha1)
                    # Linha 2: Bairro
                    if fornecedor.bairro:
                        linhas_endereco.append(fornecedor.bairro)
                    # Linha 3: Cidade / UF
                    cidade_uf = ' / '.join(p for p in [fornecedor.cidade, fornecedor.uf] if p)
                    if cidade_uf:
                        linhas_endereco.append(cidade_uf)
                    endereco_lab = '\n'.join(linhas_endereco) if linhas_endereco else '-'
        except Exception:
            endereco_lab = '-'

    dados_direita = [
        ['Código ASO', str(solicitacao.pk)],
        ['Status', solicitacao.get_status_display()],
        ['Solicitação', solicitacao.data_solicitacao.strftime('%d/%m/%Y') if solicitacao.data_solicitacao else '-'],
        ['Prev. Exame', solicitacao.data_prevista_exame.strftime('%d/%m/%Y') if solicitacao.data_prevista_exame else '-'],
        ['Vencimento', solicitacao.data_vencimento.strftime('%d/%m/%Y') if solicitacao.data_vencimento else '-'],
        ['Laboratório', solicitacao.laboratorio_nome or '-'],
        ['Email', solicitacao.laboratorio_email or '-'],
        ['Endereço Lab', endereco_lab],
        ['WhatsApp', solicitacao.trabalhador_whatsapp or '-'],
    ]

    def _tabela_resumo(dados):
        tabela = Table(dados, colWidths=[1.25 * inch, 2.15 * inch])
        tabela.setStyle(TableStyle([
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#111827')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return tabela

    tabela_duas_colunas = Table(
        [[_tabela_resumo(dados_esquerda), _tabela_resumo(dados_direita)]],
        colWidths=[3.45 * inch, 3.45 * inch]
    )
    tabela_duas_colunas.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(tabela_duas_colunas)
    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph('Riscos Ambientais da Função', secao_style))
    funcao = getattr(solicitacao.funcionario, 'funcao', None)
    riscos_ambientais = []
    if funcao:
        riscos_ambientais = list(
            funcao.riscos_ambientais.filter(ativo=True).select_related('categoria').order_by('categoria__nome', 'agente_especifico')
        )

    if riscos_ambientais:
        riscos_dados = [['Categoria', 'Agente']]
        for risco in riscos_ambientais:
            riscos_dados.append([
                risco.categoria.nome,
                risco.agente_especifico,
            ])

        tabela_riscos = Table(riscos_dados, colWidths=[2.2 * inch, 4.7 * inch])
        tabela_riscos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fff7ed')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#111827')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(tabela_riscos)
    else:
        story.append(Paragraph('Nenhum risco ambiental cadastrado para a função do funcionário.', texto_style))

    story.append(Spacer(1, 0.08 * inch))

    story.append(Paragraph('Exames Solicitados', secao_style))
    exames = list(solicitacao.exames.all())
    if exames:
        exames_texto = ' | '.join([f'{exame.nome} ({exame.codigo})' for exame in exames])
        story.append(Paragraph(exames_texto, texto_style))
    else:
        story.append(Paragraph('Nenhum exame informado.', texto_style))

    if solicitacao.possui_outros_exames and solicitacao.outros_exames_descricao:
        story.append(Spacer(1, 0.04 * inch))
        story.append(Paragraph('Outros Exames', secao_style))
        story.append(Paragraph(solicitacao.outros_exames_descricao, texto_style))

    story.append(Spacer(1, 0.06 * inch))
    story.append(Paragraph('Assinatura RH', secao_style))

    if solicitacao.assinatura_rh_imagem:
        try:
            assinatura_img = RLImage(solicitacao.assinatura_rh_imagem.path, width=2.0 * inch, height=0.7 * inch)
            story.append(assinatura_img)
        except Exception:
            story.append(Paragraph('Assinatura eletrônica registrada (imagem indisponível para renderização).', texto_style))
    else:
        story.append(Paragraph('Solicitação sem assinatura eletrônica.', texto_style))

    story.append(Paragraph(f'Responsável RH: {solicitacao.assinatura_rh_nome or "-"}', texto_style))
    story.append(Paragraph(
        f'Data/Hora da assinatura: {solicitacao.assinatura_rh_datahora.strftime("%d/%m/%Y %H:%M") if solicitacao.assinatura_rh_datahora else "-"}',
        texto_style
    ))

    doc.build(story, onFirstPage=_desenhar_cabecalho_rodape, onLaterPages=_desenhar_cabecalho_rodape)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    nome_arquivo = f'autorizacao_exame_medico_aso_{solicitacao.pk}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    if salvar_arquivo:
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f'Salvando PDF ASO: {nome_arquivo}')
            solicitacao.arquivo_pdf.save(nome_arquivo, ContentFile(pdf_bytes), save=True)
            logger.info(f'PDF ASO salvo com sucesso em: {solicitacao.arquivo_pdf.path}')
        except Exception as e:
            # Se o storage falhar, o PDF ainda deve ser entregue para download.
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'Erro ao salvar PDF ASO: {str(e)}', exc_info=True)

    return nome_arquivo, pdf_bytes


def _registrar_log_envio(solicitacao, canal, destinatario, sucesso, retorno):
    LogEnvioSolicitacaoASO.objects.create(
        solicitacao=solicitacao,
        canal=canal,
        destinatario=destinatario,
        status_envio='SUCESSO' if sucesso else 'FALHA',
        retorno=retorno or '',
    )


@login_required
def aso_solicitacao_pdf(request, pk):
    """Gera PDF da solicitação de ASO e salva cópia no cadastro."""
    empresa = request.user.empresa
    solicitacao = get_object_or_404(
        SolicitacaoASO.objects.filter(empresa=empresa).select_related('funcionario', 'vinculo', 'cadastrado_por').prefetch_related('exames'),
        pk=pk,
    )

    nome_arquivo, pdf_bytes = _gerar_pdf_solicitacao_aso(solicitacao, empresa, salvar_arquivo=True)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
    response.write(pdf_bytes)
    return response


@login_required
def aso_solicitacao_enviar_email(request, pk):
    """Envia a solicitação ASO por email para o laboratório e registra log."""
    if request.method != 'POST':
        return redirect('rh:aso_solicitacao_detail', pk=pk)

    empresa = request.user.empresa
    solicitacao = get_object_or_404(
        SolicitacaoASO.objects.filter(empresa=empresa).select_related('funcionario').prefetch_related('exames'),
        pk=pk,
    )

    destinatario = (solicitacao.laboratorio_email or '').strip()
    if not destinatario:
        msg = 'Informe o email do laboratório na solicitação para realizar o envio.'
        _registrar_log_envio(solicitacao, 'EMAIL', '-', False, msg)
        messages.error(request, msg)
        return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)

    try:
        nome_arquivo, pdf_bytes = _gerar_pdf_solicitacao_aso(solicitacao, empresa, salvar_arquivo=True)

        assunto = f'Autorização de Exame Médico (ASO) - {solicitacao.funcionario.nome_completo} - {empresa.nome}'
        conteudo = f'''
        <html>
            <body>
                <p>Ola,</p>
                <p>Segue em anexo a solicitacao de ASO para o colaborador <strong>{solicitacao.funcionario.nome_completo}</strong>.</p>
                <p>
                    <strong>Tipo de ASO:</strong> {solicitacao.get_tipo_aso_display()}<br>
                    <strong>Data prevista do exame:</strong> {solicitacao.data_prevista_exame.strftime('%d/%m/%Y') if solicitacao.data_prevista_exame else '-'}
                </p>
                <p>Atenciosamente,<br>{empresa.nome}</p>
            </body>
        </html>
        '''

        email = EmailMessage(
            subject=assunto,
            body=conteudo,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            to=[destinatario],
        )
        email.content_subtype = 'html'
        email.attach(nome_arquivo, pdf_bytes, 'application/pdf')
        email.send(fail_silently=False)

        if solicitacao.status in ['RASCUNHO', 'ASSINADO']:
            solicitacao.status = 'ENVIADO'
            solicitacao.save(update_fields=['status', 'data_atualizacao'])

        retorno = 'Email enviado com sucesso.'
        _registrar_log_envio(solicitacao, 'EMAIL', destinatario, True, retorno)
        messages.success(request, retorno)
    except Exception as exc:
        retorno = f'Erro ao enviar email: {exc}'
        _registrar_log_envio(solicitacao, 'EMAIL', destinatario, False, retorno)
        messages.error(request, retorno)

    return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)


@login_required
def aso_solicitacao_enviar_whatsapp(request, pk):
    """Envia mensagem WhatsApp com link da solicitação e registra log."""
    if request.method != 'POST':
        return redirect('rh:aso_solicitacao_detail', pk=pk)

    empresa = request.user.empresa
    solicitacao = get_object_or_404(
        SolicitacaoASO.objects.filter(empresa=empresa).select_related('funcionario').prefetch_related('exames'),
        pk=pk,
    )

    destinatario = (solicitacao.trabalhador_whatsapp or '').strip()
    if not destinatario:
        msg = 'Informe o WhatsApp do trabalhador na solicitação para realizar o envio.'
        _registrar_log_envio(solicitacao, 'WHATSAPP', '-', False, msg)
        messages.error(request, msg)
        return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)

    try:
        if not solicitacao.arquivo_pdf:
            _gerar_pdf_solicitacao_aso(solicitacao, empresa, salvar_arquivo=True)

        twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

        if not all([twilio_account_sid, twilio_auth_token, twilio_phone]):
            raise Exception('Twilio nao esta configurado. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN e TWILIO_PHONE_NUMBER.')

        try:
            from twilio.rest import Client
        except ImportError:
            raise Exception('Twilio nao esta instalado no ambiente. Execute: pip install twilio')

        numero_whatsapp = destinatario
        if not numero_whatsapp.startswith('+'):
            numero_whatsapp = '+' + numero_whatsapp

        pdf_url = request.build_absolute_uri(solicitacao.arquivo_pdf.url) if solicitacao.arquivo_pdf else ''
        mensagem = (
            f'Ola, {solicitacao.funcionario.nome_completo}!\n\n'
            f'Sua solicitacao de ASO ({solicitacao.get_tipo_aso_display()}) foi emitida.\n'
            f'Data prevista do exame: {solicitacao.data_prevista_exame.strftime("%d/%m/%Y") if solicitacao.data_prevista_exame else "-"}\n\n'
            f'Acesse o PDF: {pdf_url}\n\n'
            f'{empresa.nome}'
        )

        client = Client(twilio_account_sid, twilio_auth_token)
        message = client.messages.create(
            from_=f'whatsapp:{twilio_phone}',
            body=mensagem,
            to=f'whatsapp:{numero_whatsapp}',
        )

        if solicitacao.status in ['RASCUNHO', 'ASSINADO']:
            solicitacao.status = 'ENVIADO'
            solicitacao.save(update_fields=['status', 'data_atualizacao'])

        retorno = f'Mensagem WhatsApp enviada com sucesso (ID: {message.sid})'
        _registrar_log_envio(solicitacao, 'WHATSAPP', numero_whatsapp, True, retorno)
        messages.success(request, 'WhatsApp enviado com sucesso!')
    except Exception as exc:
        retorno = f'Erro ao enviar WhatsApp: {exc}'
        _registrar_log_envio(solicitacao, 'WHATSAPP', destinatario, False, retorno)
        messages.error(request, retorno)

    return redirect('rh:aso_solicitacao_detail', pk=solicitacao.pk)


# ============================================================================
# RESCISÕES
# ============================================================================

@login_required
def rescisao_list(request):
    """Lista todas as rescisões"""
    empresa = request.user.empresa
    
    rescisoes = RescisaoContrato.objects.filter(
        empresa=empresa
    ).select_related('funcionario').order_by('-data_desligamento')
    
    # Filtros
    status_filter = request.GET.get('status')
    tipo_filter = request.GET.get('tipo')
    funcionario_filter = request.GET.get('funcionario')
    busca = request.GET.get('q')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    
    if status_filter:
        rescisoes = rescisoes.filter(status=status_filter)
    
    if tipo_filter:
        rescisoes = rescisoes.filter(tipo_rescisao=tipo_filter)
    
    if funcionario_filter:
        rescisoes = rescisoes.filter(funcionario_id=funcionario_filter)
    
    if busca:
        rescisoes = rescisoes.filter(
            Q(funcionario__nome_completo__icontains=busca) |
            Q(motivo_detalhado__icontains=busca)
        )
    
    if data_inicio:
        rescisoes = rescisoes.filter(data_desligamento__gte=data_inicio)
    
    if data_fim:
        rescisoes = rescisoes.filter(data_desligamento__lte=data_fim)
    
    # Paginação
    page_obj, per_page, per_page_options = paginate(request, rescisoes)

    # Funcionários para filtro
    funcionarios = Funcionario.objects.filter(
        empresa=empresa
    ).order_by('nome_completo')

    context = {
        'page_obj': page_obj,
        'funcionarios': funcionarios,
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'funcionario_filter': funcionario_filter,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    
    return render(request, 'cadastros/rh/rescisao_list.html', context)


@login_required
def rescisao_create(request):
    """Criar nova rescisão"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = RescisaoContratoForm(
            request.POST,
            request.FILES,
            empresa=empresa
        )
        if form.is_valid():
            rescisao = form.save(commit=False)
            rescisao.empresa = empresa
            rescisao.cadastrado_por = request.user
            # Calcula valor líquido
            rescisao.valor_liquido = rescisao.calcular_valor_liquido()
            rescisao.save()
            # Atualiza automaticamente o funcionário ao concluir rescisão
            if rescisao.status == 'CONCLUIDA':
                funcionario = rescisao.funcionario
                funcionario.data_demissao = rescisao.data_desligamento
                funcionario.ativo = False
                funcionario.save(update_fields=['data_demissao', 'ativo'])
            # Encerra o vínculo contratual vinculado, se houver
            if rescisao.vinculo and rescisao.status == 'CONCLUIDA':
                rescisao.vinculo.encerrar(rescisao.data_desligamento)
            messages.success(request, 'Rescisão cadastrada com sucesso!')
            return redirect('rh:rescisao_detail', pk=rescisao.pk)
    else:
        form = RescisaoContratoForm(empresa=empresa)
    
    return render(request, 'cadastros/rh/rescisao_form.html', {
        'form': form,
        'title': 'Cadastrar Rescisão'
    })


@login_required
def rescisao_calcular(request):
    """Retorna estimativa automática das verbas rescisórias."""
    empresa = request.user.empresa
    funcionario_id = request.GET.get('funcionario_id')
    tipo_rescisao = request.GET.get('tipo_rescisao')
    data_desligamento = parse_date(request.GET.get('data_desligamento', ''))
    trabalhou_aviso_previo = request.GET.get('trabalhou_aviso_previo', 'true').lower() in {'1', 'true', 'on', 'yes'}
    dias_aviso_previo = request.GET.get('dias_aviso_previo') or 30

    if not funcionario_id or not tipo_rescisao or not data_desligamento:
        return JsonResponse({
            'ok': False,
            'message': 'Informe funcionário, tipo de rescisão e data de desligamento para calcular.'
        }, status=400)

    funcionario = get_object_or_404(
        Funcionario.objects.filter(empresa=empresa),
        pk=funcionario_id
    )

    calculo = RescisaoContrato.calcular_estimativa_verbas(
        funcionario=funcionario,
        tipo_rescisao=tipo_rescisao,
        data_desligamento=data_desligamento,
        trabalhou_aviso_previo=trabalhou_aviso_previo,
        dias_aviso_previo=dias_aviso_previo,
    )

    campos_monetarios = [
        'saldo_salario', 'ferias_vencidas', 'ferias_proporcionais',
        'decimo_terceiro_proporcional', 'aviso_previo_indenizado',
        'multa_fgts', 'outros_valores', 'descontos',
        'valor_total', 'valor_liquido',
    ]

    data = {
        'ok': True,
        'campos': {campo: f"{calculo[campo]:.2f}" for campo in campos_monetarios},
        'direitos': {
            'tem_direito_seguro_desemprego': calculo['tem_direito_seguro_desemprego'],
            'liberar_fgts': calculo['liberar_fgts'],
        },
        'bases': {
            'salario': f"{(funcionario.salario or 0):.2f}",
            'data_admissao': funcionario.data_admissao.strftime('%d/%m/%Y') if funcionario.data_admissao else '-',
            'tipo_contrato': funcionario.get_tipo_contrato_display(),
        },
        'memoria': calculo['memoria'],
    }
    return JsonResponse(data)


@login_required
def vinculos_por_funcionario(request):
    """Lista vínculos do funcionário para preencher select de rescisão."""
    empresa = request.user.empresa
    funcionario_id = request.GET.get('funcionario_id')

    if not funcionario_id:
        return JsonResponse({'ok': True, 'vinculos': []})

    vinculos = VinculoContrato.objects.filter(
        empresa=empresa,
        funcionario_id=funcionario_id
    ).order_by('-data_inicio')

    data = [
        {
            'id': vinculo.id,
            'label': f"{vinculo.get_tipo_contrato_display()} | {vinculo.get_status_display()} | Início: {vinculo.data_inicio.strftime('%d/%m/%Y')}"
        }
        for vinculo in vinculos
    ]
    return JsonResponse({'ok': True, 'vinculos': data})


@login_required
def rescisao_detail(request, pk):
    """Detalhes da rescisão"""
    empresa = request.user.empresa
    rescisao = get_object_or_404(
        RescisaoContrato.objects.filter(empresa=empresa),
        pk=pk
    )
    
    return render(request, 'cadastros/rh/rescisao_detail.html', {
        'rescisao': rescisao
    })


@login_required
def rescisao_update(request, pk):
    """Editar rescisão"""
    empresa = request.user.empresa
    rescisao = get_object_or_404(
        RescisaoContrato.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        form = RescisaoContratoForm(
            request.POST,
            request.FILES,
            instance=rescisao,
            empresa=empresa
        )
        if form.is_valid():
            rescisao = form.save(commit=False)
            # Recalcula valor líquido
            rescisao.valor_liquido = rescisao.calcular_valor_liquido()
            rescisao.save()
            # Atualiza automaticamente o funcionário ao concluir rescisão
            if rescisao.status == 'CONCLUIDA':
                funcionario = rescisao.funcionario
                funcionario.data_demissao = rescisao.data_desligamento
                funcionario.ativo = False
                funcionario.save(update_fields=['data_demissao', 'ativo'])
            # Encerra o vínculo contratual vinculado, se houver
            if rescisao.vinculo and rescisao.status == 'CONCLUIDA':
                rescisao.vinculo.encerrar(rescisao.data_desligamento)
            messages.success(request, 'Rescisão atualizada com sucesso!')
            return redirect('rh:rescisao_detail', pk=rescisao.pk)
    else:
        form = RescisaoContratoForm(instance=rescisao, empresa=empresa)
    
    return render(request, 'cadastros/rh/rescisao_form.html', {
        'form': form,
        'rescisao': rescisao,
        'title': 'Editar Rescisão'
    })


@login_required
def rescisao_delete(request, pk):
    """Excluir rescisão"""
    empresa = request.user.empresa
    rescisao = get_object_or_404(
        RescisaoContrato.objects.filter(empresa=empresa),
        pk=pk
    )
    
    if request.method == 'POST':
        rescisao.delete()
        messages.success(request, 'Rescisão excluída com sucesso!')
        return redirect('rescisao_list')
    
    return render(request, 'cadastros/rh/rescisao_confirm_delete.html', {
        'rescisao': rescisao
    })


@login_required
def relatorio_rh(request):
    """Relatório consolidado de RH com informações de funcionários"""
    empresa = request.user.empresa
    hoje = date.today()
    
    # Buscar todos os funcionários ativos
    funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        ativo=True
    ).order_by('nome_completo')
    
    # Preparar dados para os funcionários
    relatorio_dados = []
    for func in funcionarios:
        # Calcular idade
        hoje = date.today()
        if func.data_nascimento:
            idade = (hoje.year - func.data_nascimento.year -
                    ((hoje.month, hoje.day) < (func.data_nascimento.month, func.data_nascimento.day)))
        else:
            idade = None
        
        # Férias agendadas
        ferias_agendadas = FeriasFuncionario.objects.filter(
            funcionario=func,
            status='AGENDADA'
        ).count()
        
        # Férias em gozo
        ferias_em_gozo = FeriasFuncionario.objects.filter(
            funcionario=func,
            status='EM_GOZO'
        ).count()
        
        # Afastamentos ativos
        afastamentos_ativos = AfastamentoFuncionario.objects.filter(
            funcionario=func,
            status='ATIVO'
        ).count()
        
        # Rescisões (status não concluído)
        rescisoes = RescisaoContrato.objects.filter(
            funcionario=func,
            status__in=['EM_PROCESSO']
        ).count()
        
        relatorio_dados.append({
            'funcionario': func,
            'data_admissao': func.data_admissao,
            'idade': idade,
            'ferias_agendadas': ferias_agendadas,
            'ferias_em_gozo': ferias_em_gozo,
            'afastamentos_ativos': afastamentos_ativos,
            'rescisoes': rescisoes,
            'vinculos_ativos': func.vinculos.filter(status='ATIVO').count(),
            'tem_risco': func.vinculos.filter(status='ATIVO').filter(
                Q(possui_insalubridade=True) | Q(possui_periculosidade=True)
            ).exists(),
        })

    vinculos_ativos = VinculoContrato.objects.filter(empresa=empresa, status='ATIVO').count()
    vinculados_com_risco = VinculoContrato.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).filter(
        Q(possui_insalubridade=True) | Q(possui_periculosidade=True)
    ).count()

    encerramentos_mes = VinculoContrato.objects.filter(
        empresa=empresa,
        status='ENCERRADO',
        data_fim_real__year=hoje.year,
        data_fim_real__month=hoje.month,
    ).count()

    recontratacoes_mes = VinculoContrato.objects.filter(
        empresa=empresa,
        origem='RECONTRATACAO',
        data_inicio__year=hoje.year,
        data_inicio__month=hoje.month,
    ).count()

    laudos_vencidos = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__lt=hoje,
    ).select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade')

    laudos_a_vencer = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__gte=hoje,
        data_validade__lte=hoje + timedelta(days=30),
    ).select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade')

    taxa_rotatividade = 0
    base_turnover = funcionarios.count() + encerramentos_mes
    if base_turnover > 0:
        taxa_rotatividade = round((encerramentos_mes / base_turnover) * 100, 2)
    
    context = {
        'relatorio': relatorio_dados,
        'total_funcionarios': len(relatorio_dados),
        'total_ferias_agendadas': sum(r['ferias_agendadas'] for r in relatorio_dados),
        'total_afastamentos_ativos': sum(r['afastamentos_ativos'] for r in relatorio_dados),
        'total_rescisoes': sum(r['rescisoes'] for r in relatorio_dados),
        'vinculos_ativos': vinculos_ativos,
        'vinculados_com_risco': vinculados_com_risco,
        'encerramentos_mes': encerramentos_mes,
        'recontratacoes_mes': recontratacoes_mes,
        'taxa_rotatividade': taxa_rotatividade,
        'laudos_vencidos': laudos_vencidos,
        'laudos_a_vencer': laudos_a_vencer,
    }
    
    return render(request, 'cadastros/rh/relatorio_rh.html', context)


@login_required
def relatorio_rh_pdf(request):
    """Gerar PDF do relatório RH"""
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    empresa = request.user.empresa
    
    # Buscar todos os funcionários ativos
    funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        ativo=True
    ).order_by('nome_completo')
    
    # Preparar dados para os funcionários
    relatorio_dados = []
    hoje = date.today()
    for func in funcionarios:
        # Calcular idade
        idade = (hoje.year - func.data_nascimento.year - 
                ((hoje.month, hoje.day) < (func.data_nascimento.month, func.data_nascimento.day)))
        
        # Férias agendadas
        ferias_agendadas = FeriasFuncionario.objects.filter(
            funcionario=func,
            status='AGENDADA'
        ).count()
        
        # Férias em gozo
        ferias_em_gozo = FeriasFuncionario.objects.filter(
            funcionario=func,
            status='EM_GOZO'
        ).count()
        
        # Afastamentos ativos
        afastamentos_ativos = AfastamentoFuncionario.objects.filter(
            funcionario=func,
            status='ATIVO'
        ).count()
        
        # Rescisões (status não concluído)
        rescisoes = RescisaoContrato.objects.filter(
            funcionario=func,
            status__in=['EM_PROCESSO']
        ).count()
        
        relatorio_dados.append({
            'funcionario': func,
            'data_admissao': func.data_admissao,
            'idade': idade,
            'ferias_agendadas': ferias_agendadas,
            'ferias_em_gozo': ferias_em_gozo,
            'afastamentos_ativos': afastamentos_ativos,
            'rescisoes': rescisoes,
            'vinculos_ativos': func.vinculos.filter(status='ATIVO').count(),
            'tem_risco': func.vinculos.filter(status='ATIVO').filter(
                Q(possui_insalubridade=True) | Q(possui_periculosidade=True)
            ).exists(),
        })

    vinculos_ativos = VinculoContrato.objects.filter(empresa=empresa, status='ATIVO').count()
    vinculados_com_risco = VinculoContrato.objects.filter(
        empresa=empresa,
        status='ATIVO'
    ).filter(
        Q(possui_insalubridade=True) | Q(possui_periculosidade=True)
    ).count()

    encerramentos_mes = VinculoContrato.objects.filter(
        empresa=empresa,
        status='ENCERRADO',
        data_fim_real__year=hoje.year,
        data_fim_real__month=hoje.month,
    ).count()

    recontratacoes_mes = VinculoContrato.objects.filter(
        empresa=empresa,
        origem='RECONTRATACAO',
        data_inicio__year=hoje.year,
        data_inicio__month=hoje.month,
    ).count()

    taxa_rotatividade = 0
    base_turnover = funcionarios.count() + encerramentos_mes
    if base_turnover > 0:
        taxa_rotatividade = round((encerramentos_mes / base_turnover) * 100, 2)

    laudos_vencidos = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__lt=hoje,
    ).select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade')[:20]

    laudos_a_vencer = LaudoRisco.objects.filter(
        empresa=empresa,
        data_validade__isnull=False,
        data_validade__gte=hoje,
        data_validade__lte=hoje + timedelta(days=30),
    ).select_related('funcao', 'vinculo', 'vinculo__funcionario').order_by('data_validade')[:20]
    
    # Criar resposta PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Relatorio_RH_{}.pdf"'.format(date.today().strftime('%d_%m_%Y'))
    
    # Criar documento
    doc = SimpleDocTemplate(response, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#3b82f6'),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        spaceAfter=3,
        alignment=TA_CENTER,
    )
    
    # Cabeçalho
    story.append(Paragraph('Relatório de RH', title_style))
    story.append(Paragraph(f'Empresa: {empresa.nome}', subtitle_style))
    story.append(Paragraph(f'Data do Relatório: {date.today().strftime("%d/%m/%Y")}', subtitle_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Resumo
    total_funcionarios = len(relatorio_dados)
    total_ferias_agendadas = sum(r['ferias_agendadas'] for r in relatorio_dados)
    total_afastamentos_ativos = sum(r['afastamentos_ativos'] for r in relatorio_dados)
    total_rescisoes = sum(r['rescisoes'] for r in relatorio_dados)
    
    summary_data = [
        ['Funcionários Ativos', 'Férias Agendadas', 'Afastamentos Ativos', 'Rescisões em Processo'],
        [str(total_funcionarios), str(total_ferias_agendadas), str(total_afastamentos_ativos), str(total_rescisoes)]
    ]
    
    summary_table = Table(summary_data, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.15*inch))

    summary_data_2 = [
        ['Vínculos Ativos', 'Com Risco', 'Recontratações/Mês', 'Rotatividade (%)'],
        [str(vinculos_ativos), str(vinculados_com_risco), str(recontratacoes_mes), f'{taxa_rotatividade}%']
    ]

    summary_table_2 = Table(summary_data_2, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 1.8*inch])
    summary_table_2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1d4ed8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#eff6ff')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 11),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(summary_table_2)
    story.append(Spacer(1, 0.3*inch))
    
    # Tabela de funcionários
    table_data = [
        ['Nome do Funcionário', 'Data Admissão', 'Idade', 'Férias Agendadas', 'Férias em Gozo', 'Afastamentos', 'Rescisões']
    ]
    
    for item in relatorio_dados:
        table_data.append([
            item['funcionario'].nome_completo[:30],
            item['data_admissao'].strftime('%d/%m/%Y') if item['data_admissao'] else '—',
            str(item['idade']),
            str(item['ferias_agendadas']) if item['ferias_agendadas'] > 0 else '—',
            str(item['ferias_em_gozo']) if item['ferias_em_gozo'] > 0 else '—',
            str(item['afastamentos_ativos']) if item['afastamentos_ativos'] > 0 else '—',
            str(item['rescisoes']) if item['rescisoes'] > 0 else '—',
        ])
    
    # Criar tabela com widths
    colWidths = [2.2*inch, 1.2*inch, 0.7*inch, 1.0*inch, 1.0*inch, 0.9*inch, 0.8*inch]
    t = Table(table_data, colWidths=colWidths)
    
    # Estilo da tabela
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    story.append(t)
    story.append(Spacer(1, 0.3*inch))

    secao_style = ParagraphStyle(
        'Secao',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#b91c1c'),
        spaceAfter=6,
        alignment=TA_LEFT,
    )

    texto_style = ParagraphStyle(
        'TextoSecao',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        spaceAfter=3,
        alignment=TA_LEFT,
    )

    story.append(Paragraph('Laudos Vencidos', secao_style))
    if laudos_vencidos:
        for laudo in laudos_vencidos:
            funcionario_laudo = ''
            if laudo.vinculo and laudo.vinculo.funcionario:
                funcionario_laudo = f' - {laudo.vinculo.funcionario.nome_completo}'
            story.append(Paragraph(
                f'• {laudo.funcao.nome} ({laudo.get_tipo_laudo_display()}) - vencido em {laudo.data_validade.strftime("%d/%m/%Y")}{funcionario_laudo}',
                texto_style
            ))
    else:
        story.append(Paragraph('Nenhum laudo vencido.', texto_style))

    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph('Laudos a Vencer em 30 Dias', secao_style))
    if laudos_a_vencer:
        for laudo in laudos_a_vencer:
            funcionario_laudo = ''
            if laudo.vinculo and laudo.vinculo.funcionario:
                funcionario_laudo = f' - {laudo.vinculo.funcionario.nome_completo}'
            story.append(Paragraph(
                f'• {laudo.funcao.nome} ({laudo.get_tipo_laudo_display()}) - vence em {laudo.data_validade.strftime("%d/%m/%Y")}{funcionario_laudo}',
                texto_style
            ))
    else:
        story.append(Paragraph('Nenhum laudo a vencer nos próximos 30 dias.', texto_style))

    story.append(Spacer(1, 0.2*inch))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#999999'),
        alignment=TA_CENTER,
    )
    story.append(Paragraph(f'Gerado em {date.today().strftime("%d/%m/%Y %H:%M")}', footer_style))
    
    # Gerar PDF
    doc.build(story)
    
    return response


# ============================================================================
# VIEWS DE FUNCIONÁRIO E FUNÇÃO (movidas de cadastros/views.py)
# ============================================================================
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from cadastros.models import Fazenda
from rh.models import RiscoAmbientalCatalogo, CategoriaRiscoAmbiental
from rh.forms import (
    FuncionarioForm, DocumentoFuncionarioForm, FuncaoFuncionarioForm,
    DocumentoFuncionarioFormSet, RiscoAmbientalCatalogoForm,
)

@login_required
def funcionario_documento_create(request, funcionario_pk):
    """Adiciona documento ao funcionário"""
    funcionario = get_object_or_404(Funcionario, pk=funcionario_pk, empresa=request.user.empresa)
    if request.method == 'POST':
        form = DocumentoFuncionarioForm(request.POST, request.FILES)
        if form.is_valid():
            documento = form.save(commit=False)
            documento.funcionario = funcionario
            documento.empresa = request.user.empresa
            documento.enviado_por = request.user
            documento.save()
            messages.success(request, '✅ Documento anexado ao funcionário!')
            return redirect('rh:funcionario_detail', pk=funcionario.pk)
    else:
        form = DocumentoFuncionarioForm()
    return render(request, 'cadastros/funcionario/documento_form.html', {
        'form': form,
        'funcionario': funcionario,
        'action': 'Adicionar'
    })




# ==================== FUNÇÕES ====================

@login_required
def funcao_list(request):
    """Lista funções de funcionários"""
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa)

    q = request.GET.get('q', '').strip()
    if q:
        funcoes = funcoes.filter(nome__icontains=q)

    page_obj, per_page, per_page_options = paginate(request, funcoes.order_by('nome'))

    return render(request, 'cadastros/funcao/funcao_list.html', {
        'funcoes': page_obj,
        'page_obj': page_obj,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def risco_ambiental_catalogo_list(request):
    """Lista itens do catálogo de riscos ambientais da empresa."""
    empresa = request.user.empresa
    CategoriaRiscoAmbiental.criar_categorias_padrao_empresa(empresa)

    itens = RiscoAmbientalCatalogo.objects.filter(empresa=empresa).select_related('categoria')

    q = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria')
    status = request.GET.get('status', '').strip()

    if q:
        itens = itens.filter(Q(nome__icontains=q) | Q(epi_padrao__icontains=q) | Q(observacoes__icontains=q))
    if categoria_id:
        itens = itens.filter(categoria_id=categoria_id)
    if status == 'ativos':
        itens = itens.filter(ativo=True)
    elif status == 'inativos':
        itens = itens.filter(ativo=False)

    categorias = CategoriaRiscoAmbiental.objects.filter(empresa=empresa, ativo=True).order_by('nome')

    page_obj, per_page, per_page_options = paginate(request, itens.order_by('categoria__nome', 'nome'))

    return render(request, 'cadastros/risco_ambiental_catalogo/catalogo_list.html', {
        'itens': page_obj,
        'page_obj': page_obj,
        'categorias': categorias,
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def risco_ambiental_catalogo_create(request):
    """Cria item do catálogo de riscos ambientais."""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = RiscoAmbientalCatalogoForm(request.POST, empresa=empresa)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'✅ Item "{item.nome}" adicionado ao catálogo de riscos.')
            return redirect('rh:risco_ambiental_catalogo_list')
    else:
        form = RiscoAmbientalCatalogoForm(empresa=empresa)

    return render(request, 'cadastros/risco_ambiental_catalogo/catalogo_form.html', {
        'form': form,
        'action': 'Cadastrar',
    })


@login_required
def risco_ambiental_catalogo_update(request, pk):
    """Edita item do catálogo de riscos ambientais."""
    empresa = request.user.empresa
    item = get_object_or_404(RiscoAmbientalCatalogo, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = RiscoAmbientalCatalogoForm(request.POST, instance=item, empresa=empresa)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'✅ Item "{item.nome}" atualizado com sucesso.')
            return redirect('rh:risco_ambiental_catalogo_list')
    else:
        form = RiscoAmbientalCatalogoForm(instance=item, empresa=empresa)

    return render(request, 'cadastros/risco_ambiental_catalogo/catalogo_form.html', {
        'form': form,
        'item': item,
        'action': 'Editar',
    })


@login_required
def risco_ambiental_catalogo_delete(request, pk):
    """Exclui item do catálogo de riscos ambientais."""
    empresa = request.user.empresa
    item = get_object_or_404(RiscoAmbientalCatalogo, pk=pk, empresa=empresa)

    if request.method == 'POST':
        nome = item.nome
        item.delete()
        messages.success(request, f'🗑️ Item "{nome}" removido do catálogo.')
        return redirect('rh:risco_ambiental_catalogo_list')

    return render(request, 'cadastros/risco_ambiental_catalogo/catalogo_confirm_delete.html', {'item': item})


@login_required
def funcao_create_ajax(request):
    """Cria função via AJAX (para modal)"""
    if request.method == 'POST':
        form = FuncaoFuncionarioForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.empresa = request.user.empresa
            funcao.save()
            form.instance = funcao
            form._salvar_riscos_ambientais(funcao, request.user.empresa)
            
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
        form = FuncaoFuncionarioForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            funcao = form.save(commit=False)
            funcao.empresa = request.user.empresa
            funcao.save()
            form.instance = funcao
            form._salvar_riscos_ambientais(funcao, request.user.empresa)
            messages.success(request, f'✅ Função "{funcao.nome}" criada com sucesso!')
            return redirect('rh:funcao_list')
    else:
        form = FuncaoFuncionarioForm(empresa=request.user.empresa)
    return render(request, 'cadastros/funcao/funcao_form.html', {'form': form, 'action': 'Cadastrar'})


@login_required
@login_required
def funcao_get_salario(request):
    """Retorna o salário base de uma função via AJAX"""
    if request.method == 'GET':
        funcao_id = request.GET.get('funcao_id')
        
        if not funcao_id:
            return JsonResponse({'erro': 'ID da função não fornecido'}, status=400)
        
        try:
            funcao = FuncaoFuncionario.objects.get(
                id=funcao_id,
                empresa=request.user.empresa
            )
            return JsonResponse({
                'sucesso': True,
                'salario_base': float(funcao.salario_base) if funcao.salario_base else 0
            })
        except FuncaoFuncionario.DoesNotExist:
            return JsonResponse({'erro': 'Função não encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'erro': str(e)}, status=500)
    
    return JsonResponse({'erro': 'Método não permitido'}, status=405)


def funcao_update(request, pk):
    """Editar função de funcionário"""
    funcao = get_object_or_404(FuncaoFuncionario, pk=pk, empresa=request.user.empresa)
    if request.method == 'POST':
        salario_base_anterior = funcao.salario_base
        form = FuncaoFuncionarioForm(request.POST, instance=funcao, empresa=request.user.empresa)
        if form.is_valid():
            aplicar_reajuste_todos = request.POST.get('aplicar_reajuste_todos') == 'on'
            funcao = form.save()

            reajustes_aplicados = 0
            if (
                aplicar_reajuste_todos
                and salario_base_anterior != funcao.salario_base
                and funcao.salario_base is not None
            ):
                funcionarios = Funcionario.objects.filter(
                    empresa=request.user.empresa,
                    funcao=funcao,
                )

                with transaction.atomic():
                    for funcionario in funcionarios:
                        salario_antigo = funcionario.salario
                        salario_novo = funcao.salario_base

                        if salario_antigo == salario_novo:
                            continue

                        funcionario.salario = salario_novo
                        funcionario.save(update_fields=['salario'])

                        HistoricoFuncionario.objects.create(
                            funcionario=funcionario,
                            tipo_evento='MUDANCA_SALARIO',
                            funcao=funcao,
                            salario=salario_novo,
                            motivo=(
                                f'Reajuste em lote aplicado pela função "{funcao.nome}". '
                                f'Salário anterior: R$ {salario_antigo}. '
                                f'Novo salário: R$ {salario_novo}.'
                            ),
                            usuario=request.user,
                        )
                        reajustes_aplicados += 1

            messages.success(request, f'✅ Função "{funcao.nome}" atualizada!')
            if reajustes_aplicados > 0:
                messages.info(
                    request,
                    f'ℹ️ Reajuste aplicado automaticamente para {reajustes_aplicados} funcionário(s).'
                )
            return redirect('rh:funcao_list')
    else:
        form = FuncaoFuncionarioForm(instance=funcao, empresa=request.user.empresa)
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
            return redirect('rh:funcao_list')
        except ProtectedError:
            empregados = funcao.funcionarios.all()
            sample = ', '.join([str(e) for e in empregados[:10]])
            messages.error(request, f'❌ Não é possível excluir a função porque está atribuída a funcionários: {sample}')
            return redirect('rh:funcao_list')
    return render(request, 'cadastros/funcao/funcao_confirm_delete.html', {'funcao': funcao})


# ==================== FUNCIONÁRIOS ====================

@login_required
def ajax_buscar_funcionarios(request):
    """Combobox unificado (Select2 AJAX paginado, 10 por página): q vazio
    retorna a primeira página sem filtro; digitar busca por nome, matrícula
    ou função."""
    from core.select2 import select2_response

    q = request.GET.get('q', '').strip()
    empresa = request.user.empresa
    qs = Funcionario.objects.filter(empresa=empresa, ativo=True).select_related('funcao')
    ids = [i for i in request.GET.get('ids', '').split(',') if i]
    if ids:
        qs = qs.filter(pk__in=ids)
    if q:
        qs = qs.filter(
            Q(nome_completo__icontains=q) | Q(matricula__icontains=q) | Q(funcao__nome__icontains=q)
        )
    qs = qs.order_by('nome_completo')

    def serialize(f):
        return {'id': f.pk, 'text': str(f)}

    return select2_response(request, qs, serialize)


@login_required
def funcionario_list(request):
    """Lista funcionários"""
    # Busca e filtros
    q = request.GET.get('q', '').strip()
    fazenda_id = request.GET.get('fazenda', '')
    funcao_id = request.GET.get('funcao', '')

    # Todos funcionários (ativos e inativos juntos)
    funcionarios = Funcionario.objects.filter(empresa=request.user.empresa)
    total_ativos = funcionarios.filter(ativo=True).count()

    # Filtro de status (ativos/inativos)
    status = request.GET.get('status', '').strip()
    if status == 'ativos':
        funcionarios = funcionarios.filter(ativo=True)
    elif status == 'inativos':
        funcionarios = funcionarios.filter(ativo=False)

    if q:
        funcionarios = funcionarios.filter(
            Q(nome_completo__icontains=q) |
            Q(cpf__icontains=q) |
            Q(matricula__icontains=q) |
            Q(funcao__nome__icontains=q)
        )
    if fazenda_id:
        funcionarios = funcionarios.filter(fazenda_id=fazenda_id)
    if funcao_id:
        funcionarios = funcionarios.filter(funcao_id=funcao_id)
    page_obj, per_page, per_page_options = paginate(request, funcionarios)

    fazendas = Fazenda.objects.filter(empresa=request.user.empresa, ativa=True)
    funcoes = FuncaoFuncionario.objects.filter(empresa=request.user.empresa, ativa=True)
    context = {
        'page_obj': page_obj,
        'fazendas': fazendas,
        'funcoes': funcoes,
        'total_funcionarios': funcionarios.count(),
        'total_ativos': total_ativos,
        'per_page': per_page,
        'per_page_options': per_page_options,
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

    historicos_salariais = funcionario.historicos.filter(
        tipo_evento='MUDANCA_SALARIO'
    ).select_related('usuario', 'funcao').order_by('-data_evento')

    vinculos_contratuais = VinculoContrato.objects.filter(
        empresa=request.user.empresa,
        funcionario=funcionario
    ).select_related('funcao').order_by('-data_inicio')

    data_inicio = (request.GET.get('data_inicio') or '').strip()
    data_fim = (request.GET.get('data_fim') or '').strip()

    if data_inicio:
        try:
            historicos_salariais = historicos_salariais.filter(data_evento__gte=data_inicio)
        except Exception:
            pass
    if data_fim:
        try:
            historicos_salariais = historicos_salariais.filter(data_evento__lte=data_fim)
        except Exception:
            pass

    export = (request.GET.get('export') or '').strip().lower()
    if export == 'csv':
        import csv

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = (
            f'attachment; filename="historico_reajustes_funcionario_{funcionario.pk}.csv"'
        )

        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Data', 'Tipo', 'Funcao', 'Salario', 'Responsavel', 'Motivo'])

        for hist in historicos_salariais:
            writer.writerow([
                hist.data_evento.strftime('%d/%m/%Y') if hist.data_evento else '',
                hist.get_tipo_evento_display(),
                hist.funcao.nome if hist.funcao else '',
                f'{hist.salario:.2f}' if hist.salario is not None else '0.00',
                hist.usuario.username if hist.usuario else 'Sistema',
                (hist.motivo or '').replace('\n', ' ').strip(),
            ])

        return response

    historicos_salariais = historicos_salariais[:20]
    
    return render(request, 'cadastros/funcionario/funcionario_detail.html', {
        'funcionario': funcionario,
        'historicos_salariais': historicos_salariais,
        'vinculos_contratuais': vinculos_contratuais,
        'filtro_data_inicio': data_inicio,
        'filtro_data_fim': data_fim,
    })


@login_required
def funcionario_create(request):
    """Cria funcionário com múltiplos documentos via formset"""
    if request.method == 'POST':
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            empresa=request.user.empresa,
            usuario=request.user
        )
        
        if form.is_valid():
            funcionario = form.save()
            
            # Processa formset de documentos (se houver anexos na criação)
            formset = DocumentoFuncionarioFormSet(request.POST, request.FILES, instance=funcionario)
            if formset.is_valid():
                # Atribui empresa e enviado_por a cada documento
                for form_doc in formset:
                    if form_doc.cleaned_data and not form_doc.cleaned_data.get('DELETE', False):
                        # Se há dados e não é uma exclusão
                        doc = form_doc.save(commit=False)
                        doc.funcionario = funcionario
                        doc.empresa = request.user.empresa
                        doc.enviado_por = request.user
                        doc.save()
                
                messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" cadastrado com sucesso!')
                return redirect('rh:funcionario_detail', pk=funcionario.pk)
            else:
                # Se formset tem erros, mantém display de erros
                messages.warning(request, 'Funcionário cadastrado mas há erros nos documentos. Você pode adicioná-los depois.')
                return redirect('rh:funcionario_detail', pk=funcionario.pk)
        else:
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
        formset = DocumentoFuncionarioFormSet()
    
    # Para o modal de nova função
    form_funcao = FuncaoFuncionarioForm(empresa=request.user.empresa)
    
    return render(request, 'cadastros/funcionario/funcionario_form.html', {
        'form': form,
        'formset': formset,
        'form_funcao': form_funcao,
        'action': 'Cadastrar'
    })


@login_required
def funcionario_update(request, pk):
    """Edita funcionário com múltiplos documentos via formset"""
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        salario_anterior = funcionario.salario
        funcao_anterior = funcionario.funcao
        form = FuncionarioForm(
            request.POST,
            request.FILES,
            instance=funcionario,
            empresa=request.user.empresa,
            usuario=request.user
        )
        
        if form.is_valid():
            funcionario = form.save()

            if salario_anterior != funcionario.salario:
                motivo = (
                    f'Alteração manual no cadastro do funcionário. '
                    f'Salário anterior: R$ {salario_anterior}. '
                    f'Novo salário: R$ {funcionario.salario}.'
                )
                if funcao_anterior != funcionario.funcao:
                    motivo += (
                        f' Função alterada de "{funcao_anterior.nome}" '
                        f'para "{funcionario.funcao.nome}".'
                    )

                HistoricoFuncionario.objects.create(
                    funcionario=funcionario,
                    tipo_evento='MUDANCA_SALARIO',
                    funcao=funcionario.funcao,
                    salario=funcionario.salario,
                    motivo=motivo,
                    usuario=request.user,
                )
            
            # Processa formset de documentos
            formset = DocumentoFuncionarioFormSet(request.POST, request.FILES, instance=funcionario)
            if formset.is_valid():
                # Salva formset (dele)
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.empresa = request.user.empresa
                    instance.enviado_por = request.user
                    instance.save()
                
                # Processa exclusões (DELETE)
                for form_doc in formset.deleted_forms:
                    form_doc.instance.delete()
                
                messages.success(request, f'✅ Funcionário "{funcionario.nome_completo}" atualizado!')
                return redirect('rh:funcionario_detail', pk=funcionario.pk)
            else:
                # Se formset tem erros, mostra mensagem mas salva funcionário
                messages.warning(request, 'Funcionário atualizado mas há erros nos documentos.')
                return redirect('rh:funcionario_detail', pk=funcionario.pk)
        else:
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
        formset = DocumentoFuncionarioFormSet(instance=funcionario)
    
    form_funcao = FuncaoFuncionarioForm(empresa=request.user.empresa)
    
    return render(request, 'cadastros/funcionario/funcionario_form.html', {
        'form': form,
        'formset': formset,
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
        return redirect('rh:funcionario_list')

    return render(request, 'cadastros/funcionario/funcionario_confirm_delete.html', {
        'funcionario': funcionario
    })


def funcionario_set_pin(request, pk):
    """Define PIN e ativa acesso ao Portal do Campo (login unificado via Usuario) para um funcionário."""
    from django.contrib.auth.models import Group
    from usuarios.models import Usuario
    from .services.funcionario_portal import gerar_username_funcionario

    empresa = request.user.empresa
    funcionario = get_object_or_404(Funcionario, pk=pk, empresa=empresa)

    if request.method == 'POST':
        pin = request.POST.get('pin', '').strip()
        pin2 = request.POST.get('pin2', '').strip()
        portal_ativo = request.POST.get('portal_ativo') == '1'

        if not funcionario.usuario_vinculado_id and not pin:
            messages.error(request, 'Defina um PIN para o primeiro acesso deste funcionário.')
        elif pin and pin != pin2:
            messages.error(request, 'Os PINs não coincidem.')
        elif pin and not pin.isdigit():
            messages.error(request, 'O PIN deve conter apenas números.')
        elif pin and len(pin) < 4:
            messages.error(request, 'O PIN deve ter pelo menos 4 dígitos.')
        else:
            funcionario.portal_ativo = portal_ativo
            usuario = funcionario.usuario_vinculado

            if not usuario:
                username = gerar_username_funcionario(empresa.pk, funcionario.cpf)
                nome_partes = funcionario.nome_completo.strip().split(' ', 1)
                usuario = Usuario(
                    username=username,
                    first_name=nome_partes[0],
                    last_name=nome_partes[1] if len(nome_partes) > 1 else '',
                    empresa=empresa,
                    tipo='FUNC_CAMPO',
                    is_active=funcionario.ativo,
                )
                usuario.set_password(pin)
                usuario.save()

                grupo, _ = Group.objects.get_or_create(name='FUNC_CAMPO')
                usuario.groups.add(grupo)

                funcionario.usuario_vinculado = usuario
            else:
                if pin:
                    usuario.set_password(pin)
                usuario.is_active = funcionario.ativo
                usuario.save()

            funcionario.save(update_fields=['portal_ativo', 'usuario_vinculado'])
            messages.success(
                request,
                f'Acesso ao Portal do Campo configurado para {funcionario.nome_completo}. '
                f'Login: "{usuario.username}" (informe ao funcionário junto com o PIN).'
            )
            return redirect('rh:funcionario_detail', pk=funcionario.pk)

    return render(request, 'cadastros/funcionario/set_pin_portal.html', {
        'funcionario': funcionario,
        'title': f'Portal do Campo — {funcionario.nome_completo}',
    })

