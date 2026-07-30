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

from .models import PedidoVenda, ItemPedidoVenda, TabelaPreco
from .forms import PedidoVendaForm, ItemPedidoVendaFormSet, TabelaPrecoForm
from produtos.tributacao import resolver_tributacao_venda


def _validar_e_aplicar_tributacoes(formset, empresa, cliente, tipo_venda):
    """Resolve a tributação de cada item do formset a partir do produto, do
    cliente e do tipo de venda — nunca confia em ncm/cfop vindos do POST,
    sempre re-deriva. Retorna uma mensagem de erro (nada é salvo nesse caso)
    ou None se todos os itens foram resolvidos com sucesso (já aplicados às
    instances, prontos para formset.save())."""
    for item_form in formset.forms:
        if item_form.cleaned_data.get('DELETE'):
            continue
        produto = item_form.cleaned_data.get('produto')
        if not produto:
            continue
        resultado = resolver_tributacao_venda(produto, empresa, cliente, tipo_venda)
        if not resultado.ok:
            return resultado.mensagem
        item_form.instance.tributacao = resultado.tributacao
        item_form.instance.ncm = resultado.ncm_codigo
        item_form.instance.cfop = resultado.cfop_codigo
    return None


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
            erro_tributacao = _validar_e_aplicar_tributacoes(
                formset, empresa, form.cleaned_data['cliente'], form.cleaned_data['tipo_venda'],
            )
            if erro_tributacao:
                messages.error(request, erro_tributacao)
            else:
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
            erro_tributacao = _validar_e_aplicar_tributacoes(
                formset, empresa, form.cleaned_data['cliente'], form.cleaned_data['tipo_venda'],
            )
            if erro_tributacao:
                messages.error(request, erro_tributacao)
            else:
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
def pedido_pdf(request, pk):
    """Gera um PDF de pré-visualização do pedido, para conferência antes de aprovar."""
    empresa = request.user.empresa
    pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
    itens = pedido.itens.all()

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('vendas/pedido_pdf.html')
    html = template.render({'pedido': pedido, 'itens': itens, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pedido.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


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
        # Se o pedido já está vinculado a um Romaneio de Venda que por sua vez já
        # gerou NF-e/Invoice (fluxo embalagem-primeiro), reaproveita esse documento
        # em vez de criar um segundo — evita faturar a mesma carga duas vezes.
        romaneio = getattr(pedido, 'romaneio_venda', None)

        # --- Gerar NF-e (Mercado Interno) ---
        if pedido.gerar_nota_fiscal and pedido.tipo_venda == 'MERCADO_INTERNO' and not pedido.nota_fiscal_id and romaneio and romaneio.nota_fiscal_id:
            pedido.nota_fiscal = romaneio.nota_fiscal
            messages.info(request, f'Romaneio {romaneio.numero} já possui NF-e {romaneio.nota_fiscal.numero} — reaproveitada.')
        elif pedido.gerar_nota_fiscal and pedido.tipo_venda == 'MERCADO_INTERNO' and not pedido.nota_fiscal_id:
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
                trib = item.tributacao
                if trib:
                    # Itens legados (criados antes desta tributação automática) não têm
                    # `tributacao` — caem no fallback zerado abaixo, como já era antes.
                    base_icms = item.preco_total * (trib.icms_base_calculo / Decimal('100')) * (Decimal('1') - trib.icms_reducao_base / Decimal('100'))
                    aliquota_icms, aliquota_ipi = trib.icms_aliquota, trib.ipi_aliquota
                    aliquota_pis, aliquota_cofins = trib.pis_aliquota, trib.cofins_aliquota
                    valor_icms = (base_icms * aliquota_icms / Decimal('100')).quantize(Decimal('0.01'))
                    valor_ipi = (item.preco_total * aliquota_ipi / Decimal('100')).quantize(Decimal('0.01'))
                    valor_pis = (item.preco_total * (trib.pis_base_calculo / Decimal('100')) * aliquota_pis / Decimal('100')).quantize(Decimal('0.01'))
                    valor_cofins = (item.preco_total * (trib.cofins_base_calculo / Decimal('100')) * aliquota_cofins / Decimal('100')).quantize(Decimal('0.01'))
                    cst_icms, cst_pis, cst_cofins = trib.icms_situacao_tributaria, trib.pis_situacao_tributaria, trib.cofins_situacao_tributaria
                else:
                    cst_icms, cst_pis, cst_cofins = '00', '01', '01'
                    aliquota_icms = aliquota_ipi = aliquota_pis = aliquota_cofins = Decimal('0.00')
                    valor_icms = valor_ipi = valor_pis = valor_cofins = Decimal('0.00')

                ItemNotaFiscal.objects.create(
                    nota_fiscal=nf,
                    numero_item=item.pk,
                    descricao=item.descricao,
                    produto=item.produto,
                    ncm=item.ncm or '00000000',
                    cfop=item.cfop or (cfg.cfop_venda_interna if cfg else '5102'),
                    cst_icms=cst_icms, cst_pis=cst_pis, cst_cofins=cst_cofins,
                    unidade=item.unidade,
                    quantidade=item.quantidade,
                    valor_unitario=item.preco_unitario,
                    valor_total=item.preco_total,
                    valor_desconto=item.desconto_item,
                    aliquota_icms=aliquota_icms, valor_icms=valor_icms,
                    aliquota_ipi=aliquota_ipi, valor_ipi=valor_ipi,
                    aliquota_pis=aliquota_pis, valor_pis=valor_pis,
                    aliquota_cofins=aliquota_cofins, valor_cofins=valor_cofins,
                )
            nf.calcular_totais()
            nf.save()
            pedido.nota_fiscal = nf
            messages.info(request, f'NF-e {nf.numero} criada como rascunho.')

        # --- Gerar Invoice (Exportação) ---
        if pedido.gerar_nota_fiscal and pedido.tipo_venda == 'EXPORTACAO' and not pedido.invoice_id and romaneio and romaneio.invoice_exportacao_id:
            pedido.invoice = romaneio.invoice_exportacao
            messages.info(request, f'Romaneio {romaneio.numero} já possui Invoice {romaneio.invoice_exportacao.numero} — reaproveitada.')
        elif pedido.gerar_nota_fiscal and pedido.tipo_venda == 'EXPORTACAO' and not pedido.invoice_id:
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
                banco_nome=empresa.banco_nome,
                banco_endereco=empresa.banco_endereco,
                banco_swift=empresa.banco_swift,
                banco_iban=empresa.banco_iban,
                banco_numero_conta=empresa.banco_numero_conta,
                banco_beneficiario_nome=empresa.banco_beneficiario_nome,
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

        pedido.status = 'CONFIRMADO'
        pedido.save()
        messages.success(
            request,
            f'Pedido {pedido.numero} confirmado. Ele será concluído automaticamente '
            'quando a NF-e/Invoice vinculada for emitida.'
        )

    return redirect('vendas:pedido_detail', pk=pk)


@login_required
def pedido_cancelar(request, pk):
    if request.method == 'POST':
        empresa = request.user.empresa
        pedido = get_object_or_404(PedidoVenda, pk=pk, empresa=empresa)
        if pedido.status == 'CONCLUIDO':
            messages.error(
                request,
                'Pedido com documento fiscal emitido não pode ser cancelado diretamente. '
                'Cancele/estorne a NF-e/Invoice primeiro.'
            )
        else:
            pedido.status = 'CANCELADO'
            pedido.save()
            messages.success(request, f'Pedido {pedido.numero} cancelado.')
    return redirect('vendas:pedido_detail', pk=pk)


# ============================================
# TABELA DE PREÇO
# ============================================

@login_required
def tabela_preco_list(request):
    empresa = request.user.empresa
    qs = TabelaPreco.objects.filter(empresa=empresa).select_related('cliente', 'produto', 'porto_destino')

    q = request.GET.get('q', '')
    ativo_f = request.GET.get('ativo', '')
    if q:
        qs = qs.filter(Q(produto__nome__icontains=q) | Q(cliente__razao_social__icontains=q))
    if ativo_f in ('1', '0'):
        qs = qs.filter(ativo=(ativo_f == '1'))

    paginator = Paginator(qs.order_by('-vigencia_inicio'), 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'vendas/tabela_preco/list.html', {
        'page_obj': page,
        'filtros': {'q': q, 'ativo': ativo_f},
    })


@login_required
def tabela_preco_detail(request, pk):
    empresa = request.user.empresa
    tabela = get_object_or_404(TabelaPreco, pk=pk, empresa=empresa)
    return render(request, 'vendas/tabela_preco/detail.html', {'tabela': tabela})


@login_required
def tabela_preco_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = TabelaPrecoForm(request.POST, empresa=empresa)
        if form.is_valid():
            tabela = form.save(commit=False)
            tabela.empresa = empresa
            tabela.criado_por = request.user
            tabela.save()
            messages.success(request, 'Tabela de preço criada.')
            return redirect('vendas:tabela_preco_detail', pk=tabela.pk)
    else:
        form = TabelaPrecoForm(empresa=empresa)
    return render(request, 'vendas/tabela_preco/form.html', {'form': form, 'title': 'Nova Tabela de Preço'})


@login_required
def tabela_preco_update(request, pk):
    empresa = request.user.empresa
    tabela = get_object_or_404(TabelaPreco, pk=pk, empresa=empresa)
    if request.method == 'POST':
        form = TabelaPrecoForm(request.POST, instance=tabela, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tabela de preço atualizada.')
            return redirect('vendas:tabela_preco_detail', pk=tabela.pk)
    else:
        form = TabelaPrecoForm(instance=tabela, empresa=empresa)
    return render(request, 'vendas/tabela_preco/form.html', {
        'form': form, 'title': 'Editar Tabela de Preço', 'tabela': tabela,
    })


@login_required
def tabela_preco_delete(request, pk):
    """Desativa (soft-delete) a tabela de preço — não remove fisicamente."""
    empresa = request.user.empresa
    tabela = get_object_or_404(TabelaPreco, pk=pk, empresa=empresa)
    if request.method == 'POST':
        tabela.ativo = False
        tabela.save(update_fields=['ativo'])
        messages.success(request, 'Tabela de preço desativada.')
        return redirect('vendas:tabela_preco_list')
    return render(request, 'vendas/tabela_preco/confirm_delete.html', {'tabela': tabela})
