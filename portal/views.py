"""
Views do Portal do Cliente — acesso externo (nacionais e internacionais)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal

from financeiro.models import ContaReceber
from faturamento.models import NotaFiscal, InvoiceExportacao, PackingList


def _get_cliente(user):
    """Retorna o Cliente vinculado ao usuário do portal, ou None."""
    try:
        return user.cliente_vinculado.filter(acesso_portal=True).first()
    except Exception:
        return None


def portal_redirect_if_not_cliente(view_func):
    """Decorator: redireciona para login se não houver cliente vinculado."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/portal/cliente/login/?next=' + request.path)
        cliente = _get_cliente(request.user)
        if not cliente:
            return redirect('/portal/cliente/login/')
        return view_func(request, *args, cliente=cliente, **kwargs)
    return wrapper


@portal_redirect_if_not_cliente
def portal_dashboard(request, cliente=None):
    empresa = cliente.empresa
    hoje = timezone.now().date()

    contas = ContaReceber.objects.filter(empresa=empresa, cliente=cliente)

    total_aberto_brl = contas.filter(status__in=['ABERTA', 'VENCIDA', 'PARCIALMENTE_PAGA']).aggregate(
        s=Sum('valor_brl')
    )['s'] or Decimal('0.00')

    vencidas = contas.filter(status='VENCIDA').count()

    proximas = contas.filter(
        status='ABERTA',
        data_vencimento__gte=hoje,
        data_vencimento__lte=hoje + __import__('datetime').timedelta(days=30)
    ).order_by('data_vencimento').first()

    ultimas = contas.exclude(status='CANCELADA').order_by('-data_emissao')[:5]

    # Resumo por moeda
    por_moeda = contas.filter(status__in=['ABERTA', 'VENCIDA', 'PARCIALMENTE_PAGA']).values('moeda').annotate(
        total=Sum('valor_moeda')
    ).order_by('moeda')

    return render(request, 'portal/dashboard.html', {
        'cliente': cliente,
        'total_aberto_brl': total_aberto_brl,
        'vencidas': vencidas,
        'proxima_parcela': proximas,
        'ultimas': ultimas,
        'por_moeda': por_moeda,
    })


@portal_redirect_if_not_cliente
def portal_financeiro_list(request, cliente=None):
    empresa = cliente.empresa
    qs = ContaReceber.objects.filter(empresa=empresa, cliente=cliente).exclude(status='CANCELADA')

    status_f = request.GET.get('status', '')
    if status_f:
        qs = qs.filter(status=status_f)

    return render(request, 'portal/financeiro/list.html', {
        'cliente': cliente,
        'contas': qs.order_by('-data_emissao'),
        'status_choices': ContaReceber.STATUS_CHOICES,
        'status_filtro': status_f,
    })


@portal_redirect_if_not_cliente
def portal_financeiro_detail(request, pk, cliente=None):
    empresa = cliente.empresa
    cr = get_object_or_404(ContaReceber, pk=pk, empresa=empresa, cliente=cliente)
    parcelas = cr.parcelas.order_by('numero_parcela')
    recebimentos = cr.recebimentos.order_by('-data_pagamento')
    return render(request, 'portal/financeiro/detail.html', {
        'cliente': cliente,
        'cr': cr,
        'parcelas': parcelas,
        'recebimentos': recebimentos,
    })


@portal_redirect_if_not_cliente
def portal_documentos_list(request, cliente=None):
    empresa = cliente.empresa
    notas = NotaFiscal.objects.filter(empresa=empresa, cliente=cliente, status='EMITIDA').order_by('-data_emissao')
    invoices = InvoiceExportacao.objects.filter(empresa=empresa, cliente=cliente, status='EMITIDA').order_by('-data_emissao')
    pls = PackingList.objects.filter(empresa=empresa, invoice__cliente=cliente, status='EMITIDO').order_by('-data_emissao')
    return render(request, 'portal/documentos/list.html', {
        'cliente': cliente,
        'notas': notas,
        'invoices': invoices,
        'packing_lists': pls,
    })
