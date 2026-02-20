"""
Views para Controle de RH
Férias, Afastamentos e Rescisões de Funcionários
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from datetime import date, timedelta

from .models import (
    Funcionario, FeriasFuncionario, AfastamentoFuncionario, 
    RescisaoContrato
)
from .forms import (
    FeriasFuncionarioForm, AfastamentoFuncionarioForm,
    RescisaoContratoForm
)


# ============================================================================
# DASHBOARD RH
# ============================================================================

@login_required
def rh_dashboard(request):
    """Dashboard geral de RH"""
    empresa = request.user.empresa
    
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
    paginator = Paginator(ferias, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
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
    }
    
    return render(request, 'cadastros/rh/ferias_list.html', context)


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
            return redirect('cadastros:ferias_detail', pk=ferias.pk)
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
            return redirect('cadastros:ferias_detail', pk=ferias.pk)
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
        return redirect('cadastros:ferias_list')
    
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
    paginator = Paginator(afastamentos, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
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
            return redirect('cadastros:afastamento_detail', pk=afastamento.pk)
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
            return redirect('cadastros:afastamento_detail', pk=afastamento.pk)
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
        return redirect('cadastros:afastamento_list')
    
    return render(request, 'cadastros/rh/afastamento_confirm_delete.html', {
        'afastamento': afastamento
    })


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
    paginator = Paginator(rescisoes, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    
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
            messages.success(request, 'Rescisão cadastrada com sucesso!')
            return redirect('cadastros:rescisao_detail', pk=rescisao.pk)
    else:
        form = RescisaoContratoForm(empresa=empresa)
    
    return render(request, 'cadastros/rh/rescisao_form.html', {
        'form': form,
        'title': 'Cadastrar Rescisão'
    })


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
            messages.success(request, 'Rescisão atualizada com sucesso!')
            return redirect('cadastros:rescisao_detail', pk=rescisao.pk)
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
        })
    
    context = {
        'relatorio': relatorio_dados,
        'total_funcionarios': len(relatorio_dados),
        'total_ferias_agendadas': sum(r['ferias_agendadas'] for r in relatorio_dados),
        'total_afastamentos_ativos': sum(r['afastamentos_ativos'] for r in relatorio_dados),
        'total_rescisoes': sum(r['rescisoes'] for r in relatorio_dados),
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
    for func in funcionarios:
        # Calcular idade
        hoje = date.today()
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
        })
    
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
