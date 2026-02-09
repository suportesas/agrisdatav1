from django.shortcuts import render
from compras.models import SolicitacaoCompra, PedidoCompra
from django.db.models import Count, Sum
from produtos.models import Produto
from django.utils import timezone
from datetime import date, timedelta
from cadastros.models import Fornecedor

def dashboard_compras(request):
    empresa = request.user.empresa
    hoje = timezone.now().date()
    # inicio_mes e inicio_ano removidos pois não são usados
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    def shift_month(year, month, delta):
        month += delta
        year += (month - 1) // 12
        month = ((month - 1) % 12) + 1
        return year, month

    month_labels = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

    # Total de compras
    compras_ano = PedidoCompra.objects.filter(empresa=empresa, data_pedido__year=hoje.year).aggregate(total=Sum('valor_total'))['total'] or 0
    compras_mes = PedidoCompra.objects.filter(empresa=empresa, data_pedido__year=hoje.year, data_pedido__month=hoje.month).aggregate(total=Sum('valor_total'))['total'] or 0
    compras_semana = PedidoCompra.objects.filter(empresa=empresa, data_pedido__date__gte=inicio_semana).aggregate(total=Sum('valor_total'))['total'] or 0

    # Status das solicitações
    status_counts = SolicitacaoCompra.objects.filter(empresa=empresa).values('status').annotate(qtd=Count('id'))
    status_dict = {s['status']: s['qtd'] for s in status_counts}

    status_color_map = {
        'RASCUNHO': ('#95a5a6', '#d5dbdb'),
        'PENDENTE': ('#f39c12', '#f8c471'),
        'APROVADA': ('#27ae60', '#52be80'),
        'PARCIALMENTE_COTADA': ('#3498db', '#5dade2'),
        'TOTALMENTE_COTADA': ('#6366f1', '#a5b4fc'),
        'CONCLUIDA': ('#2c3e50', '#95a5a6'),
        'CANCELADA': ('#e74c3c', '#ec7063'),
    }

    status_barras = []
    status_choices = getattr(SolicitacaoCompra, 'STATUS_CHOICES', [])
    status_max = max([s['qtd'] for s in status_counts], default=0) or 1
    for status, label in status_choices:
        qtd = status_dict.get(status, 0)
        if qtd == 0:
            continue
        color, color_light = status_color_map.get(status, ('#3498db', '#5dade2'))
        height_pct = int((qtd / status_max) * 100)
        status_barras.append({
            'status': status,
            'label': label,
            'qtd': qtd,
            'height_pct': max(10, height_pct) if qtd > 0 else 0,
            'bar_color': color,
            'bar_color_light': color_light,
        })

    # Compras mensais (últimos 6 meses)
    compras_mensais = []
    totais_meses = []
    for i in range(5, -1, -1):
        ano, mes = shift_month(hoje.year, hoje.month, -i)
        inicio_mes = date(ano, mes, 1)
        prox_ano, prox_mes = shift_month(ano, mes, 1)
        inicio_prox_mes = date(prox_ano, prox_mes, 1)
        total_mes = PedidoCompra.objects.filter(
            empresa=empresa,
            data_pedido__date__gte=inicio_mes,
            data_pedido__date__lt=inicio_prox_mes,
        ).aggregate(total=Sum('valor_total'))['total'] or 0
        totais_meses.append(total_mes)
        compras_mensais.append({
            'label': month_labels[mes - 1],
            'total': total_mes,
        })

    max_total_mes = max(totais_meses, default=0) or 1
    for item in compras_mensais:
        height_pct = int((item['total'] / max_total_mes) * 100)
        item['height_pct'] = max(10, height_pct) if item['total'] > 0 else 0
        item['bar_color'] = '#3498db'
        item['bar_color_light'] = '#5dade2'

    # Comparação mês a mês
    prev_ano, prev_mes = shift_month(hoje.year, hoje.month, -1)
    inicio_prev = date(prev_ano, prev_mes, 1)
    next_ano, next_mes = shift_month(prev_ano, prev_mes, 1)
    inicio_next = date(next_ano, next_mes, 1)
    compras_mes_anterior = PedidoCompra.objects.filter(
        empresa=empresa,
        data_pedido__date__gte=inicio_prev,
        data_pedido__date__lt=inicio_next,
    ).aggregate(total=Sum('valor_total'))['total'] or 0

    if compras_mes_anterior > 0:
        variacao_pct = ((compras_mes - compras_mes_anterior) / compras_mes_anterior) * 100
    else:
        variacao_pct = 100 if compras_mes > 0 else 0

    comparacao_mes = {
        'mes_atual_label': month_labels[hoje.month - 1],
        'mes_anterior_label': month_labels[prev_mes - 1],
        'total_atual': compras_mes,
        'total_anterior': compras_mes_anterior,
        'variacao_pct': variacao_pct,
        'tendencia': 'up' if compras_mes >= compras_mes_anterior else 'down',
    }

    # Produtos mais comprados
    produtos_mais_comprados = Produto.objects.filter(
        itens_pedido_compra__pedido__empresa=empresa
    ).annotate(
        total_comprado=Sum('itens_pedido_compra__quantidade_pedida'),
        valor_total_comprado=Sum('itens_pedido_compra__preco_total')
    ).order_by('-total_comprado')[:5]

    # Pedidos pendentes de aprovação
    pedidos_pendentes = PedidoCompra.objects.filter(empresa=empresa, status='PENDENTE')

    # Rank dos fornecedores de compra
    fornecedores_rank = (
        Fornecedor.objects.filter(pedidos_compra__empresa=empresa)
        .annotate(total_comprado=Sum('pedidos_compra__valor_total'))
        .order_by('-total_comprado')[:5]
    )
    
    # Pedidos parcialmente recebidos (pendentes de recebimento completo)
    pedidos_parcialmente_recebidos = PedidoCompra.objects.filter(
        empresa=empresa,
        status='PARCIALMENTE_RECEBIDO'
    ).select_related('fornecedor').prefetch_related('recebimentos').order_by('-data_pedido')
    
    # Adicionar recebimento pendente a cada pedido
    for pedido in pedidos_parcialmente_recebidos:
        pedido.recebimento_pendente = pedido.recebimentos.exclude(status='FINALIZADO').first()
    

    # Solicitações de compra totalmente cotadas, mas sem pedido gerado
    from compras.models import Cotacao
    solicitacoes_cotadas_sem_pedido = SolicitacaoCompra.objects.filter(
        empresa=empresa,
        status='TOTALMENTE_COTADA'
    ).exclude(
        cotacoes__pedidos__isnull=False
    ).distinct()

    context = {
        'compras_ano': compras_ano,
        'compras_mes': compras_mes,
        'compras_semana': compras_semana,
        'status_dict': status_dict,
        'status_barras': status_barras,
        'compras_mensais': compras_mensais,
        'comparacao_mes': comparacao_mes,
        'produtos_mais_comprados': produtos_mais_comprados,
        'pedidos_pendentes': pedidos_pendentes,
        'fornecedores_rank': fornecedores_rank,
        'pedidos_parcialmente_recebidos': pedidos_parcialmente_recebidos,
        'solicitacoes_cotadas_sem_pedido': solicitacoes_cotadas_sem_pedido,
    }
    return render(request, 'compras/dashboard_compras.html', context)
