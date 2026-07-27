"""
Views do módulo Estoque
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.db.models import Sum, Q, F, Value, DecimalField
from django.db.models.functions import Coalesce
from datetime import timedelta, datetime
from decimal import Decimal
from .models import (
    Armazem, LocalEstocagem, Lote, MovimentacaoEstoque,
    InventarioCiclico, InventarioCiclicoSchedule, InventarioCiclicoItem
)
from .forms import (
    ArmazemForm, LocalEstocagemForm, LoteForm, MovimentacaoEstoqueForm,
    EntradaEstoqueForm, SaidaEstoqueForm, TransferenciaEstoqueForm
)
from produtos.models import Produto
from django.template.loader import get_template
import io
from xhtml2pdf import pisa


@login_required
def dashboard(request):
    """Dashboard do estoque"""
    empresa = request.user.empresa
    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)
    data_vence_30 = hoje + timedelta(days=30)
    data_vence_7 = hoje + timedelta(days=7)

    lotes_qs = Lote.objects.filter(empresa=empresa)

    # KPIs principais
    total_armazens = Armazem.objects.filter(empresa=empresa, ativo=True).count()
    total_locais = LocalEstocagem.objects.filter(armazem__empresa=empresa, ativo=True).count()
    total_lotes = lotes_qs.exclude(status='ESGOTADO').count()
    valor_total_estoque = lotes_qs.filter(
        status='DISPONIVEL'
    ).aggregate(total=Sum('valor_total'))['total'] or Decimal('0.00')

    # Status dos lotes
    lotes_disponiveis = lotes_qs.filter(status='DISPONIVEL').count()
    lotes_bloqueados = lotes_qs.filter(status='BLOQUEADO').count()
    lotes_vencidos_count = lotes_qs.filter(status='VENCIDO').count()
    lotes_quarentena = lotes_qs.filter(status='QUARENTENA').count()

    # Vencimentos
    lotes_vencendo_7d = lotes_qs.filter(
        data_validade__gte=hoje,
        data_validade__lte=data_vence_7,
        status='DISPONIVEL',
    ).count()
    lotes_proximos_vencimento = lotes_qs.filter(
        data_validade__gte=hoje,
        data_validade__lte=data_vence_30,
        status='DISPONIVEL',
    ).select_related('produto', 'armazem', 'unidade_medida').order_by('data_validade')[:10]
    lotes_vencidos = lotes_qs.filter(
        status='VENCIDO'
    ).select_related('produto', 'armazem')[:5]

    # Movimentações
    mov_qs = MovimentacaoEstoque.objects.filter(empresa=empresa)
    movimentacoes_mes = mov_qs.filter(data_movimentacao__date__gte=inicio_mes).count()
    entradas_mes = mov_qs.filter(data_movimentacao__date__gte=inicio_mes, tipo='ENTRADA').count()
    saidas_mes = mov_qs.filter(data_movimentacao__date__gte=inicio_mes, tipo='SAIDA').count()
    ultimas_movimentacoes = mov_qs.select_related(
        'produto', 'armazem_destino', 'armazem_origem', 'cadastrado_por'
    ).order_by('-data_movimentacao')[:8]

    context = {
        'total_armazens': total_armazens,
        'total_locais': total_locais,
        'total_lotes': total_lotes,
        'valor_total_estoque': valor_total_estoque,
        'lotes_disponiveis': lotes_disponiveis,
        'lotes_bloqueados': lotes_bloqueados,
        'lotes_vencidos_count': lotes_vencidos_count,
        'lotes_quarentena': lotes_quarentena,
        'lotes_vencendo': lotes_proximos_vencimento.count(),
        'lotes_vencendo_7d': lotes_vencendo_7d,
        'lotes_proximos_vencimento': lotes_proximos_vencimento,
        'lotes_vencidos': lotes_vencidos,
        'movimentacoes_mes': movimentacoes_mes,
        'entradas_mes': entradas_mes,
        'saidas_mes': saidas_mes,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'hoje': hoje,
    }
    return render(request, 'estoque/dashboard.html', context)


@login_required
def get_produto_unidade(request, produto_id):
    """Retorna a unidade de medida de um produto em JSON"""
    try:
        produto = Produto.objects.get(
            pk=produto_id,
            ativo=True,
            categoria__empresa=request.user.empresa
        )
        return JsonResponse({
            'success': True,
            'unidade_medida_id': produto.unidade_medida.id,
            'unidade_medida_nome': str(produto.unidade_medida)
        })
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Produto não encontrado'}, status=404)


@login_required
def armazem_list(request):
    """Lista de armazéns"""
    armazens_qs = Armazem.objects.filter(empresa=request.user.empresa).order_by('nome')
    paginator = Paginator(armazens_qs, 20)
    armazens = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/armazem_list.html', {'armazens': armazens})


@login_required
def armazem_create(request):
    """Criar armazém"""
    if request.method == 'POST':
        form = ArmazemForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Armazém cadastrado com sucesso!')
            return redirect('estoque:armazem_list')
    else:
        form = ArmazemForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/armazem_form.html', {'form': form})


@login_required
def armazem_detail(request, pk):
    """Detalhes do armazém"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)
    locais = LocalEstocagem.objects.filter(armazem=armazem).order_by('codigo')
    total_lotes = Lote.objects.filter(armazem=armazem).exclude(status='ESGOTADO').count()
    
    context = {
        'armazem': armazem,
        'locais': locais,
        'total_lotes': total_lotes,
    }
    return render(request, 'estoque/armazem_detail.html', context)


@login_required
def armazem_edit(request, pk):
    """Editar armazém"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ArmazemForm(request.POST, instance=armazem, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Armazém atualizado com sucesso!')
            return redirect('estoque:armazem_detail', pk=pk)
    else:
        form = ArmazemForm(instance=armazem, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/armazem_form.html', {'form': form})


@login_required
def armazem_delete(request, pk):
    """Desativar armazém (soft delete)"""
    armazem = get_object_or_404(Armazem, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        if LocalEstocagem.objects.filter(armazem=armazem, ativo=True).exists():
            messages.error(
                request,
                'Não é possível desativar este armazém: existem locais de estocagem ativos vinculados a ele.'
            )
        else:
            armazem.ativo = False
            armazem.save(update_fields=['ativo'])
            messages.success(request, 'Armazém desativado com sucesso!')
        return redirect('estoque:armazem_list')

    # Se GET, redireciona para a lista
    return redirect('estoque:armazem_list')


@login_required
def local_list(request):
    """Lista de locais"""
    locais_qs = LocalEstocagem.objects.filter(armazem__empresa=request.user.empresa).select_related('armazem').order_by('armazem__nome', 'codigo')
    paginator = Paginator(locais_qs, 20)
    locais = paginator.get_page(request.GET.get('page'))
    return render(request, 'estoque/local_list.html', {'locais': locais})


@login_required
def local_create(request):
    """Criar local"""
    if request.method == 'POST':
        form = LocalEstocagemForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Local de estocagem cadastrado com sucesso!')
            return redirect('estoque:local_list')
    else:
        form = LocalEstocagemForm(empresa=request.user.empresa, usuario=request.user)
        
        # Se vier armazem na querystring, pré-seleciona
        armazem_id = request.GET.get('armazem')
        if armazem_id:
            form.fields['armazem'].initial = armazem_id
    
    return render(request, 'estoque/local_form.html', {'form': form})


@login_required
def local_edit(request, pk):
    """Editar local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = LocalEstocagemForm(request.POST, instance=local, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Local de estocagem atualizado com sucesso!')
            return redirect('estoque:local_list')
    else:
        form = LocalEstocagemForm(instance=local, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/local_form.html', {'form': form})


@login_required
def local_delete(request, pk):
    """Desativar local de estocagem (soft delete)"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)

    if request.method == 'POST':
        if Lote.objects.filter(local_estocagem=local, quantidade_atual__gt=0).exists():
            messages.error(
                request,
                'Não é possível desativar este local: existem lotes com saldo de estoque vinculados a ele.'
            )
        else:
            local.ativo = False
            local.save(update_fields=['ativo'])
            messages.success(request, 'Local de estocagem desativado com sucesso!')
        return redirect('estoque:local_list')

    return redirect('estoque:local_list')


@login_required
def local_bloquear(request, pk):
    """Bloquear local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Bloqueio manual')
        local.bloquear(motivo, request.user)
        messages.warning(request, f'Local {local.codigo} bloqueado com sucesso!')
        return redirect('estoque:local_list')
    
    return redirect('estoque:local_list')


@login_required
def local_desbloquear(request, pk):
    """Desbloquear local"""
    local = get_object_or_404(LocalEstocagem, pk=pk, armazem__empresa=request.user.empresa)

    if request.method == 'POST':
        local.desbloquear()
        messages.success(request, f'Local {local.codigo} desbloqueado com sucesso!')
        return redirect('estoque:local_list')
    
    return redirect('estoque:local_list')


@login_required
def lote_list(request):
    """Lista de lotes"""
    lotes_qs = Lote.objects.filter(empresa=request.user.empresa).select_related(
        'produto', 'armazem', 'local_estocagem', 'unidade_medida'
    ).order_by('-data_entrada')

    produto_id = request.GET.get('produto', '')
    status_filtro = request.GET.get('status', '')
    armazem_id = request.GET.get('armazem', '')
    if produto_id:
        lotes_qs = lotes_qs.filter(produto_id=produto_id)
    if status_filtro:
        lotes_qs = lotes_qs.filter(status=status_filtro)
    if armazem_id:
        lotes_qs = lotes_qs.filter(armazem_id=armazem_id)

    paginator = Paginator(lotes_qs, 30)
    lotes = paginator.get_page(request.GET.get('page'))

    armazens = Armazem.objects.filter(empresa=request.user.empresa).order_by('nome')
    produto_filtrado = None
    if produto_id:
        produto_filtrado = Produto.objects.filter(pk=produto_id).first()

    return render(request, 'estoque/lote_list.html', {
        'lotes': lotes,
        'armazens': armazens,
        'status_choices': Lote.STATUS_CHOICES,
        'produto_id': produto_id,
        'produto_filtrado': produto_filtrado,
        'status_filtro': status_filtro,
        'armazem_id': armazem_id,
    })


@login_required
def lote_create(request):
    """Criar lote"""
    if request.method == 'POST':
        form = LoteForm(request.POST, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote cadastrado com sucesso!')
            return redirect('estoque:lote_list')
    else:
        form = LoteForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/lote_form.html', {'form': form})


@login_required
def lote_detail(request, pk):
    """Detalhes do lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    return render(request, 'estoque/lote_detail.html', {'lote': lote})


@login_required
def lote_edit(request, pk):
    """Editar lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = LoteForm(request.POST, instance=lote, empresa=request.user.empresa, usuario=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lote atualizado com sucesso!')
            return redirect('estoque:lote_detail', pk=pk)
    else:
        form = LoteForm(instance=lote, empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/lote_form.html', {'form': form})


@login_required
def lote_bloquear(request, pk):
    """Bloquear lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', 'Bloqueio manual')
        lote.bloquear(motivo)
        messages.warning(request, f'Lote {lote.numero_lote} bloqueado com sucesso!')
        return redirect('estoque:lote_detail', pk=pk)
    
    return redirect('estoque:lote_detail', pk=pk)


@login_required
def lote_desbloquear(request, pk):
    """Desbloquear lote"""
    lote = get_object_or_404(Lote, pk=pk, empresa=request.user.empresa)

    if request.method == 'POST':
        lote.desbloquear()
        messages.success(request, f'Lote {lote.numero_lote} desbloqueado com sucesso!')
        return redirect('estoque:lote_detail', pk=pk)
    
    return redirect('estoque:lote_detail', pk=pk)


# ============================================
# MOVIMENTAÇÕES DE ESTOQUE (FASE 2)
# ============================================

@login_required
def movimentacao_list(request):
    """Lista todas as movimentações"""
    movimentacoes = MovimentacaoEstoque.objects.filter(
        empresa=request.user.empresa
    ).select_related(
        'lote__produto', 'lote__unidade_medida', 'produto', 'unidade_medida',
        'armazem_origem', 'armazem_destino', 'cadastrado_por', 'aprovador', 'executado_por'
    ).order_by('-data_movimentacao')
    
    # Filtros
    tipo = request.GET.get('tipo')
    status = request.GET.get('status')
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if status:
        movimentacoes = movimentacoes.filter(status=status)

    paginator = Paginator(movimentacoes, 30)
    page_number = request.GET.get('page')
    movimentacoes_page = paginator.get_page(page_number)

    context = {
        'movimentacoes': movimentacoes_page,
        'page_obj': movimentacoes_page,
        'is_paginated': movimentacoes_page.has_other_pages(),
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'status_choices': MovimentacaoEstoque.STATUS_CHOICES,
        'tipo_filtro': tipo,
        'status_filtro': status,
    }
    return render(request, 'estoque/movimentacao_list.html', context)


@login_required
def movimentacao_create(request):
    """Criar movimentação genérica"""
    if request.method == 'POST':
        form = MovimentacaoEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Movimentação {movimentacao.numero} criada com sucesso!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = MovimentacaoEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Nova Movimentação'
    })


@login_required
def movimentacao_detail(request, pk):
    """Detalhes da movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    return render(request, 'estoque/movimentacao_detail.html', {'movimentacao': movimentacao})


@login_required
def movimentacao_aprovar(request, pk):
    """Aprovar movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.aprovar(request.user)
            messages.success(request, f'Movimentação {movimentacao.numero} aprovada!')
        except Exception as e:
            messages.error(request, f'Erro ao aprovar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def movimentacao_executar(request, pk):
    """Executar movimentação e atualizar estoque"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.executar(request.user)
            messages.success(request, f'Movimentação {movimentacao.numero} executada! Estoque atualizado.')
        except Exception as e:
            messages.error(request, f'Erro ao executar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def movimentacao_cancelar(request, pk):
    """Cancelar movimentação"""
    movimentacao = get_object_or_404(
        MovimentacaoEstoque,
        pk=pk,
        empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        try:
            movimentacao.cancelar()
            messages.warning(request, f'Movimentação {movimentacao.numero} cancelada.')
        except Exception as e:
            messages.error(request, f'Erro ao cancelar: {str(e)}')
        return redirect('estoque:movimentacao_detail', pk=pk)
    
    return redirect('estoque:movimentacao_detail', pk=pk)


@login_required
def entrada_create(request):
    """Entrada de estoque - executa automaticamente se for movimentação direta (sem lote)"""
    tipo_mov = request.GET.get('tipo') or request.POST.get('tipo') or 'ENTRADA'
    if request.method == 'POST':
        post_data = request.POST.copy()
        post_data['tipo'] = tipo_mov
        form = EntradaEstoqueForm(
            post_data,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            
            # Se for movimentação direta (sem lote), executa automaticamente
            if not movimentacao.lote and movimentacao.tipo == 'ENTRADA':
                try:
                    movimentacao.executar(request.user)
                    messages.success(request, f'Entrada {movimentacao.numero} registrada e processada! Estoque atualizado.')
                except Exception as e:
                    messages.warning(request, f'Entrada {movimentacao.numero} criada, mas erro ao processar: {str(e)}')
            else:
                messages.success(request, f'Entrada {movimentacao.numero} registrada!')
            
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = EntradaEstoqueForm(
            initial={'tipo': tipo_mov},
            empresa=request.user.empresa,
            usuario=request.user
        )
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Entrada de Estoque',
        'tipo': tipo_mov
    })


@login_required
def saida_create(request):
    """Saída de estoque - executa automaticamente se for movimentação direta (sem lote)"""
    if request.method == 'POST':
        form = SaidaEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            
            # Se for movimentação direta (sem lote), executa automaticamente
            if not movimentacao.lote and movimentacao.tipo == 'SAIDA':
                try:
                    movimentacao.executar(request.user)
                    messages.success(request, f'Saída {movimentacao.numero} registrada e processada! Estoque atualizado.')
                except Exception as e:
                    messages.warning(request, f'Saída {movimentacao.numero} criada, mas erro ao processar: {str(e)}')
            else:
                messages.success(request, f'Saída {movimentacao.numero} registrada!')
            
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = SaidaEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Saída de Estoque',
        'tipo': 'SAIDA'
    })


@login_required
def transferencia_create(request):
    """Transferência entre armazéns"""
    if request.method == 'POST':
        form = TransferenciaEstoqueForm(
            request.POST,
            empresa=request.user.empresa,
            usuario=request.user
        )
        if form.is_valid():
            movimentacao = form.save()
            messages.success(request, f'Transferência {movimentacao.numero} registrada!')
            return redirect('estoque:movimentacao_detail', pk=movimentacao.pk)
    else:
        form = TransferenciaEstoqueForm(empresa=request.user.empresa, usuario=request.user)
    
    return render(request, 'estoque/movimentacao_form.html', {
        'form': form,
        'titulo': 'Transferência entre Armazéns',
        'tipo': 'TRANSFERENCIA'
    })


@login_required
def get_lotes_disponiveis(request):
    """API para buscar lotes disponíveis de um produto (para JavaScript)"""
    produto_id = request.GET.get('produto_id')
    armazem_id = request.GET.get('armazem_id')
    
    lotes = Lote.objects.filter(
        empresa=request.user.empresa,
        produto_id=produto_id,
        status='DISPONIVEL',
        quantidade_atual__gt=0
    )
    
    if armazem_id:
        lotes = lotes.filter(armazem_id=armazem_id)
    
    lotes_data = [{
        'id': lote.id,
        'numero_lote': lote.numero_lote,
        'quantidade_disponivel': float(lote.quantidade_atual),
        'unidade': lote.unidade_medida.sigla,
        'data_validade': lote.data_validade.strftime('%d/%m/%Y') if lote.data_validade else None,
        'armazem': lote.armazem.nome,
    } for lote in lotes]
    
    return JsonResponse({'lotes': lotes_data})


@login_required
def estoque_produtos_list(request):
    """Listagem de produtos do estoque"""
    from django.db.models import Q, Sum
    from decimal import Decimal
    from cadastros.models import Fazenda
    from produtos.models import Categoria
    from usuarios.views import is_admin
    from estoque.disponibilidade import reservas_por_produto

    empresa = request.user.empresa
    busca = request.GET.get('busca', '')
    categoria_selecionada = request.GET.get('categoria', '')
    filtro_estoque = request.GET.get('estoque', '')

    # Admins automaticamente têm permissão de ver estoque de outras fazendas
    can_choose_fazenda = is_admin(request.user) or request.user.has_perm('cadastros.view_other_fazendas_estoque')
    fazenda_id = request.GET.get('fazenda') if can_choose_fazenda else None
    fazenda_filtro = None
    if can_choose_fazenda and fazenda_id:
        fazenda_filtro = Fazenda.objects.filter(id=fazenda_id, empresa=empresa).first()

    produtos_qs = Produto.objects.filter(
        ativo=True, categoria__empresa=empresa
    ).select_related('categoria', 'unidade_medida').order_by('nome')
    if busca:
        produtos_qs = produtos_qs.filter(nome__icontains=busca)
    if categoria_selecionada:
        produtos_qs = produtos_qs.filter(categoria_id=categoria_selecionada)

    produtos = list(produtos_qs)
    produto_ids = [p.id for p in produtos]

    # Calcula estoque a partir de DUAS fontes, em consultas agregadas por produto
    # (uma consulta por fonte para todos os produtos, em vez de 3 por produto):
    # 1. Lotes com status DISPONIVEL ou BLOQUEADO (quantidade_atual)
    # 2. Movimentacoes diretas EXECUTADAS (ENTRADA - SAIDA) para produtos sem lote
    lotes_filtro = Q(empresa=empresa, produto_id__in=produto_ids, status__in=['DISPONIVEL', 'BLOQUEADO'])
    if fazenda_filtro:
        lotes_filtro &= Q(armazem__fazenda=fazenda_filtro)
    total_lotes_por_produto = {
        row['produto']: row['total'] or Decimal('0')
        for row in Lote.objects.filter(lotes_filtro).values('produto').annotate(total=Sum('quantidade_atual'))
    }

    entradas_filtro = Q(empresa=empresa, produto_id__in=produto_ids, lote__isnull=True, tipo='ENTRADA', status='EXECUTADO')
    if fazenda_filtro:
        entradas_filtro &= Q(armazem_destino__fazenda=fazenda_filtro)
    entradas_por_produto = {
        row['produto']: row['total'] or Decimal('0')
        for row in MovimentacaoEstoque.objects.filter(entradas_filtro).values('produto').annotate(total=Sum('quantidade'))
    }

    saidas_filtro = Q(empresa=empresa, produto_id__in=produto_ids, lote__isnull=True, tipo='SAIDA', status='EXECUTADO')
    if fazenda_filtro:
        saidas_filtro &= Q(armazem_origem__fazenda=fazenda_filtro)
    saidas_por_produto = {
        row['produto']: row['total'] or Decimal('0')
        for row in MovimentacaoEstoque.objects.filter(saidas_filtro).values('produto').annotate(total=Sum('quantidade'))
    }

    reservas = reservas_por_produto(empresa)

    alertas_criticos = 0
    alertas_excesso = 0
    produtos_desatualizados = []

    for produto in produtos:
        total_lotes = total_lotes_por_produto.get(produto.id, Decimal('0'))
        movs_diretas_entrada = entradas_por_produto.get(produto.id, Decimal('0'))
        movs_diretas_saida = saidas_por_produto.get(produto.id, Decimal('0'))

        # Saldo = Lotes + (Entradas diretas - Saidas diretas)
        saldo = Decimal(total_lotes) + (Decimal(movs_diretas_entrada) - Decimal(movs_diretas_saida))

        # Marca para atualização em lote se divergir (sem gravar aqui, um produto por vez)
        if float(produto.estoque_atual) != float(saldo):
            produto.estoque_atual = saldo
            produtos_desatualizados.append(produto)

        # Define atributo para template (compatibilidade)
        produto.estoque_total = float(saldo)

        # Reserva: insumos comprometidos em OS/Requisicoes ja aprovadas mas ainda nao baixados
        reservado = reservas.get(produto.id, Decimal('0'))
        produto.estoque_reservado = float(reservado)
        produto.estoque_disponivel = float(saldo - reservado)

        # Calcula status de alertas
        produto.alerta_tipo = None
        if saldo <= 0:
            produto.alerta_tipo = 'critico'
            alertas_criticos += 1
        elif produto.estoque_maximo > 0 and saldo > produto.estoque_maximo:
            produto.alerta_tipo = 'excesso'
            alertas_excesso += 1

    if produtos_desatualizados:
        Produto.objects.bulk_update(produtos_desatualizados, ['estoque_atual'])

    if filtro_estoque == 'disponivel':
        produtos = [p for p in produtos if p.estoque_disponivel > 0]
    elif filtro_estoque == 'baixo':
        produtos = [
            p for p in produtos
            if p.estoque_total > 0 and p.estoque_minimo and p.estoque_total <= float(p.estoque_minimo)
        ]
    elif filtro_estoque == 'zerado':
        produtos = [p for p in produtos if p.estoque_total <= 0]

    paginator = Paginator(produtos, 30)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'produtos': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'busca': busca,
        'categorias': Categoria.objects.filter(empresa=empresa).order_by('nome'),
        'categoria_selecionada': categoria_selecionada,
        'filtro_estoque': filtro_estoque,
        'alertas_criticos': alertas_criticos,
        'alertas_excesso': alertas_excesso,
        'total_alertas': alertas_criticos + alertas_excesso,
        'can_choose_fazenda': can_choose_fazenda,
        'fazendas': Fazenda.objects.filter(empresa=empresa) if can_choose_fazenda else [],
        'fazenda_filtro': fazenda_filtro,
    }
    return render(request, 'estoque/estoque_produtos_list.html', context)


@login_required
def produto_historico(request, pk):
    """Histórico do produto"""
    produto = get_object_or_404(Produto, pk=pk, categoria__empresa=request.user.empresa)
    empresa = request.user.empresa

    # Filtros
    tipo_filtro = request.GET.get('tipo')
    origem_filtro = request.GET.get('origem')
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')

    movimentacoes = MovimentacaoEstoque.objects.filter(
        Q(lote__produto=produto) | Q(produto=produto),
        empresa=empresa,
    ).select_related('lote', 'armazem_origem', 'armazem_destino', 'executado_por').order_by('-data_cadastro')

    if tipo_filtro:
        movimentacoes = movimentacoes.filter(tipo=tipo_filtro)
    if origem_filtro:
        movimentacoes = movimentacoes.filter(origem=origem_filtro)
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_cadastro__date__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data_cadastro__date__lte=data_fim)

    # Estatísticas
    stats = {
        'total_entradas': movimentacoes.filter(tipo='ENTRADA').aggregate(total=models.Sum('quantidade'))['total'] or 0,
        'total_saidas': movimentacoes.filter(tipo='SAIDA').aggregate(total=models.Sum('quantidade'))['total'] or 0,
        'total_transferencias': movimentacoes.filter(tipo='TRANSFERENCIA').count(),
        'total_compras': movimentacoes.filter(origem='COMPRA').count(),
        'total_solicitacoes': movimentacoes.filter(origem='REQUISICAO').count(),
    }

    # Compras relacionadas (se houver app de compras)
    try:
        from compras.models import ItemPedidoCompra
        compras = ItemPedidoCompra.objects.filter(
            produto=produto,
            pedido__empresa=empresa
        ).select_related('pedido').order_by('-pedido__data_pedido')
    except Exception as e:
        import logging
        logging.exception(f"Erro ao buscar compras para produto {produto.id}: {str(e)}")
        compras = []

    # Solicitações relacionadas (se houver app de compras)
    try:
        from compras.models import ItemSolicitacaoCompra
        solicitacoes = ItemSolicitacaoCompra.objects.filter(produto=produto, solicitacao__empresa=empresa).select_related('solicitacao')
    except Exception:
        solicitacoes = []

    # Empréstimos relacionados removidos (app emprestimos excluído)
    emprestimos = []

    context = {
        'produto': produto,
        'movimentacoes': movimentacoes,
        'stats': stats,
        'compras': compras,
        'solicitacoes': solicitacoes,
        'emprestimos': emprestimos,  # Mantido vazio para compatibilidade de template
        'tipo_filtro': tipo_filtro,
        'origem_filtro': origem_filtro,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    return render(request, 'estoque/produto_historico.html', context)


@login_required
def produto_historico_pdf(request, pk):
    """Gera PDF do histórico do produto"""
    produto = get_object_or_404(Produto, pk=pk, categoria__empresa=request.user.empresa)
    # Aqui você pode adicionar lógica para buscar o histórico real do produto, se necessário
    context = {
        'produto': produto,
        # Adicione outros dados do histórico conforme necessário
    }
    template = get_template('estoque/produto_historico_pdf.html')
    html = template.render(context)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('Erro ao gerar PDF', status=500)


@login_required
def relatorio_estoque(request):
    """Exibir formulário de filtros para relatório de estoque"""
    from .forms_relatorio import FiltroRelatorioEstoqueForm
    
    if request.method == 'POST':
        form = FiltroRelatorioEstoqueForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio(request, form)
    else:
        form = FiltroRelatorioEstoqueForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Estoque',
    }
    return render(request, 'estoque/relatorio_estoque.html', context)


def processar_relatorio(request, form):
    """Processar e gerar o relatório"""
    from .relatorio_utils import RelatorioEstoquePDF, RelatorioEstoqueExcel
    from .enviador import EnviadorRelatorio
    from datetime import datetime
    
    empresa = request.user.empresa
    
    # Iniciar query de lotes
    lotes = Lote.objects.filter(empresa=empresa).select_related(
        'produto', 'armazem', 'unidade_medida'
    )
    
    # Aplicar filtros
    armazens = form.cleaned_data.get('armazem')
    if armazens:
        lotes = lotes.filter(armazem__in=armazens)
    
    categorias = form.cleaned_data.get('categoria')
    if categorias:
        lotes = lotes.filter(produto__categoria__in=categorias)
    
    status_lote = form.cleaned_data.get('status_lote')
    if status_lote:
        lotes = lotes.filter(status__in=status_lote)
    
    if form.cleaned_data.get('apenas_baixo_estoque'):
        lotes = lotes.filter(
            produto__estoque_atual__lt=models.F('produto__estoque_minimo')
        )
    
    if form.cleaned_data.get('apenas_vencidos'):
        lotes = lotes.filter(status='VENCIDO')
    
    # Construir descrição dos filtros
    filtros_desc = []
    if armazens:
        filtros_desc.append(f"Armazéns: {', '.join([a.nome for a in armazens])}")
    if categorias:
        filtros_desc.append(f"Categorias: {', '.join([c.nome for c in categorias])}")
    if status_lote:
        filtros_desc.append(f"Status: {', '.join([dict(Lote.STATUS_CHOICES).get(s) for s in status_lote])}")
    if form.cleaned_data.get('apenas_baixo_estoque'):
        filtros_desc.append("Apenas baixo estoque")
    if form.cleaned_data.get('apenas_vencidos'):
        filtros_desc.append("Apenas lotes vencidos")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Nenhum filtro aplicado'
    
    # Gerar relatório
    enviar_para = form.cleaned_data.get('enviar_para')
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"relatorio_estoque_{datetime.now().strftime('%d%m%Y_%H%M%S')}"

    if enviar_para == 'tela':
        # Visualizar na tela (HTML)
        context = {
            'form': form,
            'title': 'Relatório de Estoque',
            'lotes': lotes,
            'filtros_str': filtros_str,
        }
        return render(request, 'estoque/relatorio_estoque_tela.html', context)

    if formato == 'pdf':
        relatorio = RelatorioEstoquePDF(empresa, titulo='Relatório de Estoque')
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_lotes(lotes)
        relatorio.adicionar_resumo_produtos(lotes)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioEstoqueExcel(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        linha = relatorio.adicionar_tabela_lotes(lotes)
        relatorio.adicionar_resumo_produtos(lotes, linha_inicio=linha + 2)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.xlsx'
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    # Verificar se será enviado ou apenas baixado
    if enviar_para == 'nenhum':
        # Apenas baixar
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response

    # Enviar por email e/ou WhatsApp
    resultados = []

    if enviar_para in ['email', 'ambos']:
        email = form.cleaned_data.get('email_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'email', email, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('Email', sucesso, msg))

    if enviar_para in ['whatsapp', 'ambos']:
        whatsapp = form.cleaned_data.get('whatsapp_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'whatsapp', whatsapp, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('WhatsApp', sucesso, msg))

    # Exibir resultados
    for tipo, sucesso, mensagem in resultados:
        if sucesso:
            messages.success(request, f'{tipo}: {mensagem}')
        else:
            messages.error(request, f'{tipo}: {mensagem}')

    return redirect('estoque:relatorio_estoque')


@login_required
def relatorio_produto(request):
    """Exibir formulário de filtros para relatório de estoque por produto"""
    from .forms_relatorio_produto import FiltroRelatorioProdutoForm
    
    if request.method == 'POST':
        form = FiltroRelatorioProdutoForm(request.POST, empresa=request.user.empresa)
        
        if form.is_valid():
            return processar_relatorio_produto(request, form)
    else:
        form = FiltroRelatorioProdutoForm(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'title': 'Relatório de Estoque por Produto',
    }
    return render(request, 'estoque/relatorio_produto.html', context)


def processar_relatorio_produto(request, form):
    """Processar e gerar o relatório por produto"""
    from .relatorio_produto_utils import RelatorioProdutoPDF, RelatorioProdutoExcel, gerar_dados_relatorio_produto
    from .enviador import EnviadorRelatorio
    from datetime import datetime
    
    empresa = request.user.empresa
    
    # Iniciar query de lotes
    lotes = Lote.objects.filter(empresa=empresa).select_related(
        'produto', 'armazem', 'unidade_medida', 'produto__categoria'
    )
    
    # Aplicar filtros
    armazens = form.cleaned_data.get('armazem')
    if armazens:
        lotes = lotes.filter(armazem__in=armazens)
    
    categorias = form.cleaned_data.get('categoria')
    if categorias:
        lotes = lotes.filter(produto__categoria__in=categorias)
    
    if form.cleaned_data.get('apenas_baixo_estoque'):
        lotes = lotes.filter(
            produto__estoque_atual__lt=models.F('produto__estoque_minimo')
        )
    
    incluir_zerados = form.cleaned_data.get('incluir_zerados', False)
    
    # Construir descrição dos filtros
    filtros_desc = []
    if armazens:
        filtros_desc.append(f"Armazéns: {', '.join([a.nome for a in armazens])}")
    if categorias:
        filtros_desc.append(f"Categorias: {', '.join([c.nome for c in categorias])}")
    if form.cleaned_data.get('apenas_baixo_estoque'):
        filtros_desc.append("Apenas baixo estoque")
    if incluir_zerados:
        filtros_desc.append("Incluindo produtos zerados")
    
    filtros_str = ' | '.join(filtros_desc) if filtros_desc else 'Nenhum filtro aplicado'
    
    # Gerar dados agregados por produto
    ordenacao = form.cleaned_data.get('ordenacao', 'produto')
    produtos_data = gerar_dados_relatorio_produto(lotes, empresa, incluir_zerados, ordenacao)
    
    # Gerar relatório
    formato = form.cleaned_data.get('formato')
    nome_arquivo = f"relatorio_produto_{datetime.now().strftime('%d%m%Y_%H%M%S')}"
    
    if formato == 'pdf':
        relatorio = RelatorioProdutoPDF(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_produtos(produtos_data)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.pdf'
        tipo_mime = 'application/pdf'
    else:  # excel
        relatorio = RelatorioProdutoExcel(empresa)
        relatorio.adicionar_cabecalho(filtros_str)
        relatorio.adicionar_tabela_produtos(produtos_data)
        arquivo_bytes = relatorio.gerar()
        nome_arquivo += '.xlsx'
        tipo_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    # Verificar se será enviado ou apenas baixado
    enviar_para = form.cleaned_data.get('enviar_para')
    
    if enviar_para == 'visualizar':
        # Visualizar na tela
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'inline; filename="{nome_arquivo}"'
        return response
    
    if enviar_para == 'nenhum':
        # Apenas baixar
        response = HttpResponse(arquivo_bytes, content_type=tipo_mime)
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response
    
    # Enviar por email e/ou WhatsApp
    resultados = []
    
    if enviar_para in ['email', 'ambos']:
        email = form.cleaned_data.get('email_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'email', email, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('Email', sucesso, msg))
    
    if enviar_para in ['whatsapp', 'ambos']:
        whatsapp = form.cleaned_data.get('whatsapp_destino')
        sucesso, msg = EnviadorRelatorio.enviar(
            'whatsapp', whatsapp, empresa.nome, arquivo_bytes, 
            nome_arquivo, formato
        )
        resultados.append(('WhatsApp', sucesso, msg))
    
    # Exibir resultados
    for tipo, sucesso, mensagem in resultados:
        if sucesso:
            messages.success(request, f'{tipo}: {mensagem}')
        else:
            messages.error(request, f'{tipo}: {mensagem}')
    
    return redirect('estoque:relatorio_produto')


# ===============================
# FASE 3 - Relatórios Avançados
# ===============================

from django.db.models.functions import Cast
from django.db.models import Case, When

@login_required
def relatorio_analise_abc(request):
    """
    Análise ABC de Produtos (Pareto)
    Classifica produtos por valor total movimentado
    """
    empresa = request.user.empresa
    
    # Pegar produtos com seus valores de movimentação
    produtos = Produto.objects.filter(
        categoria__empresa=empresa,
        ativo=True
    ).annotate(
        total_entrada=Sum(
            'movimentacoes_estoque__quantidade',
            filter=Q(movimentacoes_estoque__tipo='ENTRADA', movimentacoes_estoque__status='EXECUTADO')
        ),
        total_saida=Sum(
            'movimentacoes_estoque__quantidade',
            filter=Q(movimentacoes_estoque__tipo='SAIDA', movimentacoes_estoque__status='EXECUTADO')
        ),
        valor_estoque=models.F('estoque_atual') * models.F('preco_custo')
    ).filter(
        movimentacoes_estoque__isnull=False
    ).distinct()
    
    # Calcular valor total movimentado (entrada + saída) * preço médio
    produtos_com_valor = []
    valor_total_geral = 0
    
    for produto in produtos:
        total_entrada = produto.total_entrada or 0
        total_saida = produto.total_saida or 0
        total_quantidade = total_entrada + total_saida
        
        valor_estoque = float(produto.preco_custo or 0) * float(produto.estoque_atual or 0)
        valor_total_geral += valor_estoque
        
        produtos_com_valor.append({
            'produto': produto,
            'quantidade_total': total_quantidade,
            'valor_estoque': valor_estoque,
            'estoque_atual': produto.estoque_atual,
            'preco_custo': produto.preco_custo,
        })
    
    # Ordenar por valor de estoque descendente
    produtos_com_valor.sort(key=lambda x: x['valor_estoque'], reverse=True)
    
    # Calcular percentuais acumulados e classificar ABC
    acumulado = 0
    for item in produtos_com_valor:
        acumulado += item['valor_estoque']
        percentual_acumulado = (acumulado / valor_total_geral * 100) if valor_total_geral > 0 else 0
        
        # Classificação ABC
        if percentual_acumulado <= 80:
            item['classe'] = 'A'
        elif percentual_acumulado <= 95:
            item['classe'] = 'B'
        else:
            item['classe'] = 'C'
        
        item['percentual_acumulado'] = round(percentual_acumulado, 2)
        item['percentual_valor'] = round((item['valor_estoque'] / valor_total_geral * 100), 2) if valor_total_geral > 0 else 0
    
    # Contar por classe
    classe_a = len([p for p in produtos_com_valor if p['classe'] == 'A'])
    classe_b = len([p for p in produtos_com_valor if p['classe'] == 'B'])
    classe_c = len([p for p in produtos_com_valor if p['classe'] == 'C'])
    
    context = {
        'produtos': produtos_com_valor,
        'valor_total_geral': valor_total_geral,
        'classe_a_count': classe_a,
        'classe_b_count': classe_b,
        'classe_c_count': classe_c,
        'total_produtos': len(produtos_com_valor),
        'title': 'Análise ABC de Produtos',
    }
    
    return render(request, 'estoque/relatorio_abc.html', context)


@login_required
def relatorio_comparativo_periodos(request):
    """
    Comparativo de movimentações entre períodos
    """
    empresa = request.user.empresa
    
    # Período padrão: últimos 3 meses
    from datetime import datetime
    data_fim = timezone.now().date()
    data_inicio = data_fim - timedelta(days=90)
    
    if request.method == 'POST':
        data_inicio_str = request.POST.get('data_inicio')
        data_fim_str = request.POST.get('data_fim')
        if data_inicio_str and data_fim_str:
            data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()
    
    # Dividir em 3 períodos iguais
    dias_total = (data_fim - data_inicio).days
    dias_periodo = dias_total // 3
    
    periodo_1_inicio = data_inicio
    periodo_1_fim = data_inicio + timedelta(days=dias_periodo)
    
    periodo_2_inicio = periodo_1_fim + timedelta(days=1)
    periodo_2_fim = periodo_2_inicio + timedelta(days=dias_periodo)
    
    periodo_3_inicio = periodo_2_fim + timedelta(days=1)
    periodo_3_fim = data_fim
    
    # Dados por período
    def obter_dados_periodo(data_ini, data_fim):
        entradas = MovimentacaoEstoque.objects.filter(
            tipo='ENTRADA',
            status='EXECUTADO',
            data_movimentacao__date__gte=data_ini,
            data_movimentacao__date__lte=data_fim
        )
        
        saidas = MovimentacaoEstoque.objects.filter(
            tipo='SAIDA',
            status='EXECUTADO',
            data_movimentacao__date__gte=data_ini,
            data_movimentacao__date__lte=data_fim
        )
        
        # Calcular quantidades
        entrada_qtd = entradas.aggregate(qtd=Sum('quantidade'))['qtd'] or 0
        saida_qtd = saidas.aggregate(qtd=Sum('quantidade'))['qtd'] or 0
        
        # Calcular valores (em Python para evitar erro de agregação)
        entrada_val = 0
        for mov in entradas.select_related('produto'):
            entrada_val += (mov.quantidade * mov.produto.preco_custo) if mov.produto else 0
        
        saida_val = 0
        for mov in saidas.select_related('produto'):
            saida_val += (mov.quantidade * mov.produto.preco_custo) if mov.produto else 0
        
        return {
            'entradas_qtd': entrada_qtd,
            'entradas_val': float(entrada_val),
            'saidas_qtd': saida_qtd,
            'saidas_val': float(saida_val),
        }
    
    periodo_1 = obter_dados_periodo(periodo_1_inicio, periodo_1_fim)
    periodo_2 = obter_dados_periodo(periodo_2_inicio, periodo_2_fim)
    periodo_3 = obter_dados_periodo(periodo_3_inicio, periodo_3_fim)
    
    # Calcular variações
    periodo_1['label'] = f'{periodo_1_inicio.strftime("%d/%m")} a {periodo_1_fim.strftime("%d/%m")}'
    periodo_2['label'] = f'{periodo_2_inicio.strftime("%d/%m")} a {periodo_2_fim.strftime("%d/%m")}'
    periodo_3['label'] = f'{periodo_3_inicio.strftime("%d/%m")} a {periodo_3_fim.strftime("%d/%m")}'
    
    context = {
        'periodo_1': periodo_1,
        'periodo_2': periodo_2,
        'periodo_3': periodo_3,
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
        'title': 'Comparativo de Períodos',
    }
    
    return render(request, 'estoque/relatorio_comparativo.html', context)


@login_required
def relatorio_auditoria(request):
    """
    Auditoria de transações de estoque
    Quem fez o quê, quando e onde
    """
    empresa = request.user.empresa
    
    # Filtros
    tipo = request.GET.get('tipo', '')
    usuario = request.GET.get('usuario', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    movimentacoes = MovimentacaoEstoque.objects.filter(empresa=empresa).select_related(
        'produto', 'cadastrado_por', 'armazem_origem'
    ).order_by('-data_movimentacao')
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    
    if usuario:
        movimentacoes = movimentacoes.filter(cadastrado_por__username__icontains=usuario)
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_movimentacao__date__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data_movimentacao__date__lte=data_fim)

    paginator = Paginator(movimentacoes, 50)
    movimentacoes_page = paginator.get_page(request.GET.get('page'))

    context = {
        'movimentacoes': movimentacoes_page,
        'tipos_movimento': MovimentacaoEstoque.TIPO_CHOICES,
        'title': 'Auditoria de Transações',
        'filtros_ativos': bool(tipo or usuario or data_inicio or data_fim),
    }

    return render(request, 'estoque/relatorio_auditoria.html', context)


@login_required
def relatorio_rastreamento_lote(request, lote_id=None):
    """
    Rastreamento completo de um lote
    Mostra toda a jornada: entrada -> saídas
    """
    empresa = request.user.empresa
    
    if lote_id:
        lote = get_object_or_404(Lote, pk=lote_id, empresa=empresa)
        
        # Histórico do lote
        movimentacoes = MovimentacaoEstoque.objects.filter(
            lote=lote
        ).order_by('data_movimentacao')
        
        # Dados do lote
        dados_lote = {
            'numero': lote.numero_lote,
            'produto': lote.produto.nome,
            'quantidade_inicial': lote.quantidade_inicial,
            'quantidade_atual': lote.quantidade_atual,
            'status': lote.get_status_display(),
            'data_entrada': lote.data_entrada,
            'data_validade': lote.data_validade,
            'armazem': lote.armazem.nome,
            'local': str(lote.local_estocagem) if lote.local_estocagem else 'Não definido',
        }
        
        context = {
            'lote': dados_lote,
            'movimentacoes': movimentacoes,
            'title': f'Rastreamento do Lote {lote.numero_lote}',
        }
        
        return render(request, 'estoque/relatorio_rastreamento_lote.html', context)
    
    else:
        # Lista todos os lotes para seleção
        lotes = Lote.objects.filter(
            empresa=empresa
        ).select_related('produto', 'armazem')
        
        context = {
            'lotes': lotes,
            'title': 'Rastreamento de Lotes',
        }
        
        return render(request, 'estoque/lista_lotes_rastreamento.html', context)


@login_required
def relatorio_rastreamento_dashboard(request):
    """Dashboard de rastreamento de movimentações"""
    empresa = request.user.empresa
    data_fim = timezone.now().date()
    data_inicio = data_fim - timedelta(days=30)

    data_inicio_str = request.GET.get('data_inicio')
    data_fim_str = request.GET.get('data_fim')
    if data_inicio_str:
        try:
            data_inicio = timezone.datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if data_fim_str:
        try:
            data_fim = timezone.datetime.strptime(data_fim_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    tipo = request.GET.get('tipo', '')
    status = request.GET.get('status', '')
    armazem_id = request.GET.get('armazem', '')

    movimentacoes = MovimentacaoEstoque.objects.filter(
        empresa=empresa,
        data_movimentacao__date__gte=data_inicio,
        data_movimentacao__date__lte=data_fim
    )

    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if status:
        movimentacoes = movimentacoes.filter(status=status)
    if armazem_id:
        movimentacoes = movimentacoes.filter(
            Q(armazem_origem_id=armazem_id) | Q(armazem_destino_id=armazem_id)
        )

    total_movimentacoes = movimentacoes.count()
    por_tipo = movimentacoes.values('tipo').annotate(total=models.Count('id')).order_by('-total')
    por_status = movimentacoes.values('status').annotate(total=models.Count('id')).order_by('-total')

    por_armazem_origem = movimentacoes.filter(armazem_origem__isnull=False).values(
        'armazem_origem__nome'
    ).annotate(total=models.Count('id')).order_by('-total')[:10]

    por_armazem_destino = movimentacoes.filter(armazem_destino__isnull=False).values(
        'armazem_destino__nome'
    ).annotate(total=models.Count('id')).order_by('-total')[:10]

    recentes = movimentacoes.select_related(
        'produto', 'lote', 'armazem_origem', 'armazem_destino', 'cadastrado_por'
    ).order_by('-data_movimentacao')[:50]

    armazens = Armazem.objects.filter(empresa=empresa, ativo=True).order_by('nome')

    context = {
        'title': 'Dashboard de Rastreamento',
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
        'tipo': tipo,
        'status': status,
        'armazem_id': int(armazem_id) if armazem_id else None,
        'armazens': armazens,
        'total_movimentacoes': total_movimentacoes,
        'por_tipo': por_tipo,
        'por_status': por_status,
        'por_armazem_origem': por_armazem_origem,
        'por_armazem_destino': por_armazem_destino,
        'recentes': recentes,
        'tipos': MovimentacaoEstoque.TIPO_CHOICES,
        'status_choices': MovimentacaoEstoque.STATUS_CHOICES,
    }
    return render(request, 'estoque/relatorio_rastreamento_dashboard.html', context)


@login_required
def relatorio_validacao_disponibilidade(request):
    """Validação de disponibilidade de estoque (saldo x estoque_atual)"""
    from decimal import Decimal

    empresa = request.user.empresa
    busca = request.GET.get('busca', '')
    show_all = request.GET.get('show_all') == '1'

    produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
    if busca:
        produtos = produtos.filter(nome__icontains=busca)

    divergencias = []
    for produto in produtos:
        total_lotes = Lote.objects.filter(
            produto=produto,
            status__in=['DISPONIVEL', 'BLOQUEADO']
        ).aggregate(total=Sum('quantidade_atual'))['total'] or Decimal('0')

        movs_entrada = MovimentacaoEstoque.objects.filter(
            produto=produto,
            lote__isnull=True,
            tipo='ENTRADA',
            status='EXECUTADO'
        ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')

        movs_saida = MovimentacaoEstoque.objects.filter(
            produto=produto,
            lote__isnull=True,
            tipo='SAIDA',
            status='EXECUTADO'
        ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')

        saldo = Decimal(total_lotes) + (Decimal(movs_entrada) - Decimal(movs_saida))
        estoque_atual = Decimal(produto.estoque_atual or 0)
        diferenca = saldo - estoque_atual

        if show_all or float(diferenca) != 0.0:
            divergencias.append({
                'produto': produto,
                'estoque_atual': estoque_atual,
                'saldo_calculado': saldo,
                'diferenca': diferenca,
            })

    paginator = Paginator(divergencias, 30)
    divergencias_page = paginator.get_page(request.GET.get('page'))

    context = {
        'title': 'Validação de Disponibilidade',
        'busca': busca,
        'show_all': show_all,
        'divergencias': divergencias_page,
        'total_produtos': produtos.count(),
        'total_divergencias': len(divergencias),
    }
    return render(request, 'estoque/relatorio_validacao_disponibilidade.html', context)


@login_required
def api_dashboard_dados(request):
    """
    API para retornar dados do dashboard em JSON
    Para gráficos em tempo real
    """
    empresa = request.user.empresa
    
    # Últimos 30 dias
    data_inicio = timezone.now() - timedelta(days=30)
    
    # Movimentações por dia
    movimentacoes_dia = []
    
    for i in range(30):
        data = data_inicio + timedelta(days=i)
        entradas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='ENTRADA',
            status='EXECUTADO',
            data_movimentacao__date=data.date()
        ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0

        saidas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='SAIDA',
            status='EXECUTADO',
            data_movimentacao__date=data.date()
        ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        
        movimentacoes_dia.append({
            'data': data.strftime('%d/%m'),
            'entradas': float(entradas),
            'saidas': float(saidas),
        })
    
    # Produtos com menor estoque
    produtos_menor = Produto.objects.filter(
        categoria__empresa=empresa,
        ativo=True
    ).order_by('estoque_atual')[:5]
    
    produtos_lista = [{
        'nome': p.nome,
        'estoque': p.estoque_atual,
        'minimo': p.estoque_minimo,
        'alerta': p.estoque_atual < p.estoque_minimo
    } for p in produtos_menor]
    
    return JsonResponse({
        'movimentacoes': movimentacoes_dia,
        'produtos_baixos': produtos_lista,
    })


@login_required
def relatorio_alertas_estoque(request):
    """Relatório de alertas de estoque (Crítico e Excesso).

    Crítico = saldo real <= estoque mínimo (mesmo critério que a extinta
    Central de Alertas de Estoque Mínimo usava). Produtos críticos que
    controlam estoque e não têm solicitação de compra em aberto ganham
    checkbox no template para gerar, em lote, uma SolicitacaoCompra via
    compras:central_alertas_gerar_solicitacao — ação incorporada aqui para
    unificar as duas telas que existiam antes.
    """
    from compras.models import ItemSolicitacaoCompra
    from empresas.acesso import usuario_tem_acesso

    empresa = request.user.empresa
    produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)

    alertas_criticos = []
    alertas_excesso = []

    for produto in produtos:
        saldo = produto.calcular_saldo_real()

        # Categoriza alertas
        if saldo <= produto.estoque_minimo:
            alertas_criticos.append({
                'produto': produto,
                'saldo': saldo,
                'minimo': produto.estoque_minimo,
                'maximo': produto.estoque_maximo,
                'tipo': 'CRÍTICO',
            })
        elif produto.estoque_maximo > 0 and saldo > produto.estoque_maximo:
            alertas_excesso.append({
                'produto': produto,
                'saldo': saldo,
                'minimo': produto.estoque_minimo,
                'maximo': produto.estoque_maximo,
                'tipo': 'EXCESSO',
            })

    # Ordenar por saldo
    alertas_criticos.sort(key=lambda x: x['saldo'])
    alertas_excesso.sort(key=lambda x: x['saldo'], reverse=True)

    # Verificar se é exportação
    export_format = request.GET.get('export')

    if export_format == 'excel':
        return exportar_alertas_excel(empresa, alertas_criticos, alertas_excesso)
    elif export_format == 'pdf':
        return exportar_alertas_pdf(empresa, alertas_criticos, alertas_excesso)

    produtos_ja_solicitados = set(ItemSolicitacaoCompra.objects.filter(
        produto_id__in=[a['produto'].id for a in alertas_criticos],
    ).exclude(
        solicitacao__status__in=['CANCELADA', 'CONCLUIDA']
    ).values_list('produto_id', flat=True))

    for alerta in alertas_criticos:
        alerta['ja_solicitado'] = alerta['produto'].id in produtos_ja_solicitados
        alerta['pode_comprar'] = alerta['produto'].controla_estoque and not alerta['ja_solicitado']

    context = {
        'alertas_criticos': alertas_criticos,
        'alertas_excesso': alertas_excesso,
        'total_criticos': len(alertas_criticos),
        'total_excesso': len(alertas_excesso),
        'total_alertas': len(alertas_criticos) + len(alertas_excesso),
        'pode_gerar_compra': usuario_tem_acesso(request, 'compras:central_alertas_gerar_solicitacao'),
        'tem_criticos_compraveis': any(a['pode_comprar'] for a in alertas_criticos),
    }

    return render(request, 'estoque/relatorio_alertas.html', context)


def exportar_alertas_excel(empresa, alertas_criticos, alertas_excesso):
    """Exporta relatório de alertas para Excel"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from datetime import datetime
    except ImportError:
        return HttpResponse('Erro: openpyxl não instalado', status=500)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Alertas de Estoque"
    
    # Estilos
    header_fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Título
    ws['A1'] = f"Relatório de Alertas de Estoque - {empresa.nome}"
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:G1')
    
    # Data
    ws['A2'] = f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].font = Font(italic=True, size=10)
    
    # Cabeçalho Críticos
    ws['A4'] = "ALERTAS CRÍTICOS (Estoque ≤ Mínimo)"
    ws['A4'].font = Font(bold=True, size=11, color="FFFFFF")
    ws['A4'].fill = PatternFill(start_color="CC0000", end_color="CC0000", fill_type="solid")
    ws.merge_cells('A4:G4')
    
    # Cabeçalhos
    headers = ['Código', 'Produto', 'Categoria', 'Saldo Atual', 'Est. Mínimo', 'Est. Máximo', 'Unidade']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=5, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    # Dados Críticos
    row = 6
    for alerta in alertas_criticos:
        ws.cell(row, 1).value = alerta['produto'].codigo or '-'
        ws.cell(row, 2).value = alerta['produto'].nome
        ws.cell(row, 3).value = alerta['produto'].categoria.nome if alerta['produto'].categoria else '-'
        ws.cell(row, 4).value = float(alerta['saldo'])
        ws.cell(row, 5).value = float(alerta['minimo'])
        ws.cell(row, 6).value = float(alerta['maximo'])
        ws.cell(row, 7).value = alerta['produto'].unidade_medida.sigla if alerta['produto'].unidade_medida else '-'
        
        # Estilo linha crítica
        for col in range(1, 8):
            cell = ws.cell(row, col)
            cell.fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
            cell.border = border
            if col in [4, 5, 6]:
                cell.alignment = Alignment(horizontal='right')
        
        row += 1
    
    # Espaço
    row += 1
    
    # Cabeçalho Excesso
    ws.cell(row, 1).value = "ALERTAS DE EXCESSO (Estoque > Máximo)"
    ws.cell(row, 1).font = Font(bold=True, size=11, color="FFFFFF")
    ws.cell(row, 1).fill = PatternFill(start_color="0066CC", end_color="0066CC", fill_type="solid")
    ws.merge_cells(f'A{row}:G{row}')
    row += 1
    
    # Cabeçalhos Excesso
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal='center')
    
    row += 1
    
    # Dados Excesso
    for alerta in alertas_excesso:
        ws.cell(row, 1).value = alerta['produto'].codigo or '-'
        ws.cell(row, 2).value = alerta['produto'].nome
        ws.cell(row, 3).value = alerta['produto'].categoria.nome if alerta['produto'].categoria else '-'
        ws.cell(row, 4).value = float(alerta['saldo'])
        ws.cell(row, 5).value = float(alerta['minimo'])
        ws.cell(row, 6).value = float(alerta['maximo'])
        ws.cell(row, 7).value = alerta['produto'].unidade_medida.sigla if alerta['produto'].unidade_medida else '-'
        
        # Estilo linha excesso
        for col in range(1, 8):
            cell = ws.cell(row, col)
            cell.fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
            cell.border = border
            if col in [4, 5, 6]:
                cell.alignment = Alignment(horizontal='right')
        
        row += 1
    
    # Ajustar largura das colunas
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 12
    
    # Resposta HTTP
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="alertas_estoque_{datetime.now().strftime("%d_%m_%Y")}.xlsx"'
    
    wb.save(response)
    return response


def exportar_alertas_pdf(empresa, alertas_criticos, alertas_excesso):
    """Exporta relatório de alertas para PDF"""
    from datetime import datetime
    
    context = {
        'empresa': empresa,
        'alertas_criticos': alertas_criticos,
        'alertas_excesso': alertas_excesso,
        'total_criticos': len(alertas_criticos),
        'total_excesso': len(alertas_excesso),
        'data': datetime.now().strftime('%d/%m/%Y %H:%M'),
    }
    
    template = get_template('estoque/relatorio_alertas_pdf.html')
    html = template.render(context)
    
    result = io.BytesIO()
    pdf_status = pisa.CreatePDF(html, dest=result)
    
    if pdf_status.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    
    result.seek(0)
    response = HttpResponse(result.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="alertas_estoque_{datetime.now().strftime("%d_%m_%Y")}.pdf"'
    
    return response


# ============================================
# INVENTÁRIO CÍCLICO (RF-056)
# ============================================

@login_required
def inventario_ciclico_list(request):
    """Lista inventários cíclicos"""
    empresa = request.user.empresa
    inventarios_qs = InventarioCiclico.objects.filter(empresa=empresa).select_related('armazem', 'responsavel').order_by('-data_contagem')

    paginator = Paginator(inventarios_qs, 20)
    inventarios = paginator.get_page(request.GET.get('page'))

    context = {
        'inventarios': inventarios,
        'total_planejados': inventarios_qs.filter(status='PLANEJADO').count(),
        'total_em_contagem': inventarios_qs.filter(status='EM_CONTAGEM').count(),
        'total_finalizados': inventarios_qs.filter(status='FINALIZADO').count(),
        'total_inventarios': inventarios_qs.count(),
    }

    return render(request, 'estoque/inventario_ciclico_list.html', context)


@login_required
def inventario_ciclico_create(request):
    """Cria novo inventário cíclico com amostragem ABC
    
    Consolidação de estoque:
    - Lotes: DISPONIVEL + BLOQUEADO
    - Movimentações diretas: ENTRADA (sem lote) EXECUTADAS + SAIDA (sem lote) EXECUTADAS
    - Total = Lotes + Entradas - Saídas (para cada produto/lote)
    """
    empresa = request.user.empresa
    
    if request.method == 'POST':
        armazem_id = request.POST.get('armazem')
        categoria_abc = request.POST.get('categoria_abc', 'A')
        tipo_inventario = request.POST.get('tipo_inventario', 'POR_LOTE')
        
        armazem = get_object_or_404(Armazem, id=armazem_id, empresa=empresa)
        
        # Gera número único
        data_hoje = timezone.now().date()
        numero = f"IC-{data_hoje.strftime('%Y%m%d')}-{armazem.id:03d}-{InventarioCiclico.objects.filter(data_contagem=data_hoje).count() + 1:02d}"
        
        # Cria inventário
        inventario = InventarioCiclico.objects.create(
            empresa=empresa,
            numero=numero,
            armazem=armazem,
            tipo_inventario=tipo_inventario,
            data_contagem=data_hoje,
            status='PLANEJADO',
            responsavel=request.user,
        )
        
        if tipo_inventario == 'POR_ITEM':
            # Agrupa por produto, soma quantidades (LOTES + MOVIMENTAÇÕES DIRETAS)
            from django.db.models import Sum, Avg, Q
            from produtos.models import Produto
            
            # 1. Dados dos lotes
            lotes_dados = Lote.objects.filter(
                empresa=empresa,
                armazem=armazem,
                status__in=['DISPONIVEL', 'BLOQUEADO']
            ).values('produto').annotate(
                qtd_lotes=Sum('quantidade_atual'),
                valor_medio_lotes=Avg('valor_unitario'),
            )
            
            # 2. Dados de movimentações diretas (sem lote, status EXECUTADO)
            # Nota: Não filtramos por armazém pois nem sempre está preenchido
            # O usuário quer consolidar TODAS as entradas e saídas
            movimentacoes_entrada = MovimentacaoEstoque.objects.filter(
                empresa=empresa,
                lote__isnull=True,
                tipo='ENTRADA',
                status='EXECUTADO'
            ).values('produto').annotate(
                qtd_entrada=Sum('quantidade')
            )
            
            movimentacoes_saida = MovimentacaoEstoque.objects.filter(
                empresa=empresa,
                lote__isnull=True,
                tipo='SAIDA',
                status='EXECUTADO'
            ).values('produto').annotate(
                qtd_saida=Sum('quantidade')
            )
            
            # 3. Consolida todos os produtos que têm estoque
            produtos_consolidados = {}
            
            # Adiciona lotes
            for item in lotes_dados:
                prod_id = item['produto']
                produtos_consolidados[prod_id] = {
                    'qtd_lotes': item['qtd_lotes'] or Decimal('0'),
                    'valor_medio_lotes': item['valor_medio_lotes'] or Decimal('0'),
                    'qtd_entrada': Decimal('0'),
                    'qtd_saida': Decimal('0'),
                }
            
            # Adiciona entradas de movimentações
            for item in movimentacoes_entrada:
                prod_id = item['produto']
                if prod_id not in produtos_consolidados:
                    produtos_consolidados[prod_id] = {
                        'qtd_lotes': Decimal('0'),
                        'valor_medio_lotes': Decimal('0'),
                        'qtd_entrada': Decimal('0'),
                        'qtd_saida': Decimal('0'),
                    }
                produtos_consolidados[prod_id]['qtd_entrada'] = item['qtd_entrada'] or Decimal('0')
            
            # Adiciona saídas de movimentações
            for item in movimentacoes_saida:
                prod_id = item['produto']
                if prod_id not in produtos_consolidados:
                    produtos_consolidados[prod_id] = {
                        'qtd_lotes': Decimal('0'),
                        'valor_medio_lotes': Decimal('0'),
                        'qtd_entrada': Decimal('0'),
                        'qtd_saida': Decimal('0'),
                    }
                produtos_consolidados[prod_id]['qtd_saida'] = item['qtd_saida'] or Decimal('0')
            
            # 4. Calcula quantidade final = lotes + entrada - saída
            produtos_finais = []
            for prod_id, dados in produtos_consolidados.items():
                qtd_final = dados['qtd_lotes'] + dados['qtd_entrada'] - dados['qtd_saida']
                if qtd_final > 0:  # Apenas produtos com estoque
                    valor_unitario = dados['valor_medio_lotes'] or Decimal('0')
                    valor_total = qtd_final * valor_unitario
                    produtos_finais.append({
                        'produto_id': prod_id,
                        'quantidade': qtd_final,
                        'valor_unitario': valor_unitario,
                        'valor_total': valor_total,
                    })
            
            # 5. Ordena por valor total (DESC) e depois por quantidade (DESC) para produtos com valor_total=0
            produtos_finais.sort(key=lambda x: (-x['valor_total'], -x['quantidade']))
            
            total_valor = sum(p['valor_total'] for p in produtos_finais)
            # Se total_valor for 0 (todos os produtos sem valor), usa quantidade como métrica
            if total_valor == 0:
                total_quantidade = sum(p['quantidade'] for p in produtos_finais)
            else:
                total_quantidade = None
            
            valor_acumulado = Decimal('0')
            qtd_acumulada = Decimal('0')
            
            produtos_classificados = []
            itens_criados = 0
            
            for prod_data in produtos_finais:
                produto = Produto.objects.get(
                    id=prod_data['produto_id'],
                    categoria__empresa=empresa
                )
                valor_total = prod_data['valor_total']
                valor_acumulado += valor_total
                
                # Classificação ABC: por valor se houver, senão por quantidade
                if total_valor > 0:
                    percentual = (valor_acumulado / total_valor * 100)
                else:
                    qtd_acumulada += prod_data['quantidade']
                    percentual = (qtd_acumulada / total_quantidade * 100) if total_quantidade > 0 else 0
                
                # Classificação ABC
                if percentual <= 80:
                    classificacao = 'A'
                elif percentual <= 95:
                    classificacao = 'B'
                else:
                    classificacao = 'C'
                
                produtos_classificados.append((produto, classificacao, prod_data))
                
                # Filtra por categoria solicitada
                if categoria_abc != 'TODOS' and classificacao != categoria_abc:
                    continue
                
                InventarioCiclicoItem.objects.create(
                    inventario=inventario,
                    lote=None,  # Sem lote específico
                    produto=produto,
                    quantidade_sistema=prod_data['quantidade'],
                    valor_unitario_sistema=prod_data['valor_unitario'],
                    valor_total_sistema=valor_total,
                    classificacao_abc=classificacao,
                )
                itens_criados += 1
            
            # Fallback se nenhum item na classe
            if itens_criados == 0 and categoria_abc != 'TODOS':
                for produto, classificacao, prod_data in produtos_classificados:
                    InventarioCiclicoItem.objects.create(
                        inventario=inventario,
                        lote=None,
                        produto=produto,
                        quantidade_sistema=prod_data['quantidade'],
                        valor_unitario_sistema=prod_data['valor_unitario'],
                        valor_total_sistema=prod_data['valor_total'],
                        classificacao_abc=classificacao,
                    )
                messages.warning(
                    request,
                    'Nenhum item encontrado na classe selecionada. O inventário foi criado com todos os itens.'
                )
        else:
            # POR_LOTE: Consolida lotes + movimentações diretas
            from django.db.models import Q
            
            # 1. Agrupa lotes por produto
            lotes_dados = {}
            lotes_por_produto = Lote.objects.filter(
                empresa=empresa,
                armazem=armazem,
                status__in=['DISPONIVEL', 'BLOQUEADO']
            ).annotate(
                valor_unitario_safe=Coalesce('valor_unitario', Value(Decimal('0'), output_field=DecimalField()))
            )
            
            for lote in lotes_por_produto:
                prod_id = lote.produto.id
                valor_lote = lote.quantidade_atual * (lote.valor_unitario_safe or Decimal('0'))
                
                if prod_id not in lotes_dados:
                    lotes_dados[prod_id] = {
                        'valor_medio': Decimal('0'),
                        'qtd_lotes': Decimal('0'),
                        'valor_total_lotes': Decimal('0'),
                    }
                
                lotes_dados[prod_id]['qtd_lotes'] += lote.quantidade_atual
                lotes_dados[prod_id]['valor_total_lotes'] += valor_lote
                if lote.quantidade_atual > 0:
                    lotes_dados[prod_id]['valor_medio'] = lote.valor_unitario_safe
            
            # 2. Movimentações diretas por produto
            # Nota: Não filtramos por armazém pois nem sempre está preenchido
            movs_entrada_dados = MovimentacaoEstoque.objects.filter(
                empresa=empresa,
                lote__isnull=True,
                tipo='ENTRADA',
                status='EXECUTADO'
            ).values('produto').annotate(qtd=Sum('quantidade'))
            
            movs_saida_dados = MovimentacaoEstoque.objects.filter(
                empresa=empresa,
                lote__isnull=True,
                tipo='SAIDA',
                status='EXECUTADO'
            ).values('produto').annotate(qtd=Sum('quantidade'))
            
            movs_entrada_dict = {item['produto']: item['qtd'] for item in movs_entrada_dados}
            movs_saida_dict = {item['produto']: item['qtd'] for item in movs_saida_dados}
            
            # 3. Cria lista consolidada de itens para inventário
            itens_consolidados = {}
            
            # Adiciona lotes
            for lote in lotes_por_produto:
                prod_id = lote.produto.id
                if prod_id not in itens_consolidados:
                    itens_consolidados[prod_id] = {
                        'produto': lote.produto,
                        'itens_lote': [],
                        'qtd_entrada_mov': movs_entrada_dict.get(prod_id, Decimal('0')),
                        'qtd_saida_mov': movs_saida_dict.get(prod_id, Decimal('0')),
                    }
                
                valor_lote = lote.quantidade_atual * (lote.valor_unitario_safe or Decimal('0'))
                itens_consolidados[prod_id]['itens_lote'].append({
                    'lote': lote,
                    'quantidade': lote.quantidade_atual,
                    'valor_unitario': lote.valor_unitario_safe or Decimal('0'),
                    'valor_total': valor_lote,
                })
            
            # 4. Calcula valor total por produto para ABC (lotes + movimentações)
            itens_com_valor = []
            for prod_id, dados in itens_consolidados.items():
                valor_total_lotes = sum(item['valor_total'] for item in dados['itens_lote'])
                # Estima valor das movimentações usando valor_medio dos lotes
                valor_medio = dados['itens_lote'][0]['valor_unitario'] if dados['itens_lote'] else Decimal('0')
                valor_mov_entrada = dados['qtd_entrada_mov'] * valor_medio
                valor_mov_saida = dados['qtd_saida_mov'] * valor_medio
                valor_total = valor_total_lotes + valor_mov_entrada - valor_mov_saida
                
                itens_com_valor.append({
                    'prod_id': prod_id,
                    'valor_total': valor_total,
                    'dados': dados,
                })
            
            # Ordena por valor total
            itens_com_valor.sort(key=lambda x: x['valor_total'], reverse=True)
            
            total_valor = sum(item['valor_total'] for item in itens_com_valor)
            valor_acumulado = Decimal('0')
            
            itens_classificados = []
            itens_criados = 0
            
            for item_info in itens_com_valor:
                valor_total = item_info['valor_total']
                valor_acumulado += valor_total
                percentual = (valor_acumulado / total_valor * 100) if total_valor > 0 else 0
                
                # Classificação ABC
                if percentual <= 80:
                    classificacao = 'A'
                elif percentual <= 95:
                    classificacao = 'B'
                else:
                    classificacao = 'C'
                
                # Filtra por categoria
                if categoria_abc != 'TODOS' and classificacao != categoria_abc:
                    itens_classificados.append((item_info, classificacao))
                    continue
                
                # Cria item por lote
                dados = item_info['dados']
                for lote_info in dados['itens_lote']:
                    InventarioCiclicoItem.objects.create(
                        inventario=inventario,
                        lote=lote_info['lote'],
                        produto=dados['produto'],
                        quantidade_sistema=lote_info['quantidade'],
                        valor_unitario_sistema=lote_info['valor_unitario'],
                        valor_total_sistema=lote_info['valor_total'],
                        classificacao_abc=classificacao,
                    )
                    itens_criados += 1
                
                # Cria item para movimentações diretas consolidadas (se houver)
                qtd_mov_net = dados['qtd_entrada_mov'] - dados['qtd_saida_mov']
                if qtd_mov_net != 0:
                    valor_mov = qtd_mov_net * (dados['itens_lote'][0]['valor_unitario'] if dados['itens_lote'] else Decimal('0'))
                    InventarioCiclicoItem.objects.create(
                        inventario=inventario,
                        lote=None,  # Movimentação direta, sem lote
                        produto=dados['produto'],
                        quantidade_sistema=qtd_mov_net,
                        valor_unitario_sistema=dados['itens_lote'][0]['valor_unitario'] if dados['itens_lote'] else Decimal('0'),
                        valor_total_sistema=valor_mov,
                        classificacao_abc=classificacao,
                    )
                    itens_criados += 1
                
                itens_classificados.append((item_info, classificacao))
            
            # Fallback se nenhuma classe encontrada
            if itens_criados == 0 and categoria_abc != 'TODOS':
                for item_info, classificacao in itens_classificados:
                    dados = item_info['dados']
                    for lote_info in dados['itens_lote']:
                        InventarioCiclicoItem.objects.create(
                            inventario=inventario,
                            lote=lote_info['lote'],
                            produto=dados['produto'],
                            quantidade_sistema=lote_info['quantidade'],
                            valor_unitario_sistema=lote_info['valor_unitario'],
                            valor_total_sistema=lote_info['valor_total'],
                            classificacao_abc=classificacao,
                        )
                    
                    qtd_mov_net = dados['qtd_entrada_mov'] - dados['qtd_saida_mov']
                    if qtd_mov_net != 0:
                        valor_mov = qtd_mov_net * (dados['itens_lote'][0]['valor_unitario'] if dados['itens_lote'] else Decimal('0'))
                        InventarioCiclicoItem.objects.create(
                            inventario=inventario,
                            lote=None,
                            produto=dados['produto'],
                            quantidade_sistema=qtd_mov_net,
                            valor_unitario_sistema=dados['itens_lote'][0]['valor_unitario'] if dados['itens_lote'] else Decimal('0'),
                            valor_total_sistema=valor_mov,
                            classificacao_abc=classificacao,
                        )
                
                messages.warning(
                    request,
                    'Nenhum item encontrado na classe selecionada. O inventário foi criado com todos os itens.'
                )
        
        inventario.total_items_sistema = inventario.itens.count()
        inventario.save()
        
        messages.success(request, f'Inventário cíclico {numero} criado com {inventario.total_items_sistema} itens')
        return redirect('estoque:inventario_ciclico_detail', pk=inventario.id)
    
    armazens = Armazem.objects.filter(empresa=empresa, ativo=True)
    
    context = {
        'armazens': armazens,
    }
    
    return render(request, 'estoque/inventario_ciclico_create.html', context)


@login_required
def inventario_ciclico_detail(request, pk):
    """Detalha inventário cíclico e permite contagem"""
    empresa = request.user.empresa
    inventario = get_object_or_404(InventarioCiclico, id=pk, empresa=empresa)
    
    # Itens com classificação
    itens = inventario.itens.select_related('lote', 'produto', 'contado_por')
    
    # Paginação por classificação ABC
    classificacao = request.GET.get('classificacao', 'TODOS')
    if classificacao in ['A', 'B', 'C']:
        itens = itens.filter(classificacao_abc=classificacao)
    
    context = {
        'inventario': inventario,
        'itens': itens,
        'classificacao_selecionada': classificacao,
        'percentual_contagem': (inventario.total_items_contados / inventario.total_items_sistema * 100) if inventario.total_items_sistema > 0 else 0,
    }
    
    return render(request, 'estoque/inventario_ciclico_detail.html', context)


@login_required
def inventario_ciclico_registrar_contagem(request, pk):
    """Registra contagem de um item"""
    empresa = request.user.empresa
    item = get_object_or_404(InventarioCiclicoItem, id=pk, inventario__empresa=empresa)
    
    if request.method == 'POST':
        quantidade = Decimal(request.POST.get('quantidade', '0'))
        motivo = request.POST.get('motivo', '')
        
        item.registrar_contagem(quantidade, request.user)
        if item.tem_divergencia:
            item.motivo_divergencia = motivo
            item.save()
        
        messages.success(request, 'Contagem registrada com sucesso')
        return redirect('estoque:inventario_ciclico_detail', pk=item.inventario.id)
    
    context = {
        'item': item,
        'inventario': item.inventario,
    }
    
    return render(request, 'estoque/inventario_ciclico_registrar_contagem.html', context)


@login_required
def inventario_ciclico_conciliar(request, pk):
    """Realiza conciliação automática"""
    empresa = request.user.empresa
    inventario = get_object_or_404(InventarioCiclico, id=pk, empresa=empresa)
    
    if inventario.total_items_contados != inventario.total_items_sistema:
        messages.warning(request, 'Todos os itens devem ser contados antes de conciliar')
        return redirect('estoque:inventario_ciclico_detail', pk=inventario.id)
    
    inventario.conciliar()
    messages.success(request, f'Inventário conciliado. Acurácia: {inventario.acuracia_percentual:.2f}%')
    
    return redirect('estoque:inventario_ciclico_detail', pk=inventario.id)


@login_required
def inventario_ciclico_finalizar(request, pk):
    """Finaliza inventário cíclico"""
    empresa = request.user.empresa
    inventario = get_object_or_404(InventarioCiclico, id=pk, empresa=empresa)
    
    if inventario.status != 'CONCILIADO':
        messages.warning(request, 'Apenas inventários conciliados podem ser finalizados')
        return redirect('estoque:inventario_ciclico_detail', pk=inventario.id)
    
    inventario.finalizar()
    messages.success(request, 'Inventário finalizado com sucesso')
    
    return redirect('estoque:inventario_ciclico_detail', pk=inventario.id)


@login_required
def inventario_ciclico_relatorio_acuracia(request):
    """Relatório de acurácia de inventários"""
    empresa = request.user.empresa
    inventarios = InventarioCiclico.objects.filter(
        empresa=empresa,
        status__in=['CONCILIADO', 'FINALIZADO']
    ).order_by('-data_conciliacao')
    
    # Estatísticas gerais
    total_inventarios = inventarios.count()
    acuracia_media = inventarios.aggregate(
        media=models.Avg('acuracia_percentual')
    )['media'] or 0
    
    # Exportar Excel
    export = request.GET.get('export')
    if export == 'excel':
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            return HttpResponse('Erro: openpyxl não instalado', status=500)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Acurácia de Inventário"
        
        # Estilos
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Título
        ws['A1'] = f"Relatório de Acurácia de Inventário - {empresa.nome}"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:H1')
        
        # Resumo
        ws['A3'] = "Total de Inventários"
        ws['B3'] = total_inventarios
        ws['A4'] = "Acurácia Média"
        ws['B4'] = f"{acuracia_media:.2f}%"
        
        # Cabeçalhos
        headers = ['Número', 'Armazém', 'Data', 'Items', 'Divergências', 'Acurácia', 'Resultado', 'Valor Divergência']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=6, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        
        # Dados
        row = 7
        for inv in inventarios:
            ws.cell(row, 1).value = inv.numero
            ws.cell(row, 2).value = inv.armazem.nome
            ws.cell(row, 3).value = inv.data_contagem.strftime('%d/%m/%Y')
            ws.cell(row, 4).value = inv.total_items_sistema
            ws.cell(row, 5).value = inv.total_items_divergencia
            ws.cell(row, 6).value = f"{inv.acuracia_percentual:.2f}%"
            ws.cell(row, 7).value = inv.resultado or '-'
            ws.cell(row, 8).value = float(inv.valor_divergencia)
            
            # Estilo
            for col in range(1, 9):
                ws.cell(row, col).border = border
            
            row += 1
        
        # Largura das colunas
        ws.column_dimensions['A'].width = 18
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 15
        ws.column_dimensions['H'].width = 18
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="acuracia_inventario_{timezone.now().strftime("%d_%m_%Y")}.xlsx"'
        
        wb.save(response)
        return response
    
    context = {
        'inventarios': inventarios,
        'total_inventarios': total_inventarios,
        'acuracia_media': acuracia_media,
    }
    
    return render(request, 'estoque/inventario_ciclico_relatorio_acuracia.html', context)
