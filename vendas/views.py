"""
Views do módulo Vendas — Pré-venda / Pedido de Venda
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal

from .models import PedidoVenda, ItemPedidoVenda
from .forms import PedidoVendaForm, ItemPedidoVendaFormSet


# ============================================
# LISTA DE PEDIDOS
# ============================================

@login_required
def pedido_list(request):
    empresa = request.user.empresa
    qs = PedidoVenda.objects.filter(empresa=empresa).select_related('cliente', 'vendedor')

    status_f = request.GET.get('status', '')
    tipo_f = request.GET.get('tipo', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_f:
        qs = qs.filter(status=status_f)
    if tipo_f:
        qs = qs.filter(tipo_venda=tipo_f)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(cliente__razao_social__icontains=q))
    if data_ini:
        qs = qs.filter(data_pedido__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_pedido__lte=data_fim)

    paginator = Paginator(qs.order_by('-criado_em'), 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'vendas/list.html', {
        'page_obj': page,
        'status_choices': PedidoVenda.STATUS_CHOICES,
        'tipo_choices': PedidoVenda.TIPO_VENDA_CHOICES,
        'filtros': {'status': status_f, 'tipo': tipo_f, 'q': q, 'data_ini': data_ini, 'data_fim': data_fim},
    })


# ============================================
# CRIAR PEDIDO
# ============================================

@login_required
def pedido_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = PedidoVendaForm(request.POST, empresa=empresa)
        formset = ItemPedidoVendaFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                pedido = form.save(commit=False)
                pedido.empresa = empresa
                pedido.numero = PedidoVenda._gerar_numero(empresa)
                pedido.criado_por = request.user
                pedido.save()
                formset.instance = pedido
                formset.save()
                pedido.calcular_total()
                pedido.save(update_fields=['valor_produtos', 'valor_total'])
            messages.success(request, f'Pedido {pedido.numero} criado.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)
    else:
        form = PedidoVendaForm(empresa=empresa)
        formset = ItemPedidoVendaFormSet(prefix='itens')
    return render(request, 'vendas/form.html', {
        'form': form, 'formset': formset, 'title': 'Novo Pedido de Venda',
    })


# ============================================
# DETALHE DO PEDIDO
# ============================================

@login_required
def pedido_detail(request, pk):
    empresa = request.user.empresa
    pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
    itens = pedido.itens.all()
    return render(request, 'vendas/detail.html', {'pedido': pedido, 'itens': itens})


# ============================================
# EDITAR PEDIDO
# ============================================

@login_required
def pedido_update(request, pk):
    empresa = request.user.empresa
    pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
    if pedido.status != 'RASCUNHO':
        messages.error(request, 'Apenas pedidos em RASCUNHO podem ser editados.')
        return redirect('vendas:pedido_detail', pk=pk)

    if request.method == 'POST':
        form = PedidoVendaForm(request.POST, instance=pedido, empresa=empresa)
        formset = ItemPedidoVendaFormSet(request.POST, instance=pedido, prefix='itens')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                p = form.save()
                formset.save()
                p.calcular_total()
                p.save(update_fields=['valor_produtos', 'valor_total'])
            messages.success(request, 'Pedido atualizado.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)
    else:
        form = PedidoVendaForm(instance=pedido, empresa=empresa)
        formset = ItemPedidoVendaFormSet(instance=pedido, prefix='itens')
    return render(request, 'vendas/form.html', {
        'form': form, 'formset': formset, 'title': 'Editar Pedido de Venda', 'pedido': pedido,
    })


# ============================================
# AÇÕES DE STATUS
# ============================================

@login_required
def pedido_aprovar(request, pk):
    if request.method == 'POST':
        empresa = request.user.empresa
        pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
        if pedido.status != 'RASCUNHO':
            messages.error(request, 'Apenas pedidos RASCUNHO podem ser aprovados.')
        else:
            pedido.status = 'APROVADO'
            pedido.save()
            messages.success(request, f'Pedido {pedido.numero} aprovado.')
    return redirect('vendas:pedido_detail', pk=pk)


@login_required
def pedido_emitir_documento(request, pk):
    """Emite NF-e ou Invoice + Conta a Receber e conclui o pedido."""
    if request.method != 'POST':
        return redirect('vendas:pedido_detail', pk=pk)

    empresa = request.user.empresa
    pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)

    if pedido.status not in ('APROVADO', 'CONFIRMADO'):
        messages.error(request, 'Pedido precisa estar APROVADO ou CONFIRMADO para emitir.')
        return redirect('vendas:pedido_detail', pk=pk)

    with transaction.atomic():
        # --- Gerar NF-e (Mercado Interno) ---
        if pedido.gerar_nota_fiscal and pedido.tipo_venda == 'MERCADO_INTERNO' and not pedido.nota_fiscal_id:
            from faturamento.models import NotaFiscal, ItemNotaFiscal, ConfiguracaoFiscal
            cfg = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
            from django.db.models import Max as _Max
            max_num = NotaFiscal.objects.filter(empresa=empresa).aggregate(m=_Max('numero'))['m'] or 0
            nf = NotaFiscal.objects.create(
                empresa=empresa,
                numero=max_num + 1,
                serie=cfg.serie_nfe if cfg else 1,
                natureza_operacao=pedido.natureza_operacao or (cfg.natureza_operacao_padrao if cfg else 'VENDA'),
                cliente=pedido.cliente,
                data_emissao=timezone.now().date(),
                cfop=cfg.cfop_venda_interna if cfg else '5102',
                status='RASCUNHO',
                modalidade_frete='SEM_FRETE',
                informacoes_complementares=pedido.observacoes_fiscais,
                criado_por=request.user,
                atualizado_por=request.user,
            )
            for item in pedido.itens.all():
                ItemNotaFiscal.objects.create(
                    nota_fiscal=nf,
                    numero_item=item.pk,
                    descricao=item.descricao,
                    produto=item.produto,
                    ncm=item.ncm or '00000000',
                    cfop=item.cfop or (cfg.cfop_venda_interna if cfg else '5102'),
                    cst_icms='00', cst_pis='01', cst_cofins='01',
                    unidade=item.unidade,
                    quantidade=item.quantidade,
                    valor_unitario=item.preco_unitario,
                    valor_total=item.preco_total,
                    valor_desconto=item.desconto_item,
                    aliquota_icms=Decimal('0.00'), valor_icms=Decimal('0.00'),
                    aliquota_ipi=Decimal('0.00'), valor_ipi=Decimal('0.00'),
                    aliquota_pis=Decimal('0.00'), valor_pis=Decimal('0.00'),
                    aliquota_cofins=Decimal('0.00'), valor_cofins=Decimal('0.00'),
                )
            nf.calcular_totais()
            nf.save()
            pedido.nota_fiscal = nf
            messages.info(request, f'NF-e {nf.numero} criada como rascunho.')

        # --- Gerar Invoice (Exportação) ---
        if pedido.gerar_nota_fiscal and pedido.tipo_venda == 'EXPORTACAO' and not pedido.invoice_id:
            from faturamento.models import InvoiceExportacao, ItemInvoice
            from faturamento.views import _gerar_numero_invoice
            inv = InvoiceExportacao.objects.create(
                empresa=empresa,
                numero=_gerar_numero_invoice(empresa),
                cliente=pedido.cliente,
                data_emissao=timezone.now().date(),
                incoterm='FOB',
                moeda=pedido.moeda,
                taxa_cambio=pedido.taxa_cambio,
                condicao_pagamento=pedido.condicao_pagamento,
                observacoes=pedido.observacoes,
                status='RASCUNHO',
                valor_mercadoria=pedido.valor_produtos,
                valor_frete=pedido.valor_frete,
                valor_seguro=Decimal('0.00'),
                valor_total=pedido.valor_total,
                criado_por=request.user,
                atualizado_por=request.user,
            )
            for item in pedido.itens.all():
                ItemInvoice.objects.create(
                    invoice=inv,
                    descricao=item.descricao,
                    quantidade=item.quantidade,
                    unidade=item.unidade,
                    peso_bruto_kg=Decimal('0.000'),
                    peso_liquido_kg=Decimal('0.000'),
                    valor_unitario_fob=item.preco_unitario,
                    marks_numbers='',
                )
            pedido.invoice = inv
            messages.info(request, f'Invoice {inv.numero} criada como rascunho.')

        # --- Gerar Conta a Receber ---
        if pedido.gerar_conta_receber and not pedido.conta_receber_id:
            from financeiro.models import ContaReceber, ParcelaContaReceber
            from financeiro.views import _gerar_numero_cr
            venc = pedido.data_entrega_prevista or timezone.now().date()
            valor_brl = (
                (pedido.valor_total * pedido.taxa_cambio)
                if pedido.taxa_cambio and pedido.moeda != 'BRL'
                else pedido.valor_total
            )
            cr = ContaReceber.objects.create(
                empresa=empresa,
                numero=_gerar_numero_cr(empresa),
                cliente=pedido.cliente,
                data_emissao=timezone.now().date(),
                data_vencimento=venc,
                status='ABERTA',
                origem='PEDIDO_VENDA',
                moeda=pedido.moeda,
                valor_moeda=pedido.valor_total,
                taxa_cambio=pedido.taxa_cambio,
                valor_brl=valor_brl,
                descricao=f'Pedido {pedido.numero} — {pedido.cliente.razao_social}',
                criado_por=request.user,
            )
            ParcelaContaReceber.objects.create(
                conta_receber=cr,
                numero_parcela=1,
                valor_parcela_moeda=pedido.valor_total,
                valor_parcela_brl=valor_brl,
                data_vencimento=venc,
            )
            pedido.conta_receber = cr
            messages.info(request, f'Conta a Receber {cr.numero} criada.')

        pedido.status = 'CONCLUIDO'
        pedido.save()
        messages.success(request, f'Pedido {pedido.numero} concluído.')

    return redirect('vendas:pedido_detail', pk=pk)


@login_required
def pedido_cancelar(request, pk):
    if request.method == 'POST':
        empresa = request.user.empresa
        pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
        if pedido.status == 'CONCLUIDO':
            messages.error(request, 'Pedidos concluídos não podem ser cancelados.')
        else:
            pedido.status = 'CANCELADO'
            pedido.save()
            messages.success(request, f'Pedido {pedido.numero} cancelado.')
    return redirect('vendas:pedido_detail', pk=pk)
