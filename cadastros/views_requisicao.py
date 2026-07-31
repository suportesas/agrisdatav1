"""
Views para Requisicoes de Consumo
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from core.pagination import paginate
from django.http import JsonResponse

from emprestimos.utils import enviar_whatsapp_emprestimo
from emprestimos.models import EmprestimoProdutor, EmprestimoMovimento
from .models import Requisicao, RequisicaoItem, Talhao, Safra
from .forms import RequisicaoForm, RequisicaoItemForm
from estoque.models import MovimentacaoEstoque
from produtos.models import Produto


def _recalcular_estoque_produto(produto, empresa):
    """Recalcula estoque_atual do produto somando todas as MovimentacaoEstoque da empresa."""
    from django.db.models import Sum, Q
    from decimal import Decimal
    movs = MovimentacaoEstoque.objects.filter(
        Q(produto=produto) | Q(lote__produto=produto),
        empresa=empresa,
    )
    entrada = movs.filter(tipo='ENTRADA').aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    saida = movs.filter(tipo='SAIDA').aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
    produto.estoque_atual = Decimal(entrada) - Decimal(saida)
    produto.save(update_fields=['estoque_atual'])


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
            Q(funcionario_destino__nome_completo__icontains=search) |
            Q(produtor__razao_social__icontains=search)
        )

    if status:
        qs = qs.filter(status=status)
    if tipo:
        qs = qs.filter(tipo=tipo)

    qs = qs.select_related('safra', 'fazenda', 'talhao', 'funcionario_destino', 'produtor').order_by('-data_requisicao')

    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'cadastros/requisicao/list.html', {
        'requisicoes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
        'status': status,
        'tipo': tipo,
        'per_page': per_page,
        'per_page_options': per_page_options,
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

    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'cadastros/requisicao/pendentes_aprovacao.html', {
        'requisicoes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
        'total_pendentes': Requisicao.objects.filter(empresa=empresa, status='PENDENTE').count(),
        'per_page': per_page,
        'per_page_options': per_page_options,
    })


@login_required
def requisicao_pendentes_atendimento(request):
    """Lista requisições aprovadas aguardando liberação/atendimento pelo almoxarifado"""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        messages.error(request, 'Usuario sem empresa vinculada.')
        return redirect('dashboard:index')

    # Filtra requisições APROVADAS
    qs = Requisicao.objects.filter(empresa=empresa, status='APROVADA')
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

    qs = qs.select_related('safra', 'fazenda', 'talhao', 'funcionario_destino', 'solicitante').order_by('-data_aprovacao')

    page_obj, per_page, per_page_options = paginate(request, qs)

    return render(request, 'cadastros/requisicao/pendentes_atendimento.html', {
        'requisicoes': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'search': search,
        'total_aguardando': Requisicao.objects.filter(empresa=empresa, status='APROVADA').count(),
        'per_page': per_page,
        'per_page_options': per_page_options,
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

    # Valor total do empréstimo: soma de quantidade_atendida * custo_estimado
    valor_total_emprestimo = sum([
        (item.quantidade_atendida or 0) * (item.custo_estimado or 0)
        for item in itens
    ])

    return render(request, 'cadastros/requisicao/detail.html', {
        'requisicao': requisicao,
        'itens': itens,
        'totais': totais,
        'valor_total_emprestimo': valor_total_emprestimo,
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
        # PLANO: Preenche campos globais de assinatura de liberação interna
        requisicao.assinatura_liberacao_interna_usuario = request.user
        requisicao.assinatura_liberacao_interna_nome = request.user.get_full_name() or request.user.username
        requisicao.assinatura_liberacao_interna_datahora = timezone.now()
        requisicao.save(update_fields=['status', 'aprovador', 'data_aprovacao', 'assinatura_liberacao_interna_usuario', 'assinatura_liberacao_interna_nome', 'assinatura_liberacao_interna_datahora'])
        messages.success(request, 'Requisicao aprovada e assinatura de liberação registrada.')

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
            mensagens_whatsapp = []
            if requisicao.tipo == 'EMPRESTIMO' and not requisicao.produtor:
                messages.error(request, 'Selecione um produtor antes de atender empréstimos.')
                return redirect('cadastros:requisicao_detail', requisicao.id)
            if requisicao.tipo == 'EMPRESTIMO' and not (requisicao.recebedor_material or '').strip():
                messages.error(request, 'Informe o recebedor do material antes de atender empréstimos.')
                return redirect('cadastros:requisicao_detail', requisicao.id)

            sai_do_estoque = not (requisicao.tipo == 'EMPRESTIMO' and requisicao.direcao_emprestimo == 'PRODUTOR_PARA_EMPRESA')
            if sai_do_estoque:
                from decimal import Decimal
                from estoque.disponibilidade import reservas_por_produto

                consumo_por_produto = {}
                produtos_por_id = {}
                for item in requisicao.itens.select_related('produto'):
                    quantidade_base = item.quantidade_atendida or item.quantidade_solicitada
                    consumo_por_produto[item.produto_id] = consumo_por_produto.get(item.produto_id, Decimal('0')) + (quantidade_base or Decimal('0'))
                    produtos_por_id[item.produto_id] = item.produto

                reservas = reservas_por_produto(empresa, excluir_requisicao_id=requisicao.id)
                produtos_sem_saldo = []
                for produto_id, consumo in consumo_por_produto.items():
                    produto = produtos_por_id[produto_id]
                    disponivel = Decimal(produto.estoque_atual or 0) - reservas.get(produto_id, Decimal('0'))
                    if disponivel < consumo:
                        produtos_sem_saldo.append(
                            f"{produto.nome} (disponível: {disponivel}, necessário: {consumo})"
                        )

                if produtos_sem_saldo:
                    messages.error(
                        request,
                        'Saldo insuficiente para atender a requisicao. Ajuste os itens: ' + '; '.join(sorted(set(produtos_sem_saldo)))
                    )
                    return redirect('cadastros:requisicao_detail', requisicao.id)

            # Criar MovimentacaoEstoque para cada item da requisição
            for item in requisicao.itens.all():
                quantidade_base = item.quantidade_atendida or item.quantidade_solicitada
                tipo_movimento_estoque = 'SAIDA'

                if requisicao.tipo == 'EMPRESTIMO' and requisicao.direcao_emprestimo == 'PRODUTOR_PARA_EMPRESA':
                    tipo_movimento_estoque = 'ENTRADA'

                MovimentacaoEstoque.objects.create(
                    tipo=tipo_movimento_estoque,
                    origem='REQUISICAO',
                    status='EXECUTADO',
                    empresa=empresa,
                    produto=item.produto,
                    unidade_medida=item.unidade_medida,
                    quantidade=quantidade_base,
                    documento=requisicao.numero,
                    requisitante=requisicao.solicitante,
                    aprovador=requisicao.aprovador,
                    executado_por=request.user,
                    data_movimentacao=timezone.now(),
                    data_execucao=timezone.now(),
                    observacao=f'Requisição {requisicao.numero} - Item: {item.produto.nome}'
                )
                _recalcular_estoque_produto(item.produto, empresa)

                if requisicao.tipo == 'EMPRESTIMO':
                    status_emprestimo = 'PROMESSA' if requisicao.data_promessa_devolucao else 'NORMAL'
                    emprestimo = EmprestimoProdutor.objects.create(
                        empresa=empresa,
                        produtor=requisicao.produtor,
                        produto=item.produto,
                        unidade_medida=item.unidade_medida,
                        requisicao=requisicao,
                        requisicao_item=item,
                        direcao=requisicao.direcao_emprestimo,
                        data_emprestimo=timezone.now(),
                        data_promessa_devolucao=requisicao.data_promessa_devolucao,
                        status=status_emprestimo,
                        quantidade_emprestada=quantidade_base,
                        quantidade_devolvida=0,
                        observacoes=f'Gerado automaticamente pela requisição {requisicao.numero}.',
                        criado_por=request.user,
                    )

                    EmprestimoMovimento.objects.create(
                        empresa=empresa,
                        emprestimo=emprestimo,
                        tipo_movimento='EMPRESTIMO',
                        quantidade=quantidade_base,
                        saldo_resultante=emprestimo.saldo_pendente,
                        data_movimento=timezone.now(),
                        documento_referencia=requisicao.numero,
                        observacoes='Lançamento automático no atendimento da requisição.',
                        criado_por=request.user,
                    )

                    sucesso_envio, retorno_envio = enviar_whatsapp_emprestimo(request, emprestimo)
                    if not sucesso_envio:
                        mensagens_whatsapp.append(f'{item.produto.nome}: {retorno_envio}')
            
            # Marcar requisição como ATENDIDA
            requisicao.status = 'ATENDIDA'
            requisicao.save(update_fields=['status'])
            messages.success(request, 'Requisicao atendida com sucesso. Movimentações de estoque criadas.')
            if mensagens_whatsapp:
                messages.warning(request, 'Alguns envios de WhatsApp não foram concluídos: ' + ' | '.join(mensagens_whatsapp))
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


_STATUS_ITENS_BLOQUEADOS = ('CANCELADA', 'ATENDIDA')


def _revogar_aprovacao_se_necessario(requisicao):
    """Se a requisicao ja estava APROVADA, qualquer alteracao nos itens a faz
    voltar para PENDENTE, exigindo nova aprovacao antes de poder ser atendida."""
    if requisicao.status != 'APROVADA':
        return False

    requisicao.status = 'PENDENTE'
    requisicao.aprovador = None
    requisicao.data_aprovacao = None
    requisicao.assinatura_liberacao_interna_usuario = None
    requisicao.assinatura_liberacao_interna_nome = ''
    requisicao.assinatura_liberacao_interna_datahora = None
    requisicao.save(update_fields=[
        'status', 'aprovador', 'data_aprovacao',
        'assinatura_liberacao_interna_usuario',
        'assinatura_liberacao_interna_nome',
        'assinatura_liberacao_interna_datahora',
    ])
    return True


@login_required
def requisicao_item_create(request, requisicao_id):
    empresa = getattr(request.user, 'empresa', None)
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id, empresa=empresa)

    if requisicao.status in _STATUS_ITENS_BLOQUEADOS:
        messages.warning(request, 'Nao e possivel adicionar itens em requisicao cancelada ou ja atendida.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        form = RequisicaoItemForm(request.POST, empresa=empresa, requisicao_tipo=requisicao.tipo, requisicao=requisicao)
        if form.is_valid():
            item = form.save(commit=False)
            item.requisicao = requisicao
            if not item.unidade_medida and item.produto:
                item.unidade_medida = item.produto.unidade_medida
            if item.custo_estimado in (None, '') and item.produto:
                if requisicao.tipo == 'EMPRESTIMO':
                    item.custo_estimado = item.produto.preco_venda
                else:
                    item.custo_estimado = item.produto.preco_custo
            item.save()

            if _revogar_aprovacao_se_necessario(requisicao):
                messages.warning(request, 'Item adicionado. Como a requisicao ja estava aprovada, ela voltou para PENDENTE e precisa ser aprovada novamente antes de ser liberada.')
            else:
                messages.success(request, 'Item adicionado com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoItemForm(empresa=empresa, requisicao_tipo=requisicao.tipo, requisicao=requisicao)

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

    if requisicao.status in _STATUS_ITENS_BLOQUEADOS:
        messages.warning(request, 'Nao e possivel editar itens em requisicao cancelada ou ja atendida.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        form = RequisicaoItemForm(request.POST, instance=item, empresa=empresa, requisicao_tipo=requisicao.tipo, requisicao=requisicao)
        if form.is_valid():
            form.save()
            if _revogar_aprovacao_se_necessario(requisicao):
                messages.warning(request, 'Item atualizado. Como a requisicao ja estava aprovada, ela voltou para PENDENTE e precisa ser aprovada novamente antes de ser liberada.')
            else:
                messages.success(request, 'Item atualizado com sucesso.')
            return redirect('cadastros:requisicao_detail', requisicao.id)
    else:
        form = RequisicaoItemForm(instance=item, empresa=empresa, requisicao_tipo=requisicao.tipo, requisicao=requisicao)

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

    if requisicao.status in _STATUS_ITENS_BLOQUEADOS:
        messages.warning(request, 'Nao e possivel excluir itens em requisicao cancelada ou ja atendida.')
        return redirect('cadastros:requisicao_detail', requisicao.id)

    if request.method == 'POST':
        item.delete()
        if _revogar_aprovacao_se_necessario(requisicao):
            messages.warning(request, 'Item excluido. Como a requisicao ja estava aprovada, ela voltou para PENDENTE e precisa ser aprovada novamente antes de ser liberada.')
        else:
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
        
        # Busca as culturas de safra às quais este talhão foi atribuído
        culturas_safra = talhao.culturas_safra.select_related('safra', 'cultura').order_by('-safra__ano', 'safra__nome')

        debug_info['total_safras_vinculadas'] = culturas_safra.count()

        result = []
        for sc in culturas_safra:
            result.append({
                'id': sc.safra_id,  # Requisicao.safra é FK para Safra, não SafraCultura
                'label': str(sc),
                'nome': sc.safra.nome,
                'ano': sc.safra.ano,
                'cultura': sc.cultura.nome,
            })

        return JsonResponse({'safras': result, 'debug': debug_info})
    except Talhao.DoesNotExist:
        return JsonResponse({'safras': [], 'debug': f'Talhao {talhao_id} nao encontrado'})
    except Exception as e:
        return JsonResponse({'safras': [], 'debug': f'Erro: {str(e)}'})


@login_required
def ajax_funcionarios_por_fazenda(request, fazenda_id):
    """AJAX endpoint para filtrar funcionários por fazenda selecionada"""
    from rh.models import Funcionario
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'funcionarios': []})

    funcionarios = Funcionario.objects.filter(
        empresa=empresa,
        fazenda_id=fazenda_id,
        ativo=True,
    ).values('id', 'nome_completo', 'matricula').order_by('nome_completo')

    result = [
        {
            'id': f['id'],
            'label': f"{f['nome_completo']} ({f['matricula']})" if f['matricula'] else f['nome_completo'],
        }
        for f in funcionarios
    ]
    return JsonResponse({'funcionarios': result})


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


@login_required
def ajax_produto_dados_requisicao(request, produto_id):
    """AJAX endpoint para obter unidade e valor sugerido por tipo da requisicao."""
    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'Usuario sem empresa.'}, status=400)

    requisicao_id = request.GET.get('requisicao_id')
    if not requisicao_id:
        return JsonResponse({'success': False, 'error': 'Requisicao nao informada.'}, status=400)

    try:
        requisicao = Requisicao.objects.get(pk=requisicao_id, empresa=empresa)
    except Requisicao.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Requisicao nao encontrada.'}, status=404)

    try:
        produto = Produto.objects.select_related('unidade_medida').get(
            pk=produto_id,
            categoria__empresa=empresa,
            ativo=True,
        )
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Produto nao encontrado.'}, status=404)

    valor_sugerido = produto.preco_venda if requisicao.tipo == 'EMPRESTIMO' else produto.preco_custo

    return JsonResponse({
        'success': True,
        'unidade_medida_id': produto.unidade_medida_id,
        'unidade_medida_nome': produto.unidade_medida.sigla if produto.unidade_medida_id else '',
        'valor_sugerido': float(valor_sugerido or 0),
        'tipo_requisicao': requisicao.tipo,
    })
