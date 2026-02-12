"""
Views do módulo Patrimônio
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse
from datetime import date
from decimal import Decimal

from .models import Patrimonio, PatrimonioMovimentacao
from .forms import PatrimonioForm, PatrimonioVeiculoExportForm, PatrimonioMovimentacaoForm
from cadastros.models import Vehicle


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
    
    # Por categoria
    por_categoria = Patrimonio.objects.filter(
        empresa=empresa, ativo=True
    ).values('categoria').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')
    
    # Por estado
    por_estado = Patrimonio.objects.filter(
        empresa=empresa, ativo=True
    ).values('estado').annotate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual')
    ).order_by('-valor_inicial_total')
    
    # Totais gerais
    totais = Patrimonio.objects.filter(
        empresa=empresa, ativo=True
    ).aggregate(
        total_bens=Count('id'),
        valor_inicial_total=Sum('valor_inicial'),
        valor_atual_total=Sum('valor_atual'),
        depreciacao_total=Sum('valor_inicial') - Sum('valor_atual')
    )
    
    # Patrimônios que precisam atenção (ruim/sucata)
    patrimonios_atencao = Patrimonio.objects.filter(
        empresa=empresa, 
        estado__in=['RUIM', 'SUCATA']
    ).order_by('-valor_inicial')[:10]
    
    context = {
        'por_categoria': por_categoria,
        'por_estado': por_estado,
        'totais': totais,
        'patrimonios_atencao': patrimonios_atencao,
    }
    
    return render(request, 'patrimonio/relatorio.html', context)
