"""
Views para Requisicoes de Consumo
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import JsonResponse

from .models import Requisicao, RequisicaoItem, Talhao, Safra
from .forms import RequisicaoForm, RequisicaoItemForm
from estoque.models import MovimentacaoEstoque


def _gerar_numero_requisicao():
    ultimo = Requisicao.objects.order_by('-id').first()
    if not ultimo or not ultimo.numero:
        return 'REQ-000001'
    prefixo = 'REQ-'
    try:
        numero_atual = int(ultimo.numero.replace(prefixo, ''))
        return f"{prefixo}{numero_atual + 1:06d}"
    except ValueError:
        return f"{prefixo}{ultimo.id + 1:06d}"


@login_required
def requisicao_list(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')

    qs = Requisicao.objects.filter(empresa=empresa)
    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    tipo = request.GET.get('tipo', '').strip()

    if search:
        qs = qs.filter(
            Q(numero__icontains=search) |
            Q(safra__nome__icontains=search) |
            Q(fazenda__nome__icontains=search) |
            Q(talhao__nome__icontains=search) |
            Q(talhao__codigo__icontains=search) |
            Q(funcionario_destino__nome_completo__icontains=search)
        )

    if status:
        qs = qs.filter(status=status)
    if tipo:
        qs = qs.filter(tipo=tipo)

    qs = qs.select_related('safra', 'fazenda', 'talhao', 'funcionario_destino').order_by('-data_requisicao')

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastros/requisicao/list.html', {
        'requisicoes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
        'status': status,
        'tipo': tipo,
    })


@login_required
def requisicao_pendentes_aprovacao(request):
    """Lista requisições pendentes de aprovação (apenas para GERENTE e ADMIN)"""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')

    # Verifica permissão
    if not (request.user.tipo in ['ADMIN', 'GERENTE']):
        messages.error(request, 'Voce nao tem permissao para visualizar requisicoes pendentes.')
        return redirect('dashboard:index')

    # Filtra requisições PENDENTES
    qs = Requisicao.objects.filter(empresa=empresa, status='PENDENTE')
    search = request.GET.get('search', '').strip()

    if search:
        qs = qs.filter(
            Q(numero__icontains=search) |
            Q(safra__nome__icontains=search) |
            Q(fazenda__nome__icontains=search) |
            Q(talhao__nome__icontains=search) |
            Q(talhao__codigo__icontains=search) |
            Q(funcionario_destino__nome_completo__icontains=search) |
            Q(solicitante__nome_completo__icontains=search)
        )

    qs = qs.select_related('safra', 'fazenda', 'talhao', 'funcionario_destino', 'solicitante').order_by('-data_requisicao')

    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'cadastros/requisicao/pendentes_aprovacao.html', {
        'requisicoes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
        'total_pendentes': Requisicao.objects.filter(empresa=empresa, status='PENDENTE').count(),
    })


@login_required
def requisicao_create(request):
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = RequisicaoForm(request.POST, user=request.user)
        if form.is_valid():
            requisicao = form.save(commit=False)
            requisicao.empresa = empresa
            requisicao.solicitante = request.user
            requisicao.numero = _gerar_numero_requisicao()
            requisicao.status = 'PENDENTE'
            requisicao.save()
            messages.success(request, 'Requisicao criada com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoForm(user=request.user)
        form.fields['numero'].initial = _gerar_numero_requisicao()

    return render(request, 'cadastros/requisicao/form.html', {
        'form': form,
        'titulo': 'Nova Requisicao',
    })


@login_required
def requisicao_detail(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    itens = requisicao.itens.select_related('produto', 'unidade_medida').all()
    totais = itens.aggregate(
        total_solicitado=Sum('quantidade_solicitada'),
        total_atendido=Sum('quantidade_atendida'),
        total_estimado=Sum('custo_estimado'),
    )

    return render(request, 'cadastros/requisicao/detail.html', {
        'requisicao': requisicao,
        'itens': itens,
        'totais': totais,
    })


@login_required
def requisicao_update(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    if requisicao.status in ['ATENDIDA', 'CANCELADA']:
        messages.warning(request, 'Requisicao nao pode ser editada neste status.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        form = RequisicaoForm(request.POST, instance=requisicao, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Requisicao atualizada com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoForm(instance=requisicao, user=request.user)

    return render(request, 'cadastros/requisicao/form.html', {
        'form': form,
        'titulo': f'Editar Requisicao {requisicao.numero}',
        'requisicao': requisicao,
    })


@login_required
def requisicao_delete(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    if requisicao.status == 'ATENDIDA':
        messages.warning(request, 'Requisicao atendida nao pode ser excluida.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        requisicao.delete()
        messages.success(request, 'Requisicao excluida com sucesso.')
        return redirect('cadastros:requisicao_list')

    return render(request, 'cadastros/requisicao/confirm_delete.html', {
        'requisicao': requisicao,
    })


@login_required
def requisicao_aprovar(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    # Verifica se usuario é GERENTE ou ADMIN
    if not (request.user.tipo in ['ADMIN', 'GERENTE']):
        messages.error(request, 'Voce nao tem permissao para aprovar requisicoes.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if requisicao.status != 'PENDENTE':
        messages.warning(request, 'Apenas requisicoes pendentes podem ser aprovadas.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        requisicao.status = 'APROVADA'
        requisicao.aprovador = request.user
        requisicao.data_aprovacao = timezone.now()
        requisicao.save(update_fields=['status', 'aprovador', 'data_aprovacao'])
        messages.success(request, 'Requisicao aprovada com sucesso.')

    return redirect('cadastros:requisicao_detail', requisicao.id)


@login_required
def requisicao_atender(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    if requisicao.status != 'APROVADA':
        messages.warning(request, 'Apenas requisicoes aprovadas podem ser atendidas.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if not requisicao.itens.exists():
        messages.warning(request, 'Adicione itens antes de atender a requisicao.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        try:
            # Criar MovimentacaoEstoque para cada item da requisição
            for item in requisicao.itens.all():
                MovimentacaoEstoque.objects.create(
                    tipo='SAIDA',
                    origem='REQUISICAO',
                    status='EXECUTADO',
                    empresa=empresa,
                    produto=item.produto,
                    unidade_medida=item.unidade_medida,
                    quantidade=item.quantidade_solicitada or item.quantidade_atendida,
                    documento=requisicao.numero,
                    requisitante=requisicao.solicitante,
                    aprovador=requisicao.aprovador,
                    executado_por=request.user,
                    data_movimentacao=timezone.now(),
                    data_execucao=timezone.now(),
                    observacao=f'Requisição {requisicao.numero} - Item: {item.produto.nome}'
                )
            
            # Marcar requisição como ATENDIDA
            requisicao.status = 'ATENDIDA'
            requisicao.save(update_fields=['status'])
            messages.success(request, 'Requisicao atendida com sucesso. Movimentações de estoque criadas.')
        except Exception as e:
            messages.error(request, f'Erro ao atender requisicao: {str(e)}')

    return redirect('cadastros:requisicao_detail', requisicao.id)


@login_required
def requisicao_cancelar(request, pk):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=pk, empresa=empresa)

    if requisicao.status == 'ATENDIDA':
        messages.warning(request, 'Requisicao atendida nao pode ser cancelada.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        requisicao.status = 'CANCELADA'
        requisicao.save(update_fields=['status'])
        messages.success(request, 'Requisicao cancelada com sucesso.')

    return redirect('cadastros:requisicao_detail', requisicao.id)


@login_required
def requisicao_item_create(request, requisicao_id):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id, empresa=empresa)

    if requisicao.status == 'CANCELADA':
        messages.warning(request, 'Nao e possivel adicionar itens em requisicao cancelada.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        form = RequisicaoItemForm(request.POST, empresa=empresa)
        if form.is_valid():
            item = form.save(commit=False)
            item.requisicao = requisicao
            if not item.unidade_medida and item.produto:
                item.unidade_medida = item.produto.unidade_medida
            if item.custo_estimado in (None, '') and item.produto:
                item.custo_estimado = item.produto.preco_custo
            item.save()
            messages.success(request, 'Item adicionado com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoItemForm(empresa=empresa)

    return render(request, 'cadastros/requisicao/item_form.html', {
        'form': form,
        'requisicao': requisicao,
        'titulo': 'Adicionar Item',
    })


@login_required
def requisicao_item_update(request, requisicao_id, item_id):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id, empresa=empresa)
    item = get_object_or_404(RequisicaoItem, pk=item_id, requisicao=requisicao)

    if requisicao.status == 'CANCELADA':
        messages.warning(request, 'Nao e possivel editar itens em requisicao cancelada.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        form = RequisicaoItemForm(request.POST, instance=item, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item atualizado com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoItemForm(instance=item, empresa=empresa)

    return render(request, 'cadastros/requisicao/item_form.html', {
        'form': form,
        'requisicao': requisicao,
        'titulo': 'Editar Item',
        'item': item,
    })


@login_required
def requisicao_item_delete(request, requisicao_id, item_id):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id, empresa=empresa)
    item = get_object_or_404(RequisicaoItem, pk=item_id, requisicao=requisicao)

    if requisicao.status == 'CANCELADA':
        messages.warning(request, 'Nao e possivel excluir itens em requisicao cancelada.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item excluido com sucesso.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    return render(request, 'cadastros/requisicao/item_confirm_delete.html', {
        'requisicao': requisicao,
        'item': item,
    })


@login_required
def ajax_safras_por_talhao(request, talhao_id):
    """AJAX endpoint para obter safras vinculadas a um talhao"""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'safras': [], 'debug': 'Sem empresa'})
    
    try:
        talhao = Talhao.objects.select_related('fazenda').get(pk=talhao_id, fazenda__empresa=empresa)
        
        # Debug info
        debug_info = {
            'talhao_id': talhao_id,
            'talhao_nome': talhao.nome,
            'fazenda_id': talhao.fazenda.id,
            'fazenda_nome': talhao.fazenda.nome,
        }
        
        # Busca APENAS safras vinculadas ao talhão (relação M2M)
        safras = talhao.safras.select_related('cultura').order_by('-ano', 'nome')
        
        debug_info['total_safras_vinculadas'] = safras.count()
        
        result = []
        for safra in safras:
            base = safra.nome or str(safra.ano or '')
            cultura = safra.cultura.nome if safra.cultura else ''
            label = f"{base} - {cultura}" if base and cultura else (base or cultura or f"Safra {safra.id}")
            result.append({
                'id': safra.id,
                'label': label,
                'nome': safra.nome,
                'ano': safra.ano,
                'cultura': cultura
            })
        
        return JsonResponse({'safras': result, 'debug': debug_info})
    except Talhao.DoesNotExist:
        return JsonResponse({'safras': [], 'debug': f'Talhao {talhao_id} nao encontrado'})
    except Exception as e:
        return JsonResponse({'safras': [], 'debug': f'Erro: {str(e)}'})


@login_required
def ajax_talhao_por_codigo(request):
    """AJAX endpoint para obter talhao por codigo"""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'talhoes': []})
    
    codigo = request.GET.get('codigo', '').strip()
    if not codigo:
        return JsonResponse({'talhoes': []})
    
    talhoes = Talhao.objects.filter(
        codigo__icontains=codigo,
        fazenda__empresa=empresa
    ).values('id', 'codigo', 'nome', 'area__nome', 'fazenda__nome', 'fazenda_id').order_by('codigo')[:10]
    
    result = []
    for talhao in talhoes:
        result.append({
            'id': talhao['id'],
            'codigo': talhao['codigo'],
            'nome': talhao['nome'],
            'area': talhao['area__nome'],
            'fazenda': talhao['fazenda__nome'],
            'fazenda_id': talhao['fazenda_id'],
            'label': f"{talhao['codigo']} - {talhao['nome']} ({talhao['area__nome']})"
        })
    
    return JsonResponse({'talhoes': result})
