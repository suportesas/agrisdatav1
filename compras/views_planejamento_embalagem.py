"""
Views para Planejamento de Compras de Embalagens.
Documento de previsão de necessidades por safra — não é SC nem PO,
mas pode gerar ambos via ação dedicada.
"""
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse

from .models import (
    PlanejamentoComprasEmbalagem,
    ItemPlanejamentoEmbalagem,
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    PedidoCompra,
    ItemPedidoCompra,
)
from .forms import (
    PlanejamentoComprasEmbalagemForm,
    ItemPlanejamentoFormSet,
    ItemPlanejamentoEmbalagemForm,
    RevisarPrecosItemForm,
)


# ─────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_list(request):
    empresa = request.user.empresa
    qs = PlanejamentoComprasEmbalagem.objects.filter(empresa=empresa).prefetch_related('itens')

    status_filtro = request.GET.get('status', '')
    safra_filtro = request.GET.get('safra', '')
    if status_filtro:
        qs = qs.filter(status=status_filtro)
    if safra_filtro:
        qs = qs.filter(safra_id=safra_filtro)

    from cadastros.models import Safra
    safras = Safra.objects.filter(fazenda__empresa=empresa).order_by('-ano', 'nome')

    paginator = Paginator(qs.order_by('-criado_em'), 20)
    planejamentos = paginator.get_page(request.GET.get('page'))

    return render(request, 'compras/planejamento_embalagem_list.html', {
        'planejamentos': planejamentos,
        'safras': safras,
        'status_filtro': status_filtro,
        'safra_filtro': safra_filtro,
        'status_choices': PlanejamentoComprasEmbalagem.STATUS,
    })


# ─────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = PlanejamentoComprasEmbalagemForm(request.POST, empresa=empresa)
        formset = ItemPlanejamentoFormSet(request.POST, empresa=empresa)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                planejamento = form.save(commit=False)
                planejamento.empresa = empresa
                planejamento.responsavel = planejamento.responsavel or request.user
                planejamento.save()
                formset.instance = planejamento
                itens = formset.save(commit=False)
                for item in itens:
                    if not item.preco_atual_unitario:
                        item.preco_atual_unitario = item.preco_estimado_unitario
                    item.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, f'Planejamento {planejamento.numero} criado com sucesso.')
            return redirect('compras:planejamento_embalagem_detail', pk=planejamento.pk)
    else:
        form = PlanejamentoComprasEmbalagemForm(empresa=empresa, initial={'responsavel': request.user})
        formset = ItemPlanejamentoFormSet(empresa=empresa)

    return render(request, 'compras/planejamento_embalagem_form.html', {
        'form': form,
        'formset': formset,
        'entry_form': ItemPlanejamentoEmbalagemForm(empresa=empresa, prefix='entry'),
        'titulo': 'Novo Planejamento de Embalagens',
        'modo': 'criar',
    })


# ─────────────────────────────────────────────
# DETAIL
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_detail(request, pk):
    empresa = request.user.empresa
    planejamento = get_object_or_404(
        PlanejamentoComprasEmbalagem.objects.prefetch_related(
            'itens__produto',
            'itens__tipo_embalagem',
            'itens__unidade_medida',
            'itens__fornecedor_preferencial',
            'itens__solicitacao_compra',
            'itens__pedido_compra',
        ),
        pk=pk, empresa=empresa,
    )
    return render(request, 'compras/planejamento_embalagem_detail.html', {
        'planejamento': planejamento,
    })


# ─────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_update(request, pk):
    empresa = request.user.empresa
    planejamento = get_object_or_404(
        PlanejamentoComprasEmbalagem,
        pk=pk, empresa=empresa,
    )
    if planejamento.status not in ('RASCUNHO', 'EM_REVISAO'):
        messages.warning(request, 'Apenas planejamentos em Rascunho ou Em Revisão podem ser editados.')
        return redirect('compras:planejamento_embalagem_detail', pk=pk)

    if request.method == 'POST':
        form = PlanejamentoComprasEmbalagemForm(request.POST, instance=planejamento, empresa=empresa)
        formset = ItemPlanejamentoFormSet(request.POST, instance=planejamento, empresa=empresa)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                itens = formset.save(commit=False)
                for item in itens:
                    if not item.preco_atual_unitario:
                        item.preco_atual_unitario = item.preco_estimado_unitario
                    item.save()
                for obj in formset.deleted_objects:
                    obj.delete()
            messages.success(request, 'Planejamento atualizado.')
            return redirect('compras:planejamento_embalagem_detail', pk=pk)
    else:
        form = PlanejamentoComprasEmbalagemForm(instance=planejamento, empresa=empresa)
        formset = ItemPlanejamentoFormSet(instance=planejamento, empresa=empresa)

    return render(request, 'compras/planejamento_embalagem_form.html', {
        'form': form,
        'formset': formset,
        'entry_form': ItemPlanejamentoEmbalagemForm(empresa=empresa, prefix='entry'),
        'planejamento': planejamento,
        'titulo': f'Editar {planejamento.numero}',
        'modo': 'editar',
    })


# ─────────────────────────────────────────────
# APROVAR
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_aprovar(request, pk):
    empresa = request.user.empresa
    planejamento = get_object_or_404(PlanejamentoComprasEmbalagem, pk=pk, empresa=empresa)
    if request.method == 'POST':
        if planejamento.status in ('RASCUNHO', 'EM_REVISAO'):
            planejamento.status = 'APROVADO'
            planejamento.save(update_fields=['status', 'atualizado_em'])
            messages.success(request, f'Planejamento {planejamento.numero} aprovado.')
        else:
            messages.warning(request, 'Planejamento não pode ser aprovado neste status.')
    return redirect('compras:planejamento_embalagem_detail', pk=pk)


# ─────────────────────────────────────────────
# REVISAR PREÇOS
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_revisar_precos(request, pk):
    empresa = request.user.empresa
    planejamento = get_object_or_404(PlanejamentoComprasEmbalagem, pk=pk, empresa=empresa)
    itens = planejamento.itens.select_related('produto', 'tipo_embalagem', 'unidade_medida').all()

    if request.method == 'POST':
        with transaction.atomic():
            for item in itens:
                preco_novo = request.POST.get(f'preco_{item.pk}', '').strip()
                obs = request.POST.get(f'obs_{item.pk}', '').strip()
                if preco_novo:
                    try:
                        from decimal import Decimal, InvalidOperation
                        item.preco_atual_unitario = Decimal(preco_novo.replace(',', '.'))
                        item.observacoes = obs
                        item.save(update_fields=['preco_atual_unitario', 'observacoes'])
                    except (ValueError, InvalidOperation):
                        pass
        planejamento.status = 'EM_REVISAO' if planejamento.status == 'APROVADO' else planejamento.status
        planejamento.save(update_fields=['status', 'atualizado_em'])
        messages.success(request, 'Preços atualizados com sucesso.')
        return redirect('compras:planejamento_embalagem_detail', pk=pk)

    return render(request, 'compras/planejamento_embalagem_revisar_precos.html', {
        'planejamento': planejamento,
        'itens': itens,
    })


# ─────────────────────────────────────────────
# GERAR SC OU PO
# ─────────────────────────────────────────────

@login_required
def planejamento_embalagem_gerar(request, pk):
    empresa = request.user.empresa
    planejamento = get_object_or_404(PlanejamentoComprasEmbalagem, pk=pk, empresa=empresa)

    if planejamento.status not in ('APROVADO', 'EM_REVISAO', 'RASCUNHO'):
        messages.warning(request, 'Planejamento encerrado — não é possível gerar documentos.')
        return redirect('compras:planejamento_embalagem_detail', pk=pk)

    itens_planejados = planejamento.itens.filter(status='PLANEJADO').select_related(
        'produto', 'tipo_embalagem', 'unidade_medida', 'fornecedor_preferencial'
    )

    if request.method == 'POST':
        tipo_geracao = request.POST.get('tipo_geracao')  # 'SC' ou 'PO'
        ids_selecionados = request.POST.getlist('itens_selecionados')

        if not ids_selecionados:
            messages.warning(request, 'Selecione pelo menos um item.')
            return redirect(request.path)

        itens_para_gerar = itens_planejados.filter(pk__in=ids_selecionados)

        if tipo_geracao == 'SC':
            return _gerar_solicitacao(request, planejamento, itens_para_gerar)
        elif tipo_geracao == 'PO':
            return _gerar_pedido_direto(request, planejamento, itens_para_gerar)
        else:
            messages.error(request, 'Tipo de geração inválido.')

    return render(request, 'compras/planejamento_embalagem_gerar.html', {
        'planejamento': planejamento,
        'itens': itens_planejados,
    })


def _gerar_solicitacao(request, planejamento, itens):
    """Cria uma SolicitacaoCompra a partir dos itens do planejamento."""
    empresa = request.user.empresa
    with transaction.atomic():
        solicitacao = SolicitacaoCompra.objects.create(
            empresa=empresa,
            solicitante=request.user,
            justificativa=f'Gerado do planejamento {planejamento.numero} — {planejamento.nome}',
            departamento='Embalagem',
            status='PENDENTE',
        )
        for item in itens:
            # Fallback para tipo_embalagem.produto mantém compatibilidade com
            # itens antigos criados antes do campo produto existir.
            produto = item.produto or (item.tipo_embalagem.produto if item.tipo_embalagem else None)
            if not produto:
                messages.warning(
                    request,
                    f'Item "{item.tipo_embalagem or item}" não tem produto cadastrado — ignorado na solicitação.',
                )
                continue
            ItemSolicitacaoCompra.objects.create(
                solicitacao=solicitacao,
                produto=produto,
                quantidade=item.quantidade_planejada,
                unidade_medida=item.unidade_medida,
                especificacao=str(item.tipo_embalagem) if item.tipo_embalagem else '',
                observacoes=item.observacoes,
            )
            item.solicitacao_compra = solicitacao
            item.status = 'SOLICITADO'
            item.save(update_fields=['solicitacao_compra', 'status'])

    messages.success(
        request,
        f'Solicitação de Compra {solicitacao.numero} gerada com sucesso. '
        f'Acesse para enviar para aprovação.',
    )
    return redirect('compras:solicitacao_detail', pk=solicitacao.pk)


def _gerar_pedido_direto(request, planejamento, itens):
    """Cria PedidoCompra diretamente (sem cotação), agrupando por fornecedor preferencial."""
    empresa = request.user.empresa
    from collections import defaultdict
    from datetime import date

    grupos = defaultdict(list)
    sem_fornecedor = []
    for item in itens:
        if item.fornecedor_preferencial:
            grupos[item.fornecedor_preferencial].append(item)
        else:
            sem_fornecedor.append(item)

    if sem_fornecedor:
        nomes = ', '.join(str(i.produto or i.tipo_embalagem) for i in sem_fornecedor)
        messages.warning(
            request,
            f'Os itens a seguir não têm fornecedor preferencial e foram ignorados: {nomes}. '
            'Atribua um fornecedor preferencial ou gere uma Solicitação de Compra.',
        )

    if not grupos:
        messages.error(request, 'Nenhum item com fornecedor preferencial para gerar pedido.')
        return redirect('compras:planejamento_embalagem_detail', pk=planejamento.pk)

    pedidos_criados = []
    with transaction.atomic():
        for fornecedor, itens_grupo in grupos.items():
            pedido = PedidoCompra.objects.create(
                empresa=empresa,
                fornecedor=fornecedor,
                comprador=request.user,
                status='RASCUNHO',
                observacoes=f'Gerado do planejamento {planejamento.numero} — {planejamento.nome}',
                data_entrega_prevista=min(i.data_prevista for i in itens_grupo),
            )
            for item in itens_grupo:
                produto = item.produto or (item.tipo_embalagem.produto if item.tipo_embalagem else None)
                if not produto:
                    messages.warning(
                        request,
                        f'Item "{item.tipo_embalagem or item}" não tem produto cadastrado — ignorado no pedido.',
                    )
                    continue
                ItemPedidoCompra.objects.create(
                    pedido=pedido,
                    produto=produto,
                    quantidade_pedida=item.quantidade_planejada,
                    unidade_medida=item.unidade_medida,
                    preco_unitario=item.preco_atual_unitario,
                    especificacao=str(item.tipo_embalagem) if item.tipo_embalagem else '',
                    observacoes=item.observacoes,
                )
                item.pedido_compra = pedido
                item.status = 'PEDIDO'
                item.save(update_fields=['pedido_compra', 'status'])
            pedido.calcular_total()
            pedido.save()
            pedidos_criados.append(pedido)

    numeros = ', '.join(p.numero for p in pedidos_criados)
    messages.success(request, f'Pedido(s) de Compra gerado(s): {numeros}.')
    if len(pedidos_criados) == 1:
        return redirect('compras:pedido_detail', pk=pedidos_criados[0].pk)
    return redirect('compras:planejamento_embalagem_detail', pk=planejamento.pk)


# ─────────────────────────────────────────────
# API — DADOS DO PRODUTO PARA AUTOPREENCHIMENTO
# ─────────────────────────────────────────────

@login_required
def get_dados_planejamento_embalagem_por_produto(request, produto_id):
    """API: dados de um produto para autopreencher o item do planejamento
    (unidade padrão, fornecedor correspondente e preço de compra)."""
    from produtos.models import Produto, ProdutoFornecedor

    try:
        produto = Produto.objects.select_related('unidade_medida').get(
            id=produto_id, categoria__empresa=request.user.empresa
        )
    except Produto.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Produto não encontrado'}, status=404)

    produto_fornecedor = ProdutoFornecedor.objects.filter(
        produto=produto, ativo=True,
        fornecedor__empresa=request.user.empresa, fornecedor__ativa=True,
    ).select_related('fornecedor').order_by('-fornecedor_preferencial', 'fornecedor__nome').first()

    if produto_fornecedor:
        fornecedor_id = produto_fornecedor.fornecedor_id
        fornecedor_nome = produto_fornecedor.fornecedor.nome
        preco_compra = produto_fornecedor.preco_compra
    else:
        fornecedor_id = None
        fornecedor_nome = None
        preco_compra = produto.preco_custo

    return JsonResponse({
        'success': True,
        'unidade_padrao_id': produto.unidade_medida.id,
        'unidade_padrao_nome': produto.unidade_medida.nome,
        'fornecedor_id': fornecedor_id,
        'fornecedor_nome': fornecedor_nome,
        'preco_compra': str(preco_compra) if preco_compra is not None else None,
    })
