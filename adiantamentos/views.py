from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    AdiantamentoInternacionalForm,
    AplicarDescontoForm,
    MigrarAdiantamentoForm,
    PularDescontoForm,
)
from .models import AdiantamentoInternacional, DescontoAdiantamento, MigracaoAdiantamento


# ---------------------------------------------------------------------------
# CRUD — AdiantamentoInternacional
# ---------------------------------------------------------------------------

@login_required
def adiantamento_list(request):
    empresa = request.user.empresa
    qs = AdiantamentoInternacional.objects.filter(empresa=empresa).select_related('cliente', 'safra')

    cliente_id = request.GET.get('cliente', '')
    safra_ref = request.GET.get('safra_referencia', '')
    status = request.GET.get('status', '')
    moeda = request.GET.get('moeda', '')

    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if safra_ref:
        qs = qs.filter(safra_referencia__icontains=safra_ref)
    if status:
        qs = qs.filter(status=status)
    if moeda:
        qs = qs.filter(moeda=moeda)

    from cadastros.models import Cliente
    clientes = Cliente.objects.filter(empresa=empresa, tipo_cliente='IMPORTADOR', status='ATIVO')

    stats = {
        'total': qs.count(),
        'ativos': qs.filter(status__in=['PENDENTE_EMBARQUE', 'EM_ANDAMENTO', 'PARCIALMENTE_QUITADO']).count(),
        'quitados': qs.filter(status='QUITADO').count(),
        'migrados': qs.filter(status='MIGRADO').count(),
    }

    return render(request, 'adiantamentos/adiantamento_list.html', {
        'adiantamentos': qs,
        'clientes': clientes,
        'filtros': {
            'cliente_id': cliente_id,
            'safra_referencia': safra_ref,
            'status': status,
            'moeda': moeda,
        },
        'status_choices': AdiantamentoInternacional.STATUS,
        'moeda_choices': AdiantamentoInternacional.MOEDA,
        'stats': stats,
    })


@login_required
def adiantamento_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = AdiantamentoInternacionalForm(request.POST, empresa=empresa)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.empresa = empresa
            obj.criado_por = request.user
            obj.save()
            messages.success(request, f'Adiantamento {obj.numero_referencia} criado com sucesso.')
            return redirect('adiantamentos:adiantamento_detail', pk=obj.pk)
    else:
        form = AdiantamentoInternacionalForm(empresa=empresa)

    return render(request, 'adiantamentos/adiantamento_form.html', {
        'form': form,
        'titulo': 'Novo Adiantamento Internacional',
    })


@login_required
def adiantamento_detail(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)
    descontos = adiantamento.descontos.select_related('invoice', 'aplicado_por').order_by('-data_desconto')

    pode_editar = adiantamento.status in ('PENDENTE_EMBARQUE', 'EM_ANDAMENTO', 'PARCIALMENTE_QUITADO')
    pode_aplicar = adiantamento.status in ('PENDENTE_EMBARQUE', 'EM_ANDAMENTO', 'PARCIALMENTE_QUITADO') and adiantamento.tem_saldo
    pode_migrar = adiantamento.status in ('EM_ANDAMENTO', 'PARCIALMENTE_QUITADO') and adiantamento.tem_saldo

    try:
        migracao_origem = adiantamento.migracao_origem
    except MigracaoAdiantamento.DoesNotExist:
        migracao_origem = None

    return render(request, 'adiantamentos/adiantamento_detail.html', {
        'adiantamento': adiantamento,
        'descontos': descontos,
        'pode_editar': pode_editar,
        'pode_aplicar': pode_aplicar,
        'pode_migrar': pode_migrar,
        'migracao_origem': migracao_origem,
        'migracoes_geradas': adiantamento.migracoes_geradas.select_related('adiantamento_destino'),
    })


@login_required
def adiantamento_edit(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    if adiantamento.status in ('QUITADO', 'MIGRADO', 'CANCELADO'):
        messages.error(request, 'Este adiantamento não pode mais ser editado.')
        return redirect('adiantamentos:adiantamento_detail', pk=pk)

    if request.method == 'POST':
        form = AdiantamentoInternacionalForm(request.POST, instance=adiantamento, empresa=empresa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Adiantamento atualizado com sucesso.')
            return redirect('adiantamentos:adiantamento_detail', pk=pk)
    else:
        form = AdiantamentoInternacionalForm(instance=adiantamento, empresa=empresa)

    return render(request, 'adiantamentos/adiantamento_form.html', {
        'form': form,
        'adiantamento': adiantamento,
        'titulo': f'Editar Adiantamento: {adiantamento.numero_referencia}',
    })


@login_required
def adiantamento_cancelar(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    if request.method == 'POST':
        tem_aplicados = adiantamento.descontos.filter(status='APLICADO').exists()
        if tem_aplicados:
            messages.error(request, 'Não é possível cancelar: existem descontos já aplicados em invoices.')
            return redirect('adiantamentos:adiantamento_detail', pk=pk)

        adiantamento.status = 'CANCELADO'
        adiantamento.save(update_fields=['status', 'atualizado_em'])
        messages.success(request, 'Adiantamento cancelado.')
        return redirect('adiantamentos:adiantamento_list')

    return render(request, 'adiantamentos/adiantamento_confirm_cancelar.html', {'adiantamento': adiantamento})


# ---------------------------------------------------------------------------
# Desconto
# ---------------------------------------------------------------------------

@login_required
def aplicar_desconto(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    if not adiantamento.tem_saldo:
        messages.warning(request, 'Este adiantamento já foi totalmente quitado.')
        return redirect('adiantamentos:adiantamento_detail', pk=pk)

    if request.method == 'POST':
        form = AplicarDescontoForm(request.POST, empresa=empresa)
        if form.is_valid():
            invoice = form.cleaned_data['invoice']
            valor = form.cleaned_data['valor_desconto_estrangeiro']
            taxa = form.cleaned_data['taxa_cambio_aplicada']

            if valor > adiantamento.saldo_estrangeiro:
                form.add_error('valor_desconto_estrangeiro',
                               f'Valor excede o saldo disponível de {adiantamento.moeda} {adiantamento.saldo_estrangeiro}.')
            else:
                with transaction.atomic():
                    DescontoAdiantamento.objects.create(
                        adiantamento=adiantamento,
                        invoice=invoice,
                        data_desconto=form.cleaned_data['data_desconto'],
                        valor_desconto_estrangeiro=valor,
                        taxa_cambio_aplicada=taxa,
                        status='APLICADO',
                        observacoes=form.cleaned_data.get('observacoes', ''),
                        aplicado_por=request.user,
                    )
                    # Atualiza o campo de desconto na invoice
                    invoice.valor_desconto_adiantamento = (invoice.valor_desconto_adiantamento or Decimal('0')) + valor
                    invoice.calcular_totais()

                    # Atualiza status do adiantamento
                    novo_total = adiantamento.total_descontado
                    if novo_total >= adiantamento.valor_estrangeiro:
                        adiantamento.status = 'QUITADO'
                    elif novo_total > 0:
                        adiantamento.status = 'PARCIALMENTE_QUITADO'
                    else:
                        adiantamento.status = 'EM_ANDAMENTO'
                    adiantamento.save(update_fields=['status', 'atualizado_em'])

                messages.success(
                    request,
                    f'Desconto de {adiantamento.moeda} {valor} aplicado na invoice {invoice.numero}.'
                )
                return redirect('adiantamentos:adiantamento_detail', pk=pk)
    else:
        # Pré-preencher valor sugerido
        sugerido = adiantamento.desconto_sugerido()
        taxa = adiantamento.taxa_cambio
        form = AplicarDescontoForm(
            empresa=empresa,
            initial={
                'valor_desconto_estrangeiro': sugerido,
                'taxa_cambio_aplicada': taxa,
                'data_desconto': timezone.now().date(),
            }
        )

    return render(request, 'adiantamentos/aplicar_desconto_form.html', {
        'form': form,
        'adiantamento': adiantamento,
    })


@login_required
def pular_desconto(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = PularDescontoForm(request.POST)
        if form.is_valid():
            DescontoAdiantamento.objects.create(
                adiantamento=adiantamento,
                invoice=None,
                data_desconto=form.cleaned_data['data_desconto'],
                valor_desconto_estrangeiro=Decimal('0'),
                taxa_cambio_aplicada=adiantamento.taxa_cambio,
                status='PULADO',
                motivo_pulo=form.cleaned_data['motivo_pulo'],
                aplicado_por=request.user,
            )
            if adiantamento.status == 'PENDENTE_EMBARQUE':
                adiantamento.status = 'EM_ANDAMENTO'
                adiantamento.save(update_fields=['status', 'atualizado_em'])

            messages.info(request, 'Desconto pulado para o próximo embarque.')
            return redirect('adiantamentos:adiantamento_detail', pk=pk)
    else:
        form = PularDescontoForm(initial={'data_desconto': timezone.now().date()})

    return render(request, 'adiantamentos/pular_desconto_form.html', {
        'form': form,
        'adiantamento': adiantamento,
    })


@login_required
def cancelar_desconto(request, desconto_pk):
    empresa = request.user.empresa
    desconto = get_object_or_404(
        DescontoAdiantamento,
        pk=desconto_pk,
        adiantamento__empresa=empresa,
    )
    adiantamento = desconto.adiantamento

    if request.method == 'POST':
        with transaction.atomic():
            if desconto.status == 'APLICADO' and desconto.invoice:
                invoice = desconto.invoice
                invoice.valor_desconto_adiantamento = max(
                    Decimal('0'),
                    (invoice.valor_desconto_adiantamento or Decimal('0')) - desconto.valor_desconto_estrangeiro
                )
                invoice.calcular_totais()

            desconto.status = 'CANCELADO'
            desconto.save(update_fields=['status'])

            # Recalcula status do adiantamento
            total = adiantamento.total_descontado
            if total <= 0:
                adiantamento.status = 'EM_ANDAMENTO'
            elif total < adiantamento.valor_estrangeiro:
                adiantamento.status = 'PARCIALMENTE_QUITADO'
            adiantamento.save(update_fields=['status', 'atualizado_em'])

        messages.success(request, 'Desconto cancelado e invoice atualizada.')
        return redirect('adiantamentos:adiantamento_detail', pk=adiantamento.pk)

    return render(request, 'adiantamentos/adiantamento_confirm_cancelar.html', {
        'adiantamento': adiantamento,
        'desconto': desconto,
        'modo': 'cancelar_desconto',
    })


# ---------------------------------------------------------------------------
# Migração
# ---------------------------------------------------------------------------

@login_required
def migrar_adiantamento(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    if adiantamento.status not in ('EM_ANDAMENTO', 'PARCIALMENTE_QUITADO') or not adiantamento.tem_saldo:
        messages.error(request, 'Este adiantamento não pode ser migrado.')
        return redirect('adiantamentos:adiantamento_detail', pk=pk)

    if request.method == 'POST':
        form = MigrarAdiantamentoForm(request.POST)
        if form.is_valid():
            saldo = adiantamento.saldo_estrangeiro
            safra_destino = form.cleaned_data['safra_referencia_destino']

            # Gera número de referência para o destino
            novo_ref = f'{adiantamento.numero_referencia}-MIG-{safra_destino}'

            with transaction.atomic():
                novo = AdiantamentoInternacional.objects.create(
                    empresa=empresa,
                    cliente=adiantamento.cliente,
                    safra_referencia=safra_destino,
                    numero_referencia=novo_ref,
                    data_adiantamento=form.cleaned_data['data_migracao'],
                    moeda=adiantamento.moeda,
                    valor_estrangeiro=saldo,
                    taxa_cambio=adiantamento.taxa_cambio,
                    tipo_regra_desconto=adiantamento.tipo_regra_desconto,
                    valor_desconto_padrao=adiantamento.valor_desconto_padrao,
                    percentual_desconto=adiantamento.percentual_desconto,
                    status='PENDENTE_EMBARQUE',
                    observacoes=f'Migrado de {adiantamento.numero_referencia}. {form.cleaned_data["motivo"]}',
                    adiantamento_origem=adiantamento,
                    criado_por=request.user,
                )
                MigracaoAdiantamento.objects.create(
                    adiantamento_origem=adiantamento,
                    adiantamento_destino=novo,
                    saldo_migrado_estrangeiro=saldo,
                    data_migracao=form.cleaned_data['data_migracao'],
                    motivo=form.cleaned_data['motivo'],
                    migrado_por=request.user,
                )
                adiantamento.status = 'MIGRADO'
                adiantamento.save(update_fields=['status', 'atualizado_em'])

            messages.success(request, f'Saldo de {adiantamento.moeda} {saldo} migrado para a safra {safra_destino}.')
            return redirect('adiantamentos:adiantamento_detail', pk=novo.pk)
    else:
        form = MigrarAdiantamentoForm(initial={'data_migracao': timezone.now().date()})

    return render(request, 'adiantamentos/migrar_adiantamento_form.html', {
        'form': form,
        'adiantamento': adiantamento,
    })


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

@login_required
def relatorio_adiantamentos(request):
    empresa = request.user.empresa
    qs = AdiantamentoInternacional.objects.filter(empresa=empresa).select_related('cliente')

    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    cliente_id = request.GET.get('cliente', '')
    safra_ref = request.GET.get('safra_referencia', '')
    status = request.GET.get('status', '')

    if data_inicio:
        qs = qs.filter(data_adiantamento__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data_adiantamento__lte=data_fim)
    if cliente_id:
        qs = qs.filter(cliente_id=cliente_id)
    if safra_ref:
        qs = qs.filter(safra_referencia__icontains=safra_ref)
    if status:
        qs = qs.filter(status=status)

    from cadastros.models import Cliente
    clientes = Cliente.objects.filter(empresa=empresa, tipo_cliente='IMPORTADOR', status='ATIVO')

    agg = qs.aggregate(
        total_usd=Sum('valor_estrangeiro', filter=Q(moeda='USD')),
        total_eur=Sum('valor_estrangeiro', filter=Q(moeda='EUR')),
        total_brl=Sum('valor_brl'),
    )

    return render(request, 'adiantamentos/relatorio_adiantamentos.html', {
        'adiantamentos': qs,
        'clientes': clientes,
        'filtros': {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'cliente_id': cliente_id,
            'safra_referencia': safra_ref,
            'status': status,
        },
        'status_choices': AdiantamentoInternacional.STATUS,
        'agg': {
            'total_usd': agg['total_usd'] or Decimal('0'),
            'total_eur': agg['total_eur'] or Decimal('0'),
            'total_brl': agg['total_brl'] or Decimal('0'),
        },
    })


# ---------------------------------------------------------------------------
# AJAX
# ---------------------------------------------------------------------------

@login_required
def ajax_adiantamentos_cliente(request, cliente_pk):
    empresa = request.user.empresa
    adiantamentos = AdiantamentoInternacional.objects.filter(
        empresa=empresa,
        cliente_id=cliente_pk,
        status__in=['PENDENTE_EMBARQUE', 'EM_ANDAMENTO', 'PARCIALMENTE_QUITADO'],
    )

    resultado = []
    for a in adiantamentos:
        resultado.append({
            'id': a.pk,
            'numero_referencia': a.numero_referencia,
            'moeda': a.moeda,
            'valor_estrangeiro': str(a.valor_estrangeiro),
            'saldo_estrangeiro': str(a.saldo_estrangeiro),
            'safra_referencia': a.safra_referencia,
            'taxa_cambio': str(a.taxa_cambio),
            'tipo_regra': a.tipo_regra_desconto,
            'valor_desconto_padrao': str(a.valor_desconto_padrao or 0),
            'percentual_desconto': str(a.percentual_desconto or 0),
        })

    return JsonResponse({'adiantamentos': resultado})


@login_required
def ajax_desconto_sugerido(request, pk):
    empresa = request.user.empresa
    adiantamento = get_object_or_404(AdiantamentoInternacional, pk=pk, empresa=empresa)

    valor_invoice_str = request.GET.get('valor_invoice', '0')
    try:
        valor_invoice = Decimal(valor_invoice_str)
    except Exception:
        valor_invoice = Decimal('0')

    sugerido = adiantamento.desconto_sugerido(valor_invoice=valor_invoice)

    return JsonResponse({
        'sugerido': str(sugerido),
        'saldo': str(adiantamento.saldo_estrangeiro),
        'moeda': adiantamento.moeda,
        'taxa_cambio': str(adiantamento.taxa_cambio),
    })
