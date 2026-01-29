from django.shortcuts import render
from compras.models import SolicitacaoCompra, PedidoCompra
from django.db.models import Count, Sum
from produtos.models import Produto
from django.utils import timezone
from datetime import timedelta
from cadastros.models import Fornecedor

def dashboard_compras(request):
    empresa = request.user.empresa
    hoje = timezone.now().date()
    # inicio_mes e inicio_ano removidos pois não são usados
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    # Total de compras
    compras_ano = PedidoCompra.objects.filter(empresa=empresa, data_pedido__year=hoje.year).aggregate(total=Sum('valor_total'))['total'] or 0
    compras_mes = PedidoCompra.objects.filter(empresa=empresa, data_pedido__year=hoje.year, data_pedido__month=hoje.month).aggregate(total=Sum('valor_total'))['total'] or 0
    compras_semana = PedidoCompra.objects.filter(empresa=empresa, data_pedido__date__gte=inicio_semana).aggregate(total=Sum('valor_total'))['total'] or 0

    # Status das solicitações
    status_counts = SolicitacaoCompra.objects.filter(empresa=empresa).values('status').annotate(qtd=Count('id'))
    status_dict = {s['status']: s['qtd'] for s in status_counts}

    # Produtos mais comprados
    produtos_mais_comprados = Produto.objects.filter(
        itens_pedido_compra__pedido__empresa=empresa
    ).annotate(
        total_comprado=Sum('itens_pedido_compra__quantidade_pedida')
    ).order_by('-total_comprado')[:5]

    # Pedidos pendentes de aprovação
    pedidos_pendentes = PedidoCompra.objects.filter(empresa=empresa, status='PENDENTE')

    # Rank dos fornecedores de compra
    fornecedores_rank = (
        Fornecedor.objects.filter(pedidos_compra__empresa=empresa)
        .annotate(total_comprado=Sum('pedidos_compra__valor_total'))
        .order_by('-total_comprado')[:5]
    )
    context = {
        'compras_ano': compras_ano,
        'compras_mes': compras_mes,
        'compras_semana': compras_semana,
        'status_dict': status_dict,
        'produtos_mais_comprados': produtos_mais_comprados,
        'pedidos_pendentes': pedidos_pendentes,
        'fornecedores_rank': fornecedores_rank,
    }
    return render(request, 'compras/dashboard_compras.html', context)
