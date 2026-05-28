from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import (
    CertificadoDigitalForm,
    ConfiguracaoFiscalForm,
    InvoiceExportacaoForm,
    ItemInvoiceFormSet,
    ItemNotaFiscalFormSet,
    ItemPackingListFormSet,
    NotaFiscalCancelarForm,
    NotaFiscalForm,
    PackingListForm,
)
from .models import (
    ConfiguracaoFiscal,
    InvoiceExportacao,
    ItemPackingList,
    NotaFiscal,
    PackingList,
)


def _get_empresa(request):
    return request.user.empresa


# ─────────────────────────── Dashboard ───────────────────────────

@login_required
def faturamento_dashboard(request):
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'Empresa não encontrada.')
        return redirect('dashboard:index')

    hoje = timezone.now().date()
    inicio_mes = hoje.replace(day=1)

    nf_stats = NotaFiscal.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidas=Count('id', filter=Q(status='EMITIDA')),
        canceladas=Count('id', filter=Q(status='CANCELADA')),
        valor_mes=Sum('valor_total', filter=Q(status='EMITIDA', data_emissao__gte=inicio_mes)),
    )

    invoice_stats = InvoiceExportacao.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidas=Count('id', filter=Q(status='EMITIDA')),
        valor_fob=Sum('valor_mercadoria', filter=Q(status='EMITIDA')),
    )

    pl_stats = PackingList.objects.filter(empresa=empresa).aggregate(
        total=Count('id'),
        emitidos=Count('id', filter=Q(status='EMITIDO')),
    )

    ultimas_nf = NotaFiscal.objects.filter(empresa=empresa).select_related('cliente').order_by('-criado_em')[:5]
    ultimas_invoice = InvoiceExportacao.objects.filter(empresa=empresa).select_related('cliente', 'booking').order_by('-criado_em')[:5]

    return render(request, 'faturamento/dashboard.html', {
        'nf_stats': nf_stats,
        'invoice_stats': invoice_stats,
        'pl_stats': pl_stats,
        'ultimas_nf': ultimas_nf,
        'ultimas_invoice': ultimas_invoice,
    })


# ─────────────────────────── Nota Fiscal ───────────────────────────

@login_required
def nota_fiscal_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = NotaFiscal.objects.filter(empresa=empresa).select_related('cliente')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
    if data_ini:
        qs = qs.filter(data_emissao__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao__lte=data_fim)

    qs = qs.order_by('-data_emissao', '-numero')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/nota_fiscal/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': NotaFiscal.STATUS,
    })


@login_required
def nota_fiscal_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = NotaFiscalForm(request.POST, empresa=empresa)
        formset = ItemNotaFiscalFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            nf = form.save(user=request.user)
            # Auto-numerar — respeita numero_nfe_inicial para migração de outro sistema
            if not nf.numero:
                ultimo = NotaFiscal.objects.filter(empresa=empresa).exclude(numero__isnull=True).order_by('-numero').first()
                if ultimo:
                    nf.numero = ultimo.numero + 1
                else:
                    cfg = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
                    nf.numero = cfg.numero_nfe_inicial if cfg else 1
            formset.instance = nf
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.numero_item = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            nf.calcular_totais()
            messages.success(request, f'NF {nf.numero}/{nf.serie} criada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=nf.pk)
    else:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        initial = {}
        if config:
            initial['natureza_operacao'] = config.natureza_operacao_padrao
            initial['cfop'] = config.cfop_venda_interna
            initial['informacoes_complementares'] = config.observacoes_padrao_nfe
        form = NotaFiscalForm(empresa=empresa, initial=initial)
        formset = ItemNotaFiscalFormSet(prefix='itens')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nova Nota Fiscal',
    })


@login_required
def nota_fiscal_detail(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    return render(request, 'faturamento/nota_fiscal/detail.html', {'nf': nf})


@login_required
def nota_fiscal_update(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status != 'RASCUNHO':
        messages.error(request, 'Apenas NF-e em RASCUNHO podem ser editadas.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if request.method == 'POST':
        form = NotaFiscalForm(request.POST, instance=nf, empresa=empresa)
        formset = ItemNotaFiscalFormSet(request.POST, instance=nf, prefix='itens')
        if form.is_valid() and formset.is_valid():
            form.save(user=request.user)
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.numero_item = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            nf.calcular_totais()
            messages.success(request, 'NF-e atualizada com sucesso.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = NotaFiscalForm(instance=nf, empresa=empresa)
        formset = ItemNotaFiscalFormSet(instance=nf, prefix='itens')

    return render(request, 'faturamento/nota_fiscal/form.html', {
        'form': form,
        'formset': formset,
        'nf': nf,
        'title': f'Editar NF {nf.numero}/{nf.serie}',
    })


@login_required
@require_POST
def nota_fiscal_emitir(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status != 'RASCUNHO':
        messages.error(request, 'Apenas NF-e em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if not nf.itens.exists():
        messages.error(request, 'Adicione pelo menos um item antes de emitir.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
    if not config or not config.token_integranotas:
        messages.error(request, 'Configure o token IntegraNota em Faturamento → Configuração Fiscal antes de emitir.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    try:
        client = IntegranNotasClient(config.token_integranotas, config.ambiente_nfe)
        data = client.emitir_nfe(nf)

        chave = data.get('chave', '')
        protocolo = data.get('protocolo', '')
        xml_b64 = data.get('xml', '')
        pdf_b64 = data.get('pdf', '')
        codigo = data.get('codigo')

        if codigo == 5023:
            # Queued — salva chave e aguarda webhook / polling
            nf.chave_acesso = chave
            nf.status = 'EMITIDA'
            nf.data_hora_emissao = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=['chave_acesso', 'status', 'data_hora_emissao', 'atualizado_por'])
            messages.info(request, f'NF {nf.numero}/{nf.serie} enviada à SEFAZ — aguardando autorização. Chave: {chave}')
        else:
            # Authorized immediately (codigo == 100)
            nf.chave_acesso = chave
            nf.protocolo_autorizacao = protocolo
            nf.xml_autorizacao = xml_b64
            nf.pdf_danfe = pdf_b64
            nf.status = 'EMITIDA'
            nf.data_hora_emissao = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=[
                'chave_acesso', 'protocolo_autorizacao', 'xml_autorizacao',
                'pdf_danfe', 'status', 'data_hora_emissao', 'atualizado_por',
            ])
            messages.success(request, f'NF {nf.numero}/{nf.serie} autorizada! Chave: {chave}')

    except IntegranNotasError as exc:
        erros = '; '.join(str(e) for e in exc.erros) if exc.erros else ''
        msg = f'Erro IntegraNota [{exc.codigo}]: {exc} {erros}'.strip()
        messages.error(request, msg)
    except Exception as exc:
        messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')

    return redirect('faturamento:nota_fiscal_detail', pk=pk)


@login_required
def nota_fiscal_cancelar(request, pk):
    from .services.integranotas import IntegranNotasClient, IntegranNotasError

    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    if nf.status == 'CANCELADA':
        messages.warning(request, 'NF-e já está cancelada.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)

    if request.method == 'POST':
        form = NotaFiscalCancelarForm(request.POST)
        if form.is_valid():
            justificativa = form.cleaned_data['justificativa']

            # Se NF tem chave, tenta cancelar na SEFAZ via IntegraNota
            if nf.chave_acesso:
                config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
                if not config or not config.token_integranotas:
                    messages.error(request, 'Configure o token IntegraNota para cancelar via SEFAZ.')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})
                try:
                    client = IntegranNotasClient(config.token_integranotas, config.ambiente_nfe)
                    client.cancelar_nfe(nf.chave_acesso, justificativa)
                except IntegranNotasError as exc:
                    messages.error(request, f'Erro ao cancelar na SEFAZ [{exc.codigo}]: {exc}')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})
                except Exception as exc:
                    messages.error(request, f'Falha na comunicação com IntegraNota: {exc}')
                    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})

            nf.status = 'CANCELADA'
            nf.motivo_cancelamento = justificativa
            nf.data_cancelamento = timezone.now()
            nf.atualizado_por = request.user
            nf.save(update_fields=['status', 'motivo_cancelamento', 'data_cancelamento', 'atualizado_por'])
            messages.success(request, f'NF {nf.numero}/{nf.serie} cancelada.')
            return redirect('faturamento:nota_fiscal_detail', pk=pk)
    else:
        form = NotaFiscalCancelarForm()

    return render(request, 'faturamento/nota_fiscal/cancelar_form.html', {'form': form, 'nf': nf})


@csrf_exempt
def integranotas_webhook(request):
    """Receives async status notifications from IntegraNota."""
    import json
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        payload = json.loads(request.body)
    except Exception:
        return HttpResponse(status=400)

    chave = payload.get('chave') or payload.get('chave_acesso', '')
    if not chave:
        return HttpResponse(status=200)

    try:
        nf = NotaFiscal.objects.get(chave_acesso=chave)
    except NotaFiscal.DoesNotExist:
        return HttpResponse(status=200)

    codigo = payload.get('codigo')
    if codigo == 100:
        nf.protocolo_autorizacao = payload.get('protocolo', nf.protocolo_autorizacao)
        nf.xml_autorizacao = payload.get('xml', nf.xml_autorizacao)
        nf.pdf_danfe = payload.get('pdf', nf.pdf_danfe)
        if not nf.data_hora_emissao:
            nf.data_hora_emissao = timezone.now()
        nf.status = 'EMITIDA'
        nf.save(update_fields=['protocolo_autorizacao', 'xml_autorizacao', 'pdf_danfe', 'data_hora_emissao', 'status'])
    elif codigo == 101:
        nf.status = 'CANCELADA'
        if not nf.data_cancelamento:
            nf.data_cancelamento = timezone.now()
        nf.save(update_fields=['status', 'data_cancelamento'])

    return HttpResponse(status=200)


@login_required
def nota_fiscal_danfe(request, pk):
    """Download the DANFE PDF returned by IntegraNota (base64 stored in pdf_danfe)."""
    import base64
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)
    if not nf.pdf_danfe:
        messages.error(request, 'DANFE não disponível — a NF-e ainda não foi autorizada pela SEFAZ.')
        return redirect('faturamento:nota_fiscal_detail', pk=pk)
    pdf_bytes = base64.b64decode(nf.pdf_danfe)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="DANFE_{nf.numero}_{nf.serie}.pdf"'
    return response


@login_required
def nota_fiscal_pdf(request, pk):
    empresa = _get_empresa(request)
    nf = get_object_or_404(NotaFiscal, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/nota_fiscal/pdf.html')
    html = template.render({'nf': nf, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="NF_{nf.numero}_{nf.serie}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Invoice de Exportação ───────────────────────────

@login_required
def invoice_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = InvoiceExportacao.objects.filter(empresa=empresa).select_related('cliente', 'booking')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(cliente__razao_social__icontains=q) | Q(numero__icontains=q))
    if data_ini:
        qs = qs.filter(data_emissao__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_emissao__lte=data_fim)

    qs = qs.order_by('-data_emissao')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/invoice/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'status_choices': InvoiceExportacao.STATUS,
    })


@login_required
def invoice_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    booking_id = request.GET.get('booking')
    initial = {}
    if booking_id:
        from exportacao.models import Booking
        try:
            b = Booking.objects.get(pk=booking_id, empresa=empresa)
            initial['booking'] = b
            if b.porto_origem:
                initial['porto_embarque'] = str(b.porto_origem)
            if b.porto_destino:
                initial['porto_destino'] = str(b.porto_destino)
            if b.data_embarque_previsto:
                initial['data_embarque_previsto'] = b.data_embarque_previsto
            if b.solicitacao and b.solicitacao.cliente:
                initial['cliente'] = b.solicitacao.cliente
        except Exception:
            pass

    if request.method == 'POST':
        form = InvoiceExportacaoForm(request.POST, empresa=empresa)
        formset = ItemInvoiceFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            invoice = form.save(user=request.user)
            invoice.numero = _gerar_numero_invoice(empresa)
            invoice.save(update_fields=['numero'])
            formset.instance = invoice
            formset.save()
            invoice.calcular_totais()
            messages.success(request, f'Invoice {invoice.numero} criada com sucesso.')
            return redirect('faturamento:invoice_detail', pk=invoice.pk)
    else:
        config = ConfiguracaoFiscal.objects.filter(empresa=empresa).first()
        if config and config.observacoes_padrao_invoice:
            initial.setdefault('observacoes', config.observacoes_padrao_invoice)
        form = InvoiceExportacaoForm(empresa=empresa, initial=initial)
        formset = ItemInvoiceFormSet(prefix='itens')

    return render(request, 'faturamento/invoice/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Nova Invoice de Exportação',
    })


def _gerar_numero_invoice(empresa):
    ano = timezone.now().year
    ultimo = InvoiceExportacao.objects.filter(
        empresa=empresa,
        numero__startswith=f'INV-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'INV-{ano}-{seq:04d}'


@login_required
def invoice_detail(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)
    return render(request, 'faturamento/invoice/detail.html', {'invoice': invoice})


@login_required
def invoice_update(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status != 'RASCUNHO':
        messages.error(request, 'Apenas invoices em RASCUNHO podem ser editadas.')
        return redirect('faturamento:invoice_detail', pk=pk)

    if request.method == 'POST':
        form = InvoiceExportacaoForm(request.POST, instance=invoice, empresa=empresa)
        formset = ItemInvoiceFormSet(request.POST, instance=invoice, prefix='itens')
        if form.is_valid() and formset.is_valid():
            form.save(user=request.user)
            formset.save()
            invoice.calcular_totais()
            messages.success(request, 'Invoice atualizada com sucesso.')
            return redirect('faturamento:invoice_detail', pk=pk)
    else:
        form = InvoiceExportacaoForm(instance=invoice, empresa=empresa)
        formset = ItemInvoiceFormSet(instance=invoice, prefix='itens')

    return render(request, 'faturamento/invoice/form.html', {
        'form': form,
        'formset': formset,
        'invoice': invoice,
        'title': f'Editar {invoice.numero}',
    })


@login_required
@require_POST
def invoice_emitir(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status != 'RASCUNHO':
        messages.error(request, 'Apenas invoices em RASCUNHO podem ser emitidas.')
        return redirect('faturamento:invoice_detail', pk=pk)

    if invoice.booking and invoice.booking.status != 'CONFIRMADO':
        messages.error(request, 'O booking vinculado precisa estar CONFIRMADO (RN-07).')
        return redirect('faturamento:invoice_detail', pk=pk)

    if not invoice.itens.exists():
        messages.error(request, 'Adicione pelo menos um item antes de emitir.')
        return redirect('faturamento:invoice_detail', pk=pk)

    invoice.status = 'EMITIDA'
    invoice.atualizado_por = request.user
    invoice.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{invoice.numero} emitida com sucesso.')
    return redirect('faturamento:invoice_detail', pk=pk)


@login_required
@require_POST
def invoice_cancelar(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    if invoice.status == 'CANCELADA':
        messages.warning(request, 'Invoice já está cancelada.')
        return redirect('faturamento:invoice_detail', pk=pk)

    invoice.status = 'CANCELADA'
    invoice.atualizado_por = request.user
    invoice.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{invoice.numero} cancelada.')
    return redirect('faturamento:invoice_detail', pk=pk)


@login_required
def invoice_pdf(request, pk):
    empresa = _get_empresa(request)
    invoice = get_object_or_404(InvoiceExportacao, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/invoice/pdf.html')
    html = template.render({'invoice': invoice, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Packing List ───────────────────────────

@login_required
def packing_list_list(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    qs = PackingList.objects.filter(empresa=empresa).select_related('invoice', 'invoice__cliente')

    status_filter = request.GET.get('status', '')
    q = request.GET.get('q', '')

    if status_filter:
        qs = qs.filter(status=status_filter)
    if q:
        qs = qs.filter(Q(numero__icontains=q) | Q(invoice__numero__icontains=q))

    qs = qs.order_by('-data_emissao')
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'faturamento/packing_list/list.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'q': q,
        'status_choices': PackingList.STATUS,
    })


@login_required
def packing_list_create(request):
    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    invoice_id = request.GET.get('invoice')
    initial = {}
    if invoice_id:
        try:
            inv = InvoiceExportacao.objects.get(pk=invoice_id, empresa=empresa)
            initial['invoice'] = inv
        except InvoiceExportacao.DoesNotExist:
            pass

    if request.method == 'POST':
        form = PackingListForm(request.POST, empresa=empresa)
        formset = ItemPackingListFormSet(request.POST, prefix='itens')
        if form.is_valid() and formset.is_valid():
            pl = form.save(user=request.user)
            pl.numero = _gerar_numero_pl(empresa)
            pl.save(update_fields=['numero'])
            formset.instance = pl
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.ordem = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, f'Packing List {pl.numero} criado com sucesso.')
            return redirect('faturamento:packing_list_detail', pk=pl.pk)
    else:
        form = PackingListForm(empresa=empresa, initial=initial)
        formset = ItemPackingListFormSet(prefix='itens')

    return render(request, 'faturamento/packing_list/form.html', {
        'form': form,
        'formset': formset,
        'title': 'Novo Packing List',
    })


def _gerar_numero_pl(empresa):
    ano = timezone.now().year
    ultimo = PackingList.objects.filter(
        empresa=empresa,
        numero__startswith=f'PL-{ano}-',
    ).order_by('-numero').first()
    if ultimo and ultimo.numero:
        try:
            seq = int(ultimo.numero.split('-')[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1
    return f'PL-{ano}-{seq:04d}'


@login_required
def packing_list_detail(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)
    return render(request, 'faturamento/packing_list/detail.html', {'pl': pl})


@login_required
def packing_list_update(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    if pl.status != 'RASCUNHO':
        messages.error(request, 'Apenas Packing Lists em RASCUNHO podem ser editados.')
        return redirect('faturamento:packing_list_detail', pk=pk)

    if request.method == 'POST':
        form = PackingListForm(request.POST, instance=pl, empresa=empresa)
        formset = ItemPackingListFormSet(request.POST, instance=pl, prefix='itens')
        if form.is_valid() and formset.is_valid():
            form.save(user=request.user)
            items = formset.save(commit=False)
            for idx, item in enumerate(items, start=1):
                item.ordem = idx
                item.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Packing List atualizado.')
            return redirect('faturamento:packing_list_detail', pk=pk)
    else:
        form = PackingListForm(instance=pl, empresa=empresa)
        formset = ItemPackingListFormSet(instance=pl, prefix='itens')

    return render(request, 'faturamento/packing_list/form.html', {
        'form': form,
        'formset': formset,
        'pl': pl,
        'title': f'Editar {pl.numero}',
    })


@login_required
@require_POST
def packing_list_emitir(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    if pl.status != 'RASCUNHO':
        messages.error(request, 'Apenas Packing Lists em RASCUNHO podem ser emitidos.')
        return redirect('faturamento:packing_list_detail', pk=pk)

    pl.status = 'EMITIDO'
    pl.atualizado_por = request.user
    pl.save(update_fields=['status', 'atualizado_por'])
    messages.success(request, f'{pl.numero} emitido com sucesso.')
    return redirect('faturamento:packing_list_detail', pk=pk)


@login_required
def packing_list_pdf(request, pk):
    empresa = _get_empresa(request)
    pl = get_object_or_404(PackingList, pk=pk, empresa=empresa)

    from django.template.loader import get_template
    from xhtml2pdf import pisa
    from django.http import HttpResponse
    import io

    template = get_template('faturamento/packing_list/pdf.html')
    html = template.render({'pl': pl, 'empresa': empresa})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), result)
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pl.numero}.pdf"'
        return response
    return HttpResponse('Erro ao gerar PDF', status=500)


# ─────────────────────────── Configuração Fiscal ───────────────────────────

@login_required
def configuracao_fiscal(request):
    from datetime import timedelta
    from empresas.forms import EmpresaFiscalForm

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)

    if request.method == 'POST':
        form = ConfiguracaoFiscalForm(request.POST, instance=config)
        empresa_form = EmpresaFiscalForm(request.POST, instance=empresa)
        if form.is_valid() and empresa_form.is_valid():
            form.save()
            empresa_form.save()
            messages.success(request, 'Configuração fiscal salva com sucesso.')
            return redirect('faturamento:configuracao')
    else:
        form = ConfiguracaoFiscalForm(instance=config)
        empresa_form = EmpresaFiscalForm(instance=empresa)

    today = timezone.now().date()
    cert_expirado = config.certificado_validade and config.certificado_validade < today
    cert_expira_breve = (
        config.certificado_validade
        and not cert_expirado
        and config.certificado_validade <= today + timedelta(days=30)
    )

    return render(request, 'faturamento/configuracao.html', {
        'form': form,
        'config': config,
        'empresa_form': empresa_form,
        'cert_form': CertificadoDigitalForm(),
        'cert_expirado': cert_expirado,
        'cert_expira_breve': cert_expira_breve,
    })


@login_required
@require_POST
def certificado_upload(request):
    from .services.integranotas import parse_pfx

    empresa = _get_empresa(request)
    if not empresa:
        return redirect('dashboard:index')

    config, _ = ConfiguracaoFiscal.objects.get_or_create(empresa=empresa)
    form = CertificadoDigitalForm(request.POST, request.FILES)

    if form.is_valid():
        arquivo = form.cleaned_data['arquivo_pfx']
        senha = form.cleaned_data['senha_certificado']
        pfx_bytes = arquivo.read()
        try:
            info = parse_pfx(pfx_bytes, senha)
            config.certificado_pfx = pfx_bytes
            config.senha_certificado = senha
            config.certificado_validade = info['validade']
            config.certificado_cnpj = info['cnpj']
            config.certificado_arquivo_nome = arquivo.name
            config.save()
            messages.success(
                request,
                f'Certificado "{arquivo.name}" importado. '
                f'Válido até {info["validade"].strftime("%d/%m/%Y")}.'
            )
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'Erro inesperado ao processar certificado: {exc}')
    else:
        for field_errors in form.errors.values():
            for error in field_errors:
                messages.error(request, error)

    return redirect('faturamento:configuracao')


# ─────────────────────────── AJAX ───────────────────────────

@login_required
def ajax_produto_detail(request, pk):
    empresa = _get_empresa(request)
    from produtos.models import Produto
    try:
        produto = Produto.objects.select_related('ncm', 'unidade_venda').get(pk=pk, categoria__empresa=empresa)
    except Produto.DoesNotExist:
        return JsonResponse({'erro': 'Produto não encontrado'}, status=404)

    tributacoes = []
    for t in produto.tributacoes.select_related('cfop').all():
        tributacoes.append({
            'cfop': t.cfop.codigo,
            'cst_icms': t.icms_situacao_tributaria,
            'cst_pis': t.pis_situacao_tributaria,
            'cst_cofins': t.cofins_situacao_tributaria,
            'aliquota_icms': float(t.icms_aliquota),
            'aliquota_ipi': float(t.ipi_aliquota),
            'ipi_codigo_enquadramento': t.ipi_codigo_enquadramento or '999',
            'aliquota_pis': float(t.pis_aliquota),
            'aliquota_cofins': float(t.cofins_aliquota),
        })

    return JsonResponse({
        'nome': produto.nome,
        'ncm': produto.ncm.codigo if produto.ncm_id else '',
        'cest': produto.cest or '',
        'origem_mercadoria': produto.origem_mercadoria or '0',
        'unidade': produto.unidade_venda.sigla if produto.unidade_venda_id else '',
        'preco_venda': float(produto.preco_venda),
        'tributacoes': tributacoes,
    })


@login_required
def ajax_booking_preview(request, pk):
    empresa = _get_empresa(request)
    from exportacao.models import Booking
    try:
        b = Booking.objects.get(pk=pk, empresa=empresa)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'Não encontrado'}, status=404)

    cliente_id = None
    cliente_nome = ''
    if b.solicitacao and b.solicitacao.cliente:
        cliente_id = b.solicitacao.cliente.pk
        cliente_nome = str(b.solicitacao.cliente)

    containers = list(b.containers.values('id', 'numero_container', 'tipo_container'))

    return JsonResponse({
        'porto_embarque': str(b.porto_origem) if b.porto_origem else '',
        'porto_destino': str(b.porto_destino) if b.porto_destino else '',
        'data_embarque_previsto': str(b.data_embarque_previsto) if b.data_embarque_previsto else '',
        'valor_fob': str(b.valor_fob) if b.valor_fob else '',
        'cliente_id': cliente_id,
        'cliente_nome': cliente_nome,
        'containers': containers,
    })


@login_required
def ajax_cotacao_bcb(request):
    """
    Retorna cotações PTAX do BCB para o último dia útil anterior.
    Usado nos formulários de Invoice, Pedido de Venda e Conta a Receber
    para pré-preencher a taxa de câmbio.

    Query params opcionais:
        moedas — lista separada por vírgula (ex: USD,EUR,GBP). Padrão: USD,EUR,GBP
        data   — data de referência ISO (ex: 2026-05-20). Padrão: hoje
    """
    from .bcb import buscar_cotacoes
    from datetime import date

    moedas_param = request.GET.get('moedas', 'USD,EUR,GBP')
    moedas = [m.strip().upper() for m in moedas_param.split(',') if m.strip()]

    data_ref = None
    data_param = request.GET.get('data', '')
    if data_param:
        try:
            data_ref = date.fromisoformat(data_param)
        except ValueError:
            pass

    try:
        resultado = buscar_cotacoes(moedas=moedas, referencia=data_ref)
    except RuntimeError as e:
        return JsonResponse({'erro': str(e)}, status=503)
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao consultar o BCB: {e}'}, status=503)

    cotacoes_json = {}
    for moeda, dados in resultado['cotacoes'].items():
        cotacoes_json[moeda] = {
            'compra': float(dados['compra']),
            'venda': float(dados['venda']),
            'dataHora': dados.get('dataHora', ''),
        }

    return JsonResponse({
        'data': resultado['data'],
        'data_iso': resultado['data_iso'],
        'cotacoes': cotacoes_json,
    })
