"""
Views para o módulo financeiro
Funcionalidades de contas a pagar, parcelas, pagamentos, ajustes
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, F, Sum, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from .models import (
    ContaPagar, ParcelaContaPagar, PagamentoContaPagar, AjusteContaPagar, FormaPagemento,
    ContaReceber, ParcelaContaReceber, RecebimentoContaReceber,
)
from .forms import (
    ContaPageForm,
    ParcelaContaPageForm,
    ParcelaContaPageFormSet,
    PagamentoContaPageForm,
    AjusteContaPageForm,
    ContaReceberForm,
    ParcelaContaReceberFormSet,
    RecebimentoContaReceberForm,
)


def _gerar_parcelas_automaticas(conta, quantidade_parcelas, intervalo_dias, primeira_data_vencimento):
    """Cria parcelas sequenciais com vencimento incremental a partir do cadastro."""
    valor_total = conta.valor_ajustado or conta.valor_total
    valor_base = (valor_total / quantidade_parcelas).quantize(Decimal('0.01'))
    valor_acumulado = Decimal('0.00')

    for numero_parcela in range(1, quantidade_parcelas + 1):
        if numero_parcela == quantidade_parcelas:
            valor_parcela = valor_total - valor_acumulado
        else:
            valor_parcela = valor_base

        data_vencimento = primeira_data_vencimento + timedelta(days=intervalo_dias * (numero_parcela - 1))

        ParcelaContaPagar.objects.create(
            conta_pagar=conta,
            numero_parcela=numero_parcela,
            valor_parcela=valor_parcela,
            valor_total_parcela=valor_parcela,
            data_vencimento=data_vencimento,
            status='ABERTA',
        )
        valor_acumulado += valor_parcela


# ============================================
# VIEWS - DASHBOARD
# ============================================

@login_required
def financeiro_dashboard(request):
    """Dashboard do módulo financeiro com resumos e alertas"""
    empresa = request.user.empresa
    
    hoje = timezone.now().date()
    proximos_7_dias = hoje + timedelta(days=7)
    proximos_30_dias = hoje + timedelta(days=30)
    
    # Contas
    total_contas = ContaPagar.objects.filter(empresa=empresa).count()
    contas_abertas = ContaPagar.objects.filter(empresa=empresa, status='ABERTA').count()
    contas_aprovadas = ContaPagar.objects.filter(empresa=empresa, status='APROVADA').count()
    contas_pagas = ContaPagar.objects.filter(empresa=empresa, status='PAGA').count()
    
    # Valores
    valor_total = ContaPagar.objects.filter(empresa=empresa).aggregate(Sum('valor_total'))['valor_total__sum'] or Decimal('0.00')
    valor_ajustado = ContaPagar.objects.filter(empresa=empresa).aggregate(Sum('valor_ajustado'))['valor_ajustado__sum'] or Decimal('0.00')
    juros_acumulados = ContaPagar.objects.filter(empresa=empresa).aggregate(Sum('juros_acumulados'))['juros_acumulados__sum'] or Decimal('0.00')
    multa_acumulada = ContaPagar.objects.filter(empresa=empresa).aggregate(Sum('multa_acumulada'))['multa_acumulada__sum'] or Decimal('0.00')
    
    # Parcelas
    parcelas_vencidas = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__lt=hoje,
        status__in=['ABERTA', 'VENCIDA']
    )
    
    parcelas_vencidas_count = parcelas_vencidas.count()
    valor_vencido = parcelas_vencidas.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    
    parcelas_proximas = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=hoje,
        data_vencimento__lte=proximos_7_dias,
        status='ABERTA'
    )
    
    parcelas_proximas_count = parcelas_proximas.count()
    valor_proximo = parcelas_proximas.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    
    # Próximos 30 dias
    parcelas_30dias = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=hoje,
        data_vencimento__lte=proximos_30_dias,
        status='ABERTA'
    )
    valor_30dias = parcelas_30dias.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    
    # Pagamentos
    pagamentos_mes = PagamentoContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_pagamento__gte=datetime(hoje.year, hoje.month, 1).date(),
        data_pagamento__lte=hoje
    )
    
    total_pago_mes = pagamentos_mes.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')
    
    # Juros + Multas total
    juros_e_multas = juros_acumulados + multa_acumulada
    
    # Top fornecedores (por valor)
    top_fornecedores = ContaPagar.objects.filter(
        empresa=empresa
    ).values('fornecedor__nome').annotate(
        total=Sum('valor_total'),
        contas_count=Count('id')
    ).order_by('-total')[:5]

    # Últimas contas
    ultimas_contas = ContaPagar.objects.filter(empresa=empresa).order_by('-data_criacao')[:5]

    # ── Contas a Receber ──
    cr_abertas_qs = ContaReceber.objects.filter(
        empresa=empresa, status__in=['ABERTA', 'VENCIDA']
    )
    cr_abertas_count = cr_abertas_qs.count()
    valor_a_receber = cr_abertas_qs.aggregate(
        total=Sum('valor_brl')
    )['total'] or Decimal('0.00')
    cr_recebimentos_mes = RecebimentoContaReceber.objects.filter(
        conta_receber__empresa=empresa,
        data_pagamento__gte=datetime(hoje.year, hoje.month, 1).date(),
        data_pagamento__lte=hoje,
    ).aggregate(total=Sum('valor_recebido_brl'))['total'] or Decimal('0.00')

    posicao_liquida = valor_a_receber - valor_vencido

    context = {
        'stats': {
            'total_contas': total_contas,
            'contas_abertas': contas_abertas,
            'contas_aprovadas': contas_aprovadas,
            'contas_pagas': contas_pagas,
        },
        'valores': {
            'total': valor_total,
            'ajustado': valor_ajustado,
            'juros': juros_acumulados,
            'multa': multa_acumulada,
        },
        'juros_e_multas': juros_e_multas,
        'alertas': {
            'parcelas_vencidas_count': parcelas_vencidas_count,
            'valor_vencido': valor_vencido,
            'parcelas_proximas_count': parcelas_proximas_count,
            'valor_proximo': valor_proximo,
        },
        'fluxo': {
            'valor_vencer_30d': valor_30dias,
            'total_pago_mes': total_pago_mes,
        },
        'top_fornecedores': top_fornecedores,
        'ultimas_contas': ultimas_contas,
        'parcelas_vencidas': parcelas_vencidas[:10],
        'parcelas_proximas': parcelas_proximas[:10],
        # CR
        'cr_abertas_count': cr_abertas_count,
        'valor_a_receber': valor_a_receber,
        'cr_recebimentos_mes': cr_recebimentos_mes,
        'posicao_liquida': posicao_liquida,
    }

    return render(request, 'financeiro/dashboard.html', context)


# ============================================
# VIEWS - CONTA A PAGAR
# ============================================

@login_required
def conta_pagar_list(request):
    """Listagem de contas a pagar com filtros"""
    empresa = request.user.empresa
    
    # Base query
    contas = ContaPagar.objects.filter(empresa=empresa).select_related(
        'fornecedor'
    ).prefetch_related('pagamentos').annotate(
        total_parcelas=Count('parcelas', distinct=True),
        parcelas_pagas=Count('parcelas', filter=Q(parcelas__status='PAGA'), distinct=True),
    )
    
    # Filtros
    status = request.GET.get('status', '')
    fornecedor = request.GET.get('fornecedor', '')
    periodo = request.GET.get('periodo', 'todos')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status:
        contas = contas.filter(status=status)

    if fornecedor:
        contas = contas.filter(fornecedor__nome__icontains=fornecedor)

    # Filtro de data de emissão (intervalo livre — campo data_ini/data_fim)
    if data_ini:
        try:
            contas = contas.filter(data_emissao__gte=datetime.strptime(data_ini, '%Y-%m-%d').date())
        except ValueError:
            pass
    if data_fim:
        try:
            contas = contas.filter(data_emissao__lte=datetime.strptime(data_fim, '%Y-%m-%d').date())
        except ValueError:
            pass

    # Filtro por período (vencimento de parcelas)
    hoje = timezone.now().date()

    # Semana ISO 8601: param ?semana_iso=YYYY-Www (ex: 2025-W26)
    # Um ano tem 52 ou 53 semanas. date.fromisocalendar(year, week, 1) retorna a
    # segunda-feira exata da semana — correto independente de virada de ano.
    semana_iso_str = request.GET.get('semana_iso', '')
    if semana_iso_str:
        try:
            # Formato esperado: "2025-W26"
            partes = semana_iso_str.split('-W')
            iso_year, iso_week = int(partes[0]), int(partes[1])
            import datetime as _dt
            inicio_semana = _dt.date.fromisocalendar(iso_year, iso_week, 1)
        except (ValueError, IndexError, AttributeError):
            inicio_semana = hoje - timedelta(days=hoje.weekday())
    else:
        inicio_semana = hoje - timedelta(days=hoje.weekday())

    fim_semana = inicio_semana + timedelta(days=6)

    # Calcula o valor ISO para as semanas anterior e próxima
    _prev = inicio_semana - timedelta(days=7)
    _next = inicio_semana + timedelta(days=7)
    iso_semana_atual = f"{inicio_semana.isocalendar()[0]}-W{inicio_semana.isocalendar()[1]:02d}"
    iso_semana_anterior = f"{_prev.isocalendar()[0]}-W{_prev.isocalendar()[1]:02d}"
    iso_semana_proxima = f"{_next.isocalendar()[0]}-W{_next.isocalendar()[1]:02d}"
    num_semana_ano = inicio_semana.isocalendar()[1]   # 1‥52/53
    ano_semana = inicio_semana.isocalendar()[0]

    if periodo == 'semana':
        contas = contas.filter(
            parcelas__data_vencimento__gte=inicio_semana,
            parcelas__data_vencimento__lte=fim_semana,
        ).distinct()
    elif periodo == '30dias':
        contas = contas.filter(
            parcelas__data_vencimento__gte=hoje,
            parcelas__data_vencimento__lte=hoje + timedelta(days=30)
        ).distinct()
    elif periodo == 'vencidas':
        contas = contas.filter(
            parcelas__data_vencimento__lt=hoje,
            parcelas__status='ABERTA'
        ).distinct()
    elif periodo == 'proximas':
        contas = contas.filter(
            parcelas__data_vencimento__gte=hoje,
            parcelas__status='ABERTA'
        ).distinct()

    # Ordenação
    order_by = request.GET.get('order_by', '-data_emissao')
    contas = contas.order_by(order_by)

    # Paginação
    paginator = Paginator(contas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Estatísticas
    stats = {
        'total': ContaPagar.objects.filter(empresa=empresa).count(),
        'abertas': ContaPagar.objects.filter(empresa=empresa, status='ABERTA').count(),
        'aprovadas': ContaPagar.objects.filter(empresa=empresa, status='APROVADA').count(),
        'pagas': ContaPagar.objects.filter(empresa=empresa, status='PAGA').count(),
        'valor_total': ContaPagar.objects.filter(empresa=empresa).aggregate(Sum('valor_total'))['valor_total__sum'] or Decimal('0.00'),
    }

    n_vencidas = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__lt=hoje,
        status__in=['ABERTA', 'VENCIDA'],
    ).count()

    n_semana = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=inicio_semana,
        data_vencimento__lte=fim_semana,
        status='ABERTA',
    ).count()

    context = {
        'page_obj': page_obj,
        'contas': page_obj.object_list,
        'stats': stats,
        'status_filter': status,
        'fornecedor_filter': fornecedor,
        'periodo_filter': periodo,
        'periodo': periodo,
        'data_ini': data_ini,
        'data_fim': data_fim,
        'n_vencidas': n_vencidas,
        'n_semana': n_semana,
        'inicio_semana': inicio_semana,
        'fim_semana': fim_semana,
        'semana_iso': iso_semana_atual,
        'semana_anterior': iso_semana_anterior,
        'semana_proxima': iso_semana_proxima,
        'num_semana_ano': num_semana_ano,
        'ano_semana': ano_semana,
    }

    return render(request, 'financeiro/conta_pagar_list.html', context)


@login_required
def conta_pagar_detail(request, pk):
    """Detalhe de uma conta a pagar com parcelas, pagamentos e ajustes"""
    empresa = request.user.empresa
    conta = get_object_or_404(
        ContaPagar.objects.select_related('recebimento__pedido', 'fornecedor'),
        pk=pk, empresa=empresa
    )

    parcelas = conta.parcelas.all().order_by('numero_parcela')
    pagamentos = conta.pagamentos.select_related('parcela', 'pago_por').order_by('-data_pagamento')
    ajustes = conta.ajustes.all().order_by('-data_criacao')

    # Logs de auditoria
    from .models import LogAlteracaoPagamento
    logs_auditoria = LogAlteracaoPagamento.objects.filter(
        pagamento__conta_pagar=conta
    ).select_related('usuario', 'pagamento').order_by('-data_hora')

    # Totais — apenas pagamentos compensados
    total_pago = pagamentos.filter(status='COMPENSADO').aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')
    saldo_devedor = conta.valor_ajustado - total_pago

    # Progresso de pagamento para exibição
    total_parcelas = parcelas.count()
    parcelas_pagas = parcelas.filter(status='PAGA').count()

    # Fallback: se o FK recebimento não estiver setado, tenta encontrar pelo número da NF
    recebimento_ref = conta.recebimento
    if recebimento_ref is None and conta.numero.startswith('NF-'):
        from compras.models import RecebimentoCompra
        nf_num = conta.numero[3:]
        recebimento_ref = RecebimentoCompra.objects.filter(
            nota_fiscal=nf_num, empresa=empresa
        ).first()

    context = {
        'conta': conta,
        'parcelas': parcelas,
        'pagamentos': pagamentos,
        'ajustes': ajustes,
        'logs_auditoria': logs_auditoria,
        'total_pago': total_pago,
        'saldo_devedor': saldo_devedor,
        'total_parcelas': total_parcelas,
        'parcelas_pagas': parcelas_pagas,
        'recebimento_ref': recebimento_ref,
    }

    return render(request, 'financeiro/conta_pagar_detail.html', context)


@login_required
def pagamento_retornar_pendente(request, pk):
    """Reverte um pagamento para PENDENTE com confirmação de senha e registro de auditoria."""
    from .models import LogAlteracaoPagamento, PagamentoContaPagar
    from django.contrib.auth.hashers import check_password

    pagamento = get_object_or_404(
        PagamentoContaPagar,
        pk=pk,
        conta_pagar__empresa=request.user.empresa
    )

    if request.method != 'POST':
        return redirect('financeiro:conta_pagar_detail', pk=pagamento.conta_pagar.pk)

    senha = request.POST.get('senha', '')
    observacao = request.POST.get('observacao', '').strip()

    if not request.user.check_password(senha):
        messages.error(request, 'Senha incorreta. Operação não autorizada.')
        return redirect('financeiro:conta_pagar_detail', pk=pagamento.conta_pagar.pk)

    status_anterior = pagamento.status

    LogAlteracaoPagamento.objects.create(
        pagamento=pagamento,
        usuario=request.user,
        acao='RETORNO_PENDENTE',
        status_anterior=status_anterior,
        status_novo='PENDENTE',
        dados_anteriores={
            'status': status_anterior,
            'valor_pago': str(pagamento.valor_pago),
            'data_pagamento': str(pagamento.data_pagamento),
            'forma_pagamento': pagamento.forma_pagamento,
            'numero_documento': pagamento.numero_documento,
        },
        observacao=observacao,
        ip=request.META.get('REMOTE_ADDR'),
    )

    pagamento.status = 'CANCELADO'
    pagamento.save(update_fields=['status'])

    # Retorna a parcela para ABERTA se ela estava PAGA
    parcela = pagamento.parcela
    if parcela.status == 'PAGA':
        parcela.status = 'ABERTA'
        parcela.save(update_fields=['status'])

    # Se a conta estava PAGA, volta para APROVADA
    conta = pagamento.conta_pagar
    if conta.status == 'PAGA':
        conta.status = 'APROVADA'
        conta.save(update_fields=['status'])

    messages.success(request, f'Pagamento retornado ao status Pendente. Alteração registrada no histórico.')
    return redirect('financeiro:conta_pagar_detail', pk=pagamento.conta_pagar.pk)


@login_required
def ajuste_criar(request, pk):
    """Cria um ajuste (desconto ou acréscimo) na conta a pagar e atualiza valor_ajustado."""
    conta = get_object_or_404(ContaPagar, pk=pk, empresa=request.user.empresa)

    if request.method != 'POST':
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    senha = request.POST.get('senha', '')
    if not request.user.check_password(senha):
        messages.error(request, 'Senha incorreta. Ajuste não aplicado.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    tipo = request.POST.get('tipo', '')
    motivo = request.POST.get('motivo', '').strip()
    observacao = request.POST.get('observacao', '').strip()

    try:
        valor_input = Decimal(request.POST.get('valor', '0').replace(',', '.'))
    except Exception:
        messages.error(request, 'Valor inválido.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    if valor_input <= 0:
        messages.error(request, 'O valor do ajuste deve ser maior que zero.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    if not motivo:
        messages.error(request, 'O motivo é obrigatório.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    TIPOS_VALIDOS = [t[0] for t in AjusteContaPagar.TIPO_AJUSTE_CHOICES]
    if tipo not in TIPOS_VALIDOS:
        messages.error(request, 'Tipo de ajuste inválido.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    # Descontos reduzem o valor ajustado; acréscimos aumentam
    TIPOS_DESCONTO = {'DESCONTO_DIVERGENCIA', 'DESCONTO_NEGOCIADO'}
    operacao = request.POST.get('operacao', 'desconto')
    if tipo in TIPOS_DESCONTO:
        valor_ajuste = -valor_input
    elif tipo in {'ACRESCIMO_JUROS', 'ACRESCIMO_MULTA'}:
        valor_ajuste = valor_input
    else:
        valor_ajuste = -valor_input if operacao == 'desconto' else valor_input

    with transaction.atomic():
        AjusteContaPagar.objects.create(
            conta_pagar=conta,
            tipo=tipo,
            valor_ajuste=valor_ajuste,
            motivo=motivo,
            aprovado=True,
            aprovado_por=request.user,
            observacao=observacao,
        )
        conta.valor_ajustado = max(Decimal('0.00'), conta.valor_ajustado + valor_ajuste)
        conta.save(update_fields=['valor_ajustado'])

    sinal = 'Desconto' if valor_ajuste < 0 else 'Acréscimo'
    messages.success(request, f'{sinal} de R$ {valor_input:,.2f} aplicado com sucesso.')
    return redirect('financeiro:conta_pagar_detail', pk=pk)


@login_required
def conta_quitar_saldo(request, pk):
    """
    Quita o saldo residual de uma conta a pagar criando um ajuste de desconto.
    Só permitido quando 0 < saldo <= R$ 50,00.
    """
    conta = get_object_or_404(ContaPagar, pk=pk, empresa=request.user.empresa)

    if request.method != 'POST':
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    TOLERANCIA = Decimal('50.00')

    total_pago = conta.pagamentos.filter(status='COMPENSADO').aggregate(
        Sum('valor_pago')
    )['valor_pago__sum'] or Decimal('0.00')
    saldo = conta.valor_ajustado - total_pago

    if saldo <= 0:
        messages.error(request, 'Não há saldo devedor para quitar.')
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    if saldo > TOLERANCIA:
        messages.error(
            request,
            f'Saldo de R$ {saldo:,.2f} excede o limite de R$ {TOLERANCIA:,.2f} para quitação automática. '
            f'Registre um pagamento ou ajuste manual.'
        )
        return redirect('financeiro:conta_pagar_detail', pk=pk)

    with transaction.atomic():
        AjusteContaPagar.objects.create(
            conta_pagar=conta,
            tipo='DESCONTO_DIVERGENCIA',
            valor_ajuste=-saldo,
            motivo=f'Quitação de saldo residual — R$ {saldo:,.2f}',
            aprovado=True,
            aprovado_por=request.user,
            observacao=(
                f'Baixa automática do saldo residual de R$ {saldo:,.2f}. '
                f'Operador: {request.user.get_full_name() or request.user.username}'
            )
        )

        conta.valor_ajustado = total_pago
        conta.status = 'PAGA'
        conta.save(update_fields=['valor_ajustado', 'status'])

        # Fecha parcelas ainda abertas (caso haja)
        conta.parcelas.filter(status__in=['ABERTA', 'VENCIDA']).update(status='PAGA')

    messages.success(
        request,
        f'Conta quitada! Desconto de R$ {saldo:,.2f} registrado como ajuste por divergência.'
    )
    return redirect('financeiro:conta_pagar_detail', pk=pk)


@login_required
def conta_pagar_create(request):
    """Criar nova conta a pagar"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        form = ContaPageForm(request.POST, empresa=empresa)
        if form.is_valid():
            with transaction.atomic():
                conta = form.save(commit=False)
                conta.empresa = empresa
                conta.criado_por = request.user
                conta.calcular_valor_ajustado()
                conta.save()
                
                # Gerar número automático se não tiver
                if not conta.numero:
                    conta.numero = f"CP-{conta.id:06d}"
                    conta.save(update_fields=['numero'])

                _gerar_parcelas_automaticas(
                    conta=conta,
                    quantidade_parcelas=form.cleaned_data.get('quantidade_parcelas') or 1,
                    intervalo_dias=form.cleaned_data.get('intervalo_dias') or 30,
                    primeira_data_vencimento=form.cleaned_data['primeira_data_vencimento'],
                )
            
            messages.success(
                request,
                f'Conta {conta.numero} criada com {conta.parcelas.count()} parcelas automaticamente!'
            )
            return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    else:
        form = ContaPageForm(
            initial={'empresa': empresa, 'data_emissao': timezone.now().date()},
            empresa=empresa,
        )
    
    context = {
        'form': form,
        'title': 'Criar Conta a Pagar'
    }
    
    return render(request, 'financeiro/conta_pagar_form.html', context)


@login_required
def conta_pagar_edit(request, pk):
    """Editar conta a pagar"""
    empresa = request.user.empresa
    conta = get_object_or_404(ContaPagar, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        form = ContaPageForm(request.POST, instance=conta, empresa=empresa)
        if form.is_valid():
            conta = form.save(commit=False)
            conta.calcular_valor_ajustado()
            conta.save()
            messages.success(request, f'Conta {conta.numero} atualizada com sucesso!')
            return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    else:
        form = ContaPageForm(instance=conta, empresa=empresa)
    
    context = {
        'form': form,
        'conta': conta,
        'title': f'Editar Conta {conta.numero}'
    }
    
    return render(request, 'financeiro/conta_pagar_form.html', context)


@login_required
def conta_pagar_aprovar(request, pk):
    """Aprovar conta a pagar (se requer_aprovacao=True)"""
    empresa = request.user.empresa
    conta = get_object_or_404(ContaPagar, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        try:
            conta.aprovar(request.user)
            messages.success(request, f'Conta {conta.numero} aprovada com sucesso!')
        except Exception as e:
            messages.error(request, f'Erro ao aprovar: {str(e)}')
        
        return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    
    context = {
        'conta': conta,
        'parcelas': conta.parcelas.all().order_by('numero_parcela'),
        'title': f'Aprovar Conta {conta.numero}'
    }

    return render(request, 'financeiro/conta_pagar_confirm.html', context)


# ============================================
# VIEWS - PARCELAS
# ============================================

@login_required
def parcela_list(request):
    """Listagem de parcelas com filtros de vencimento"""
    empresa = request.user.empresa
    
    parcelas = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa
    ).select_related('conta_pagar__fornecedor').annotate(
        total_parcelas_conta=Count('conta_pagar__parcelas', distinct=True),
        parcelas_pagas_conta=Count('conta_pagar__parcelas', filter=Q(conta_pagar__parcelas__status='PAGA'), distinct=True),
    )
    
    # Filtros
    status = request.GET.get('status', '')
    vencimento = request.GET.get('vencimento') or request.GET.get('tipo_vencimento') or 'todas'
    
    if status:
        parcelas = parcelas.filter(status=status)
    
    hoje = timezone.now().date()
    if vencimento == 'vencidas':
        parcelas = parcelas.filter(
            data_vencimento__lt=hoje,
            status='ABERTA'
        )
    elif vencimento in ['proximas', 'proximas_7']:
        parcelas = parcelas.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=7),
            status='ABERTA'
        )
    elif vencimento in ['30dias', 'proximas_30']:
        parcelas = parcelas.filter(
            data_vencimento__gte=hoje,
            data_vencimento__lte=hoje + timedelta(days=30),
            status='ABERTA'
        )
    
    # Ordenação
    order_by = request.GET.get('order_by', 'data_vencimento')
    parcelas = parcelas.order_by(order_by)
    
    # Paginação
    paginator = Paginator(parcelas, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    agregados = ParcelaContaPagar.objects.filter(conta_pagar__empresa=empresa).aggregate(
        total=Count('id'),
        abertas=Count('id', filter=Q(status='ABERTA')),
        vencidas=Count('id', filter=Q(status='VENCIDA')),
        pagas=Count('id', filter=Q(status='PAGA')),
    )

    context = {
        'page_obj': page_obj,
        'parcelas': page_obj.object_list,
        'status_filter': status,
        'vencimento_filter': vencimento,
        'total_parcelas': agregados['total'],
        'parcelas_abertas': agregados['abertas'],
        'parcelas_vencidas': agregados['vencidas'],
        'parcelas_pagas': agregados['pagas'],
        'is_paginated': page_obj.has_other_pages(),
    }
    
    return render(request, 'financeiro/parcela_list.html', context)


@login_required
def parcela_criar(request, conta_pk):
    """
    Criar parcelas para uma conta a pagar de forma inteligente
    Permite definir condição de pagamento, forma de pagamento e gera automaticamente
    """
    empresa = request.user.empresa
    conta = get_object_or_404(ContaPagar, pk=conta_pk, empresa=empresa)
    
    # Se conta já tem parcelas, redireciona para detalhe
    if conta.parcelas.exists():
        messages.warning(request, 'Esta conta já possui parcelas. Use a edição para modificar.')
        return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    
    formas_pagamento = FormaPagemento.objects.filter(ativo=True).order_by('ordem_exibicao')
    
    # Condições de pagamento padrão
    condicoes_padrao = [
        {'valor': '0', 'label': 'À Vista', 'dias': [0]},
        {'valor': '30', 'label': '30 Dias', 'dias': [30]},
        {'valor': '30/60', 'label': '30/60 Dias', 'dias': [30, 60]},
        {'valor': '30/60/90', 'label': '30/60/90 Dias', 'dias': [30, 60, 90]},
        {'valor': '15/28', 'label': '15/28 Dias', 'dias': [15, 28]},
        {'valor': 'custom', 'label': 'Customizado', 'dias': []},
    ]
    
    if request.method == 'GET':
        context = {
            'conta': conta,
            'condicoes': condicoes_padrao,
            'formas_pagamento': formas_pagamento,
        }
        return render(request, 'financeiro/parcela_criar_multiplas.html', context)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Deletar parcelas existentes (se houver)
                conta.parcelas.all().delete()
                
                # Obter dados do formulário
                condicao = request.POST.get('condicao_pagamento', '30')
                forma_padrao_id = request.POST.get('forma_pagamento_padrao')
                
                # Determinar os dias de vencimento
                if condicao == 'custom':
                    dias_list = [int(d) for d in request.POST.getlist('dias_customizado[]') if d]
                else:
                    # Encontrar a condição padrão
                    cond_obj = next((c for c in condicoes_padrao if c['valor'] == condicao), None)
                    dias_list = cond_obj['dias'] if cond_obj else [0]
                
                if not dias_list:
                    messages.error(request, 'Informe pelo menos um período de vencimento.')
                    return redirect('financeiro:parcela_criar', conta_pk=conta.pk)
                
                num_parcelas = len(dias_list)
                valor_parcela = conta.valor_total / num_parcelas
                valor_acumulado = Decimal('0')
                
                # Criar parcelas
                for idx, dias in enumerate(dias_list, 1):
                    # Última parcela recebe o restante
                    if idx == num_parcelas:
                        valor = conta.valor_total - valor_acumulado
                    else:
                        valor = valor_parcela
                    
                    valor_acumulado += valor
                    
                    # Calcular data de vencimento
                    from datetime import timedelta
                    data_vencimento = conta.data_emissao + timedelta(days=dias)
                    
                    # Obter forma de pagamento
                    forma_pagamento = None
                    if forma_padrao_id:
                        try:
                            forma_pagamento = FormaPagemento.objects.get(pk=forma_padrao_id)
                        except FormaPagemento.DoesNotExist:
                            pass
                    
                    # Criar parcela
                    parcela = ParcelaContaPagar.objects.create(
                        conta_pagar=conta,
                        numero_parcela=idx,
                        valor_parcela=valor,
                        valor_total_parcela=valor,  # Garante preenchimento obrigatório
                        forma_pagamento=forma_pagamento,
                        data_vencimento=data_vencimento,
                        status='ABERTA'
                    )
                    parcela.recalcular_total()
                    parcela.save()
                
                messages.success(
                    request,
                    f'✅ {num_parcelas} parcelas criadas com sucesso para {conta.numero}!'
                )
                return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
        
        except Exception as e:
            messages.error(request, f'Erro ao criar parcelas: {str(e)}')
            return redirect('financeiro:parcela_criar', conta_pk=conta.pk)
    
    context = {
        'conta': conta,
        'formas_pagamento': formas_pagamento,
        'condicoes': condicoes_padrao,
    }
    return render(request, 'financeiro/parcela_criar_multiplas.html', context)


# ============================================
# VIEWS - PAGAMENTOS
# ============================================

@login_required
def parcela_pagar(request, parcela_pk):
    """Registrar pagamento de uma parcela"""
    empresa = request.user.empresa
    parcela = get_object_or_404(
        ParcelaContaPagar,
        pk=parcela_pk,
        conta_pagar__empresa=empresa
    )
    
    if request.method == 'POST':
        form = PagamentoContaPageForm(request.POST, request.FILES)
        if form.is_valid():
            # Cancelar pagamentos PENDENTE anteriores desta parcela para evitar duplicidade
            parcela.pagamentos.filter(status='PENDENTE').update(status='CANCELADO')

            pagamento = form.save(commit=False)
            pagamento.parcela = parcela
            pagamento.conta_pagar = parcela.conta_pagar
            pagamento.pago_por = request.user
            pagamento.status = 'COMPENSADO'
            pagamento.save()

            # Atualizar status da parcela
            parcela.status = 'PAGA'
            parcela.data_pagamento = pagamento.data_pagamento
            parcela.save()

            # Atualizar status da ContaPagar se todas as parcelas estiverem pagas
            conta = parcela.conta_pagar
            if not conta.parcelas.exclude(status='PAGA').exists():
                conta.status = 'PAGA'
                conta.save(update_fields=['status'])

            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    else:
        # Pré-preencher valor sugerido (valor total com juros/multa)
        form = PagamentoContaPageForm(initial={
            'valor_pago': parcela.valor_total_parcela,
            'data_pagamento': timezone.now().date()
        })
    
    context = {
        'form': form,
        'parcela': parcela,
        'title': f'Registrar Pagamento - Parcela {parcela.numero_parcela}'
    }
    
    return render(request, 'financeiro/pagamento_form.html', context)


@login_required
def parcela_atualizar_juros_multa(request, parcela_pk):
    """Atualiza manualmente juros e multa de uma parcela em aberto (AJAX).

    Cada fornecedor cobra atraso do seu jeito (valor fechado informado por telefone,
    juros por dia, etc.), por isso o valor é digitado manualmente aqui em vez de
    aplicar uma taxa automática única.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido.'}, status=405)

    empresa = request.user.empresa
    parcela = get_object_or_404(
        ParcelaContaPagar,
        pk=parcela_pk,
        conta_pagar__empresa=empresa
    )

    if parcela.status not in ('ABERTA', 'VENCIDA'):
        return JsonResponse(
            {'success': False, 'error': 'Só é possível editar juros/multa de parcelas em aberto ou vencidas.'},
            status=400
        )

    def _parse_valor(nome):
        bruto = (request.POST.get(nome) or '0').replace(',', '.').strip()
        try:
            valor = Decimal(bruto or '0')
        except InvalidOperation:
            raise ValueError(f'Valor informado para {nome} é inválido.')
        if valor < 0:
            raise ValueError(f'Valor de {nome} não pode ser negativo.')
        return valor.quantize(Decimal('0.01'))

    try:
        juros = _parse_valor('juros')
        multa = _parse_valor('multa')
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)

    parcela.juros_parcela = juros
    parcela.multa_parcela = multa
    parcela.recalcular_total()
    parcela.save(update_fields=['juros_parcela', 'multa_parcela', 'valor_total_parcela', 'dias_atraso', 'data_atualizacao'])

    return JsonResponse({
        'success': True,
        'valor_total_parcela': str(parcela.valor_total_parcela),
        'juros_parcela': str(parcela.juros_parcela),
        'multa_parcela': str(parcela.multa_parcela),
    })


# ============================================
# VIEWS - RELATÓRIOS
# ============================================

@login_required
def relatorio_contas_vencer(request):
    """Relatório de contas a vencer (próximos 30 dias)"""
    empresa = request.user.empresa
    
    hoje = timezone.now().date()
    proximos_30_dias = hoje + timedelta(days=30)
    
    contas = ContaPagar.objects.filter(
        empresa=empresa,
        parcelas__data_vencimento__gte=hoje,
        parcelas__data_vencimento__lte=proximos_30_dias,
        parcelas__status='ABERTA'
    ).distinct().prefetch_related('fornecedor', 'parcelas')
    
    parcelas_vencer = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=hoje,
        data_vencimento__lte=proximos_30_dias,
        status='ABERTA'
    ).order_by('data_vencimento').prefetch_related('conta_pagar__fornecedor')
    
    total_a_vencer = parcelas_vencer.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    
    context = {
        'contas': contas,
        'parcelas': parcelas_vencer,
        'total_a_vencer': total_a_vencer,
        'titulo': 'Contas a Vencer (Próximos 30 dias)',
    }
    
    return render(request, 'financeiro/relatorio_contas_vencer.html', context)


@login_required
def relatorio_contas_vencidas(request):
    """Relatório de contas vencidas"""
    empresa = request.user.empresa
    
    hoje = timezone.now().date()
    
    parcelas_vencidas = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__lt=hoje,
        status__in=['ABERTA', 'VENCIDA']
    ).order_by('data_vencimento').prefetch_related('conta_pagar__fornecedor')
    
    total_vencido = parcelas_vencidas.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    
    context = {
        'parcelas': parcelas_vencidas,
        'total_vencido': total_vencido,
        'titulo': 'Contas Vencidas',
    }
    
    return render(request, 'financeiro/relatorio_contas_vencidas.html', context)


@login_required
def relatorio_fluxo_caixa(request):
    """Relatório de fluxo de caixa"""
    empresa = request.user.empresa
    
    mes_str = request.GET.get('mes', timezone.now().strftime('%Y-%m'))
    
    try:
        ano, mes = map(int, mes_str.split('-'))
    except:
        ano, mes = timezone.now().year, timezone.now().month
    
    # Calcular primeiro e último dia do mês
    if mes == 12:
        proximo_mes = (ano + 1, 1)
    else:
        proximo_mes = (ano, mes + 1)
    
    primeiro_dia = timezone.datetime(ano, mes, 1).date()
    ultimo_dia = (timezone.datetime(proximo_mes[0], proximo_mes[1], 1) - timedelta(days=1)).date()
    
    # Parcelas vencendo no mês
    parcelas_vencer = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=primeiro_dia,
        data_vencimento__lte=ultimo_dia,
        status__in=['ABERTA', 'VENCIDA']
    ).order_by('data_vencimento')
    
    # Pagamentos realizados no mês
    pagamentos = PagamentoContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_pagamento__gte=primeiro_dia,
        data_pagamento__lte=ultimo_dia,
        status='COMPENSADO'
    ).order_by('data_pagamento')
    
    total_saida = parcelas_vencer.aggregate(Sum('valor_total_parcela'))['valor_total_parcela__sum'] or Decimal('0.00')
    total_entrada = pagamentos.aggregate(Sum('valor_pago'))['valor_pago__sum'] or Decimal('0.00')
    
    context = {
        'mes_str': mes_str,
        'mes': mes,
        'ano': ano,
        'parcelas_vencer': parcelas_vencer,
        'pagamentos': pagamentos,
        'total_saida': total_saida,
        'total_entrada': total_entrada,
        'saldo': total_entrada - total_saida,
        'titulo': f'Fluxo de Caixa - {mes:02d}/{ano}',
    }
    
    return render(request, 'financeiro/relatorio_fluxo_caixa.html', context)


# ============================================
# API AUXILIARES
# ============================================

@login_required
def recalcular_juros_multas(request, conta_pk):
    """API para recalcular juros e multas de uma conta"""
    empresa = request.user.empresa
    conta = get_object_or_404(ContaPagar, pk=conta_pk, empresa=empresa)
    
    config = empresa.configuracao_juros_multa
    if not config:
        messages.error(request, 'Configuração de juros/multa não encontrada!')
        return redirect('financeiro:conta_pagar_detail', pk=conta.pk)
    
    # Recalcular cada parcela
    for parcela in conta.parcelas.filter(status='ABERTA'):
        parcela.recalcular_total()
        parcela.save()
    
    # Recalcular totais da conta
    total_juros = conta.parcelas.aggregate(Sum('juros_parcela'))['juros_parcela__sum'] or Decimal('0.00')
    total_multa = conta.parcelas.aggregate(Sum('multa_parcela'))['multa_parcela__sum'] or Decimal('0.00')
    
    conta.juros_acumulados = total_juros
    conta.multa_acumulada = total_multa
    conta.save()
    
    messages.success(request, 'Juros e multas recalculados com sucesso!')
    return redirect('financeiro:conta_pagar_detail', pk=conta.pk)


# ============================================
# CONTAS A RECEBER
# ============================================

def _gerar_numero_cr(empresa):
    """Gera próximo número CR-YYYY-NNNN para a empresa."""
    from django.utils import timezone as tz
    ano = tz.now().year
    prefixo = f"CR-{ano}-"
    ultimo = (
        ContaReceber.objects
        .filter(empresa=empresa, numero__startswith=prefixo)
        .order_by('numero')
        .last()
    )
    if ultimo:
        seq = int(ultimo.numero.split('-')[-1]) + 1
    else:
        seq = 1
    return f"{prefixo}{seq:04d}"


@login_required
def conta_receber_list(request):
    empresa = request.user.empresa
    qs = ContaReceber.objects.filter(empresa=empresa).select_related('cliente')

    status_f = request.GET.get('status', '')
    moeda_f = request.GET.get('moeda', '')
    q = request.GET.get('q', '')
    data_ini = request.GET.get('data_ini', '')
    data_fim = request.GET.get('data_fim', '')

    if status_f:
        qs = qs.filter(status=status_f)
    if moeda_f:
        qs = qs.filter(moeda=moeda_f)
    if q:
        qs = qs.filter(
            Q(numero__icontains=q) | Q(cliente__razao_social__icontains=q) | Q(descricao__icontains=q)
        )
    if data_ini:
        qs = qs.filter(data_vencimento__gte=data_ini)
    if data_fim:
        qs = qs.filter(data_vencimento__lte=data_fim)

    # Totais
    totais = qs.aggregate(
        total_brl=Sum('valor_brl'),
        total_recebido=Sum('recebimentos__valor_recebido_brl'),
    )

    paginator = Paginator(qs.order_by('-data_emissao'), 20)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'financeiro/conta_receber/list.html', {
        'page_obj': page,
        'status_choices': ContaReceber.STATUS_CHOICES,
        'moeda_choices': ContaReceber.MOEDA_CHOICES,
        'filtros': {'status': status_f, 'moeda': moeda_f, 'q': q, 'data_ini': data_ini, 'data_fim': data_fim},
        'totais': totais,
    })


@login_required
def conta_receber_create(request):
    empresa = request.user.empresa
    if request.method == 'POST':
        form = ContaReceberForm(request.POST, empresa=empresa)
        formset = ParcelaContaReceberFormSet(request.POST, prefix='parcelas')
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                cr = form.save(commit=False)
                cr.empresa = empresa
                cr.numero = _gerar_numero_cr(empresa)
                cr.origem = 'MANUAL'
                cr.criado_por = request.user
                cr.save()
                formset.instance = cr
                formset.save()
            messages.success(request, f'Conta a Receber {cr.numero} criada.')
            return redirect('financeiro:conta_receber_detail', pk=cr.pk)
    else:
        form = ContaReceberForm(empresa=empresa)
        formset = ParcelaContaReceberFormSet(prefix='parcelas')
    return render(request, 'financeiro/conta_receber/form.html', {
        'form': form, 'formset': formset, 'title': 'Nova Conta a Receber',
    })


@login_required
def conta_receber_detail(request, pk):
    empresa = request.user.empresa
    cr = get_object_or_404(ContaReceber, pk=pk, empresa=empresa)
    parcelas = cr.parcelas.order_by('numero_parcela')
    recebimentos = cr.recebimentos.order_by('-data_pagamento')
    return render(request, 'financeiro/conta_receber/detail.html', {
        'cr': cr, 'parcelas': parcelas, 'recebimentos': recebimentos,
    })


@login_required
def conta_receber_cancelar(request, pk):
    if request.method == 'POST':
        empresa = request.user.empresa
        cr = get_object_or_404(ContaReceber, pk=pk, empresa=empresa)
        if cr.status == 'CANCELADA':
            messages.warning(request, 'Conta já está cancelada.')
        else:
            cr.status = 'CANCELADA'
            cr.save()
            messages.success(request, f'Conta {cr.numero} cancelada.')
    return redirect('financeiro:conta_receber_detail', pk=pk)


@login_required
def parcela_receber_registrar(request, parcela_pk):
    """Registra recebimento de uma parcela."""
    empresa = request.user.empresa
    parcela = get_object_or_404(ParcelaContaReceber, pk=parcela_pk, conta_receber__empresa=empresa)
    cr = parcela.conta_receber

    if request.method == 'POST':
        form = RecebimentoContaReceberForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                rec = form.save(commit=False)
                rec.parcela = parcela
                rec.conta_receber = cr
                rec.recebido_por = request.user
                rec.save()
                parcela.status = 'PAGA'
                parcela.data_pagamento = rec.data_pagamento
                parcela.save()
                cr.atualizar_status()
            messages.success(request, 'Recebimento registrado.')
            return redirect('financeiro:conta_receber_detail', pk=cr.pk)
    else:
        from django.utils import timezone as tz
        form = RecebimentoContaReceberForm(initial={
            'data_pagamento': tz.now().date(),
            'valor_recebido_moeda': parcela.valor_parcela_moeda,
            'valor_recebido_brl': parcela.valor_parcela_brl,
        })
    return render(request, 'financeiro/conta_receber/registrar_recebimento.html', {
        'form': form, 'parcela': parcela, 'cr': cr,
    })
