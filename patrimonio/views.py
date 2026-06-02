"""
Views do módulo Patrimônio
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.utils.text import slugify
from datetime import date
from decimal import Decimal
from xhtml2pdf import pisa
from io import BytesIO
from openpyxl import Workbook

from .models import Patrimonio, PatrimonioMovimentacao, PatrimonioAuditoria, PatrimonioAuditoriaItem
from .forms import (
    PatrimonioForm,
    PatrimonioVeiculoExportForm,
    PatrimonioMovimentacaoForm,
    PatrimonioAuditoriaForm,
    PatrimonioAuditoriaItemForm,
)
from frota.models import Vehicle
from rh.models import Funcionario


@login_required
def patrimonio_list(request):
    """Lista todos os patrimônios da empresa"""
    empresa = request.user.empresa
    
    # Filtros
    categoria = request.GET.get('categoria', '')
    estado = request.GET.get('estado', '')
    ativo = request.GET.get('ativo', '1')
    busca = request.GET.get('q', '')
    
    patrimonios = Patrimonio.objects.filter(empresa=empresa)
    
    if categoria:
        patrimonios = patrimonios.filter(categoria=categoria)
    if estado:
        patrimonios = patrimonios.filter(estado=estado)
    if ativo:
        patrimonios = patrimonios.filter(ativo=ativo == '1')
    if busca:
        patrimonios = patrimonios.filter(
            Q(numero_patrimonio__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(localizacao__icontains=busca)
        )
    
    # Paginação
    from django.core.paginator import Paginator
    paginator = Paginator(patrimonios, 25)
    page = request.GET.get('page', 1)
    page_obj = paginator.get_page(page)
    
    # Estatísticas
    total_valor = patrimonios.aggregate(Sum('valor_inicial'))['valor_inicial__sum'] or Decimal('0.00')
    total_ativo = patrimonios.aggregate(Sum('valor_atual'))['valor_atual__sum'] or Decimal('0.00')
    total_depreciacao = total_valor - total_ativo
    
    context = {
        'page_obj': page_obj,
        'patrimonios': page_obj.object_list,
        'categorias': Patrimonio.CATEGORIA_CHOICES,
        'estados': Patrimonio.ESTADO_CHOICES,
        'filtro_categoria': categoria,
        'filtro_estado': estado,
        'filtro_ativo': ativo,
        'busca': busca,
        'total_valor': total_valor,
        'total_ativo': total_ativo,
        'total_depreciacao': total_depreciacao,
        'total_patrimonios': patrimonios.count(),
    }
    
    return render(request, 'patrimonio/patrimonio_list.html', context)


@login_required
def patrimonio_detail(request, pk):
    """Visualiza detalhes de um patrimônio"""
    patrimonio = get_object_or_404(Patrimonio, pk=pk, empresa=request.user.empresa)
    
    # Calcular depreciação atual
    patrimonio.atualizar_valor_atual()
    depreciacao_acumulada = patrimonio.calcular_depreciacao_acumulada()
    percentual_depreciacao = (depreciacao_acumulada / patrimonio.valor_inicial * 100) if patrimonio.valor_inicial else 0
    
    movimentacoes = patrimonio.movimentacoes.all()[:10]
    
    context = {
        'patrimonio': patrimonio,
        'depreciacao_acumulada': depreciacao_acumulada,
        'percentual_depreciacao': percentual_depreciacao,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'patrimonio/patrimonio_detail.html', context)


@login_required
def patrimonio_create(request):
    """Cria novo patrimônio"""
    if request.method == 'POST':
        form = PatrimonioForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            patrimonio = form.save(commit=True, user=request.user)
            messages.success(request, f'Patrimônio {patrimonio.numero_patrimonio} criado com sucesso!')
            return redirect('patrimonio:patrimonio_detail', pk=patrimonio.pk)
    else:
        form = PatrimonioForm(empresa=request.user.empresa)
    
    context = {'form': form, 'action': 'Novo'}
    return render(request, 'patrimonio/patrimonio_form.html', context)


@login_required
def patrimonio_edit(request, pk):
    """Edita um patrimônio"""
    patrimonio = get_object_or_404(Patrimonio, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = PatrimonioForm(request.POST, instance=patrimonio, empresa=request.user.empresa)
        if form.is_valid():
            patrimonio = form.save(commit=True, user=request.user)
            messages.success(request, f'Patrimônio {patrimonio.numero_patrimonio} atualizado!')
            return redirect('patrimonio:patrimonio_detail', pk=patrimonio.pk)
    else:
        form = PatrimonioForm(instance=patrimonio, empresa=request.user.empresa)
    
    context = {'form': form, 'patrimonio': patrimonio, 'action': 'Editar'}
    return render(request, 'patrimonio/patrimonio_form.html', context)


@login_required
def patrimonio_delete(request, pk):
    """Deleta um patrimônio"""
    patrimonio = get_object_or_404(Patrimonio, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        numero = patrimonio.numero_patrimonio
        patrimonio.delete()
        messages.success(request, f'Patrimônio {numero} deletado!')
        return redirect('patrimonio:patrimonio_list')
    
    context = {'patrimonio': patrimonio}
    return render(request, 'patrimonio/patrimonio_confirm_delete.html', context)


@login_required
def patrimonio_from_veiculo(request, vehicle_pk):
    """Exporta um veículo como patrimônio"""
    veiculo = get_object_or_404(Vehicle, pk=vehicle_pk, empresa=request.user.empresa)
    
    # Verificar se já existe patrimônio vinculado
    if hasattr(veiculo, 'patrimonio') and veiculo.patrimonio:
        messages.warning(request, f'Este veículo já está vinculado ao patrimônio {veiculo.patrimonio.numero_patrimonio}')
        return redirect('cadastros:vehicle_detail', pk=veiculo.pk)
    
    if request.method == 'POST':
        form = PatrimonioVeiculoExportForm(request.POST, empresa=request.user.empresa)
        if form.is_valid():
            # Determinar categoria
            if veiculo.tipo == 'IMPLEMENTO':
                categoria = 'IMPLEMENTO'
            else:
                categoria = 'VEICULO'
            
            # Construir localização
            fazenda = form.cleaned_data.get('fazenda')
            localizacao_detalhada = form.cleaned_data.get('localizacao_detalhada', '')
            
            if fazenda and localizacao_detalhada:
                localizacao = f"{fazenda.nome} - {localizacao_detalhada}"
            elif fazenda:
                localizacao = fazenda.nome
            else:
                localizacao = localizacao_detalhada or ''
            
            # Criar patrimônio vinculado ao veículo
            vida_util = form.cleaned_data['vida_util_anos']
            valor_inicial = form.cleaned_data['valor_inicial']
            
            # Calcular depreciação anual e valor residual
            percentual_anual = Decimal('100') / Decimal(max(vida_util, 1))  # Ex: 100/10 = 10% ao ano
            valor_residual = valor_inicial * Decimal('0.1')  # 10% do valor inicial
            
            patrimonio = Patrimonio.objects.create(
                empresa=request.user.empresa,
                numero_patrimonio=form.cleaned_data['numero_patrimonio'],
                descricao=veiculo.descricao or f"{veiculo.marca} {veiculo.modelo}",
                categoria=categoria,
                veiculo=veiculo,
                valor_inicial=valor_inicial,
                valor_residual=valor_residual,
                percentual_depreciacao_anual=percentual_anual,
                data_aquisicao=form.cleaned_data['data_aquisicao'],
                vida_util_anos=vida_util,
                localizacao=localizacao,
                tipo_depreciacao='LINEAR',
            )
            
            # Atualizar valor atual
            patrimonio.atualizar_valor_atual()
            
            messages.success(request, f'Veículo {veiculo.descricao} registrado como patrimônio {patrimonio.numero_patrimonio}!')
            return redirect('patrimonio:patrimonio_detail', pk=patrimonio.pk)
    else:
        # Pre-preencher com dados do veículo
        initial_data = {
            'numero_patrimonio': '',
            'valor_inicial': veiculo.valor_atual or Decimal('0.00'),
            'data_aquisicao': date.today(),
            'vida_util_anos': 10,
        }
        form = PatrimonioVeiculoExportForm(initial=initial_data, empresa=request.user.empresa)
    
    context = {
        'form': form,
        'veiculo': veiculo,
        'action': 'Registrar como Patrimônio'
    }
    return render(request, 'patrimonio/veiculo_export_form.html', context)


@login_required
def patrimonio_movimentacao_add(request, pk):
    """Adiciona uma movimentação de patrimônio"""
    patrimonio = get_object_or_404(Patrimonio, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = PatrimonioMovimentacaoForm(request.POST)
        if form.is_valid():
            movimentacao = form.save(commit=False)
            movimentacao.patrimonio = patrimonio
            movimentacao.save()
            messages.success(request, 'Movimentação registrada!')
            return redirect('patrimonio:patrimonio_detail', pk=patrimonio.pk)
    else:
        form = PatrimonioMovimentacaoForm()
    
    context = {
        'form': form,
        'patrimonio': patrimonio,
        'action': 'Nova Movimentação'
    }
    return render(request, 'patrimonio/movimentacao_form.html', context)


@login_required
def patrimonio_relatorio(request):
    """Relatório consolidado de patrimônio"""
    empresa = request.user.empresa
    qs, filtros = _filtrar_patrimonios_relatorio(request, empresa)

    # Por categoria
    por_categoria = qs.values('categoria').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')

    # Por estado
    por_estado = qs.values('estado').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')

    # Totais gerais
    totais = qs.aggregate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual'),
        depreciacao_total=Sum('valor_inicial') - Sum('valor_atual')
    )

    # Patrimônios que precisam atenção (ruim/sucata)
    patrimonios_atencao = qs.filter(
        estado__in=['RUIM', 'SUCATA']
    ).order_by('-valor_inicial')[:10]

    # Lista detalhada com paginação
    from django.core.paginator import Paginator
    paginator = Paginator(qs.order_by('-data_aquisicao', '-data_cadastro'), 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    querystring = query_params.urlencode()

    context = {
        'por_categoria': por_categoria,
        'por_estado': por_estado,
        'totais': totais,
        'patrimonios_atencao': patrimonios_atencao,
        'patrimonios': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'categorias': Patrimonio.CATEGORIA_CHOICES,
        'estados': Patrimonio.ESTADO_CHOICES,
        'responsaveis': Funcionario.objects.filter(empresa=empresa).order_by('nome_completo'),
        'filtros': filtros,
        'querystring': querystring,
    }
    
    return render(request, 'patrimonio/relatorio.html', context)


def _filtrar_patrimonios_relatorio(request, empresa):
    """Aplica filtros do relatório e retorna queryset e filtros usados"""
    qs = Patrimonio.objects.filter(empresa=empresa).select_related('responsavel')

    busca = request.GET.get('q', '').strip()
    categorias = request.GET.getlist('categoria')
    estados = request.GET.getlist('estado')
    ativo = request.GET.get('ativo', '1')
    responsavel = request.GET.get('responsavel', '')
    data_de = request.GET.get('data_aquisicao_de', '')
    data_ate = request.GET.get('data_aquisicao_ate', '')
    data_baixa_de = request.GET.get('data_baixa_de', '')
    data_baixa_ate = request.GET.get('data_baixa_ate', '')
    valor_inicial_de_raw = request.GET.get('valor_inicial_de', '').strip()
    valor_inicial_ate_raw = request.GET.get('valor_inicial_ate', '').strip()
    valor_atual_de_raw = request.GET.get('valor_atual_de', '').strip()
    valor_atual_ate_raw = request.GET.get('valor_atual_ate', '').strip()

    if busca:
        qs = qs.filter(
            Q(numero_patrimonio__icontains=busca) |
            Q(descricao__icontains=busca) |
            Q(localizacao__icontains=busca)
        )
    if categorias:
        qs = qs.filter(categoria__in=categorias)
    if estados:
        qs = qs.filter(estado__in=estados)
    if ativo in ['0', '1']:
        qs = qs.filter(ativo=(ativo == '1'))
    if responsavel:
        qs = qs.filter(responsavel_id=responsavel)
    if data_de:
        qs = qs.filter(data_aquisicao__gte=data_de)
    if data_ate:
        qs = qs.filter(data_aquisicao__lte=data_ate)
    if data_baixa_de:
        qs = qs.filter(data_baixa__gte=data_baixa_de)
    if data_baixa_ate:
        qs = qs.filter(data_baixa__lte=data_baixa_ate)

    valor_inicial_de = None
    valor_inicial_ate = None
    if valor_inicial_de_raw:
        try:
            valor_inicial_de = Decimal(valor_inicial_de_raw.replace(',', '.'))
            qs = qs.filter(valor_inicial__gte=valor_inicial_de)
        except Exception:
            valor_inicial_de = None
    if valor_inicial_ate_raw:
        try:
            valor_inicial_ate = Decimal(valor_inicial_ate_raw.replace(',', '.'))
            qs = qs.filter(valor_inicial__lte=valor_inicial_ate)
        except Exception:
            valor_inicial_ate = None

    valor_atual_de = None
    valor_atual_ate = None
    if valor_atual_de_raw:
        try:
            valor_atual_de = Decimal(valor_atual_de_raw.replace(',', '.'))
            qs = qs.filter(valor_atual__gte=valor_atual_de)
        except Exception:
            valor_atual_de = None
    if valor_atual_ate_raw:
        try:
            valor_atual_ate = Decimal(valor_atual_ate_raw.replace(',', '.'))
            qs = qs.filter(valor_atual__lte=valor_atual_ate)
        except Exception:
            valor_atual_ate = None

    categorias_map = dict(Patrimonio.CATEGORIA_CHOICES)
    categorias_labels = [categorias_map.get(c, c) for c in categorias]
    estados_map = dict(Patrimonio.ESTADO_CHOICES)
    estados_labels = [estados_map.get(e, e) for e in estados]

    responsavel_nome = ''
    if responsavel:
        try:
            responsavel_nome = Funcionario.objects.filter(empresa=empresa, id=responsavel).values_list('nome_completo', flat=True).first() or ''
        except Exception:
            responsavel_nome = ''

    filtros = {
        'q': busca,
        'categoria': categorias,
        'categoria_labels': categorias_labels,
        'estado': estados,
        'estado_labels': estados_labels,
        'ativo': ativo,
        'responsavel': responsavel,
        'responsavel_nome': responsavel_nome,
        'data_aquisicao_de': data_de,
        'data_aquisicao_ate': data_ate,
        'data_baixa_de': data_baixa_de,
        'data_baixa_ate': data_baixa_ate,
        'valor_inicial_de': valor_inicial_de_raw,
        'valor_inicial_ate': valor_inicial_ate_raw,
        'valor_atual_de': valor_atual_de_raw,
        'valor_atual_ate': valor_atual_ate_raw,
    }

    return qs, filtros


@login_required
def patrimonio_relatorio_pdf(request):
    """Exporta relatório filtrado em PDF"""
    empresa = request.user.empresa
    qs, filtros = _filtrar_patrimonios_relatorio(request, empresa)

    por_categoria = qs.values('categoria').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')

    por_estado = qs.values('estado').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')

    totais = qs.aggregate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual'),
        depreciacao_total=Sum('valor_inicial') - Sum('valor_atual')
    )

    html = render_to_string('patrimonio/relatorio_pdf.html', {
        'empresa': empresa,
        'totais': totais,
        'por_categoria': por_categoria,
        'por_estado': por_estado,
        'patrimonios': qs.order_by('-data_aquisicao', '-data_cadastro'),
        'filtros': filtros,
        'data_geracao': timezone.now(),
    })

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('UTF-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        filename = f"relatorio_patrimonios_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    messages.error(request, 'Erro ao gerar PDF do relatório.')
    return redirect('patrimonio:patrimonio_relatorio')


@login_required
def patrimonio_relatorio_excel(request):
    """Exporta relatório filtrado em Excel"""
    empresa = request.user.empresa
    qs, filtros = _filtrar_patrimonios_relatorio(request, empresa)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Patrimonios'

    headers = [
        'Numero', 'Descricao', 'Categoria', 'Estado', 'Data Aquisicao', 'Data Baixa',
        'Valor Inicial', 'Valor Atual', 'Localizacao', 'Responsavel', 'Ativo'
    ]
    ws.append(headers)

    for pat in qs.order_by('-data_aquisicao', '-data_cadastro'):
        ws.append([
            pat.numero_patrimonio,
            pat.descricao,
            pat.get_categoria_display() if hasattr(pat, 'get_categoria_display') else pat.categoria,
            pat.get_estado_display() if hasattr(pat, 'get_estado_display') else pat.estado,
            pat.data_aquisicao.strftime('%d/%m/%Y') if pat.data_aquisicao else '',
            pat.data_baixa.strftime('%d/%m/%Y') if pat.data_baixa else '',
            float(pat.valor_inicial) if pat.valor_inicial is not None else 0,
            float(pat.valor_atual) if pat.valor_atual is not None else 0,
            pat.localizacao,
            pat.responsavel.nome_completo if pat.responsavel else '',
            'Sim' if pat.ativo else 'Nao',
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"relatorio_patrimonios_{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def patrimonio_auditoria_list(request):
    """Lista auditorias anuais"""
    empresa = request.user.empresa
    auditorias = PatrimonioAuditoria.objects.filter(empresa=empresa).order_by('-ano')
    context = {
        'auditorias': auditorias,
    }
    return render(request, 'patrimonio/auditoria_list.html', context)


@login_required
def patrimonio_auditoria_create(request):
    """Cria auditoria anual e gera itens"""
    empresa = request.user.empresa

    if request.method == 'POST':
        form = PatrimonioAuditoriaForm(request.POST, empresa=empresa)
        if form.is_valid():
            ano = form.cleaned_data['ano']
            if PatrimonioAuditoria.objects.filter(empresa=empresa, ano=ano).exists():
                messages.warning(request, f'Já existe auditoria para o ano {ano}.')
                return redirect('patrimonio:auditoria_list')

            auditoria = form.save(commit=False)
            auditoria.empresa = empresa
            auditoria.criado_por = request.user
            auditoria.save()

            patrimonios = Patrimonio.objects.filter(empresa=empresa, ativo=True).select_related('responsavel')
            itens = []
            for p in patrimonios:
                responsavel_nome = str(p.responsavel) if p.responsavel else ''
                itens.append(
                    PatrimonioAuditoriaItem(
                        auditoria=auditoria,
                        patrimonio=p,
                        numero_patrimonio=p.numero_patrimonio,
                        descricao=p.descricao,
                        localizacao=p.localizacao or '',
                        responsavel_nome=responsavel_nome,
                        valor_atual=p.valor_atual,
                        estado=p.estado,
                    )
                )
            if itens:
                PatrimonioAuditoriaItem.objects.bulk_create(itens)

            messages.success(request, f'Auditoria {ano} criada com sucesso!')
            return redirect('patrimonio:auditoria_detail', pk=auditoria.pk)
    else:
        form = PatrimonioAuditoriaForm(empresa=empresa)

    context = {
        'form': form,
        'action': 'Nova Auditoria',
    }
    return render(request, 'patrimonio/auditoria_form.html', context)


@login_required
def patrimonio_auditoria_detail(request, pk):
    """Detalhe da auditoria"""
    auditoria = get_object_or_404(PatrimonioAuditoria, pk=pk, empresa=request.user.empresa)

    status_filtro = request.GET.get('status', '')
    itens = auditoria.itens.select_related('patrimonio')
    if status_filtro:
        itens = itens.filter(status=status_filtro)

    total_itens = auditoria.itens.count()
    total_pendente = auditoria.itens.filter(status='PENDENTE').count()
    total_ok = auditoria.itens.filter(status='OK').count()
    total_divergencias = auditoria.itens.filter(status__in=['NAO_LOCALIZADO', 'DANIFICADO', 'BAIXA']).count()

    context = {
        'auditoria': auditoria,
        'itens': itens.order_by('numero_patrimonio'),
        'status_filtro': status_filtro,
        'status_choices': PatrimonioAuditoriaItem.STATUS_CHOICES,
        'total_itens': total_itens,
        'total_pendente': total_pendente,
        'total_ok': total_ok,
        'total_divergencias': total_divergencias,
    }
    return render(request, 'patrimonio/auditoria_detail.html', context)


@login_required
def patrimonio_auditoria_item_update(request, pk, item_pk):
    """Atualiza item da auditoria"""
    auditoria = get_object_or_404(PatrimonioAuditoria, pk=pk, empresa=request.user.empresa)
    item = get_object_or_404(PatrimonioAuditoriaItem, pk=item_pk, auditoria=auditoria)

    if request.method == 'POST':
        form = PatrimonioAuditoriaItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.status != 'PENDENTE' and not obj.data_verificacao:
                obj.data_verificacao = timezone.now()
            obj.save()
            messages.success(request, 'Item de auditoria atualizado!')
            return redirect('patrimonio:auditoria_detail', pk=auditoria.pk)
    else:
        form = PatrimonioAuditoriaItemForm(instance=item)

    context = {
        'auditoria': auditoria,
        'item': item,
        'form': form,
    }
    return render(request, 'patrimonio/auditoria_item_form.html', context)


@login_required
def patrimonio_auditoria_finalizar(request, pk):
    """Finaliza auditoria"""
    auditoria = get_object_or_404(PatrimonioAuditoria, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        auditoria.status = 'FECHADA'
        auditoria.data_fechamento = date.today()
        auditoria.save(update_fields=['status', 'data_fechamento'])
        messages.success(request, 'Auditoria finalizada!')
        return redirect('patrimonio:auditoria_detail', pk=auditoria.pk)

    context = {'auditoria': auditoria}
    return render(request, 'patrimonio/auditoria_confirmar_finalizar.html', context)


@login_required
def patrimonio_auditoria_pdf(request, pk):
    """Gera PDF da auditoria (resumo + divergencias)"""
    auditoria = get_object_or_404(PatrimonioAuditoria, pk=pk, empresa=request.user.empresa)

    divergencias = auditoria.itens.filter(status__in=['NAO_LOCALIZADO', 'DANIFICADO', 'BAIXA'])
    total_itens = auditoria.itens.count()
    total_pendente = auditoria.itens.filter(status='PENDENTE').count()
    total_ok = auditoria.itens.filter(status='OK').count()
    total_divergencias = divergencias.count()

    context = {
        'auditoria': auditoria,
        'divergencias': divergencias.order_by('numero_patrimonio'),
        'total_itens': total_itens,
        'total_pendente': total_pendente,
        'total_ok': total_ok,
        'total_divergencias': total_divergencias,
        'gerado_em': timezone.now(),
    }

    html = render_to_string('patrimonio/auditoria_pdf.html', context)
    response = HttpResponse(content_type='application/pdf')
    filename = slugify(f"Auditoria Patrimonial {auditoria.ano}")
    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'

    result = pisa.CreatePDF(html, dest=response)
    if result.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    return response
