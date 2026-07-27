"""Calculo de reserva/empenho de estoque para insumos comprometidos em
Ordens de Servico e Requisicoes que ainda nao foram baixados fisicamente
(inclui OS ja concluidas cuja baixa ainda depende de execucao manual pelo
almoxarifado — ver `operacoes_campo.views_os.os_concluir`)."""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Sum, When


def reservas_por_produto(empresa, excluir_os_id=None, excluir_requisicao_id=None):
    """Calcula, em duas queries (independente do numero de produtos), quanto
    de cada produto esta comprometido em OS APROVADA/EM_ANDAMENTO, em OS
    CONCLUIDA cuja baixa ainda nao foi executada pelo almoxarifado, ou em
    Requisicao APROVADA mas ainda nao gerou MovimentacaoEstoque.
    Retorna {produto_id: Decimal}."""
    from operacoes_campo.models import OrdemServicoInsumo
    from cadastros.models import RequisicaoItem

    totais = defaultdict(lambda: Decimal('0'))

    os_qs = OrdemServicoInsumo.objects.filter(
        os__empresa=empresa,
        os__status__in=['APROVADA', 'EM_ANDAMENTO', 'CONCLUIDA'],
    ).exclude(os__status='CONCLUIDA', movimentacao__status='EXECUTADO')
    if excluir_os_id:
        os_qs = os_qs.exclude(os_id=excluir_os_id)
    for row in os_qs.values('produto_id').annotate(total=Sum('quantidade_aplicada')):
        totais[row['produto_id']] += row['total'] or Decimal('0')

    req_qs = RequisicaoItem.objects.filter(
        requisicao__empresa=empresa,
        requisicao__status='APROVADA',
    )
    if excluir_requisicao_id:
        req_qs = req_qs.exclude(requisicao_id=excluir_requisicao_id)
    quantidade_efetiva = Case(
        When(quantidade_atendida__gt=0, then=F('quantidade_atendida')),
        default=F('quantidade_solicitada'),
        output_field=DecimalField(max_digits=15, decimal_places=3),
    )
    for row in req_qs.values('produto_id').annotate(total=Sum(quantidade_efetiva)):
        totais[row['produto_id']] += row['total'] or Decimal('0')

    return dict(totais)


def quantidade_reservada(produto, empresa, excluir_os_id=None, excluir_requisicao_id=None):
    """Reserva de um unico produto. Para listas com varios produtos, prefira
    `reservas_por_produto` (evita 1 par de queries por produto)."""
    totais = reservas_por_produto(empresa, excluir_os_id=excluir_os_id, excluir_requisicao_id=excluir_requisicao_id)
    return totais.get(produto.id, Decimal('0'))


def estoque_disponivel(produto, empresa, excluir_os_id=None, excluir_requisicao_id=None):
    """Saldo fisico menos o que ja esta reservado por outras OS/requisicoes em aberto."""
    atual = Decimal(produto.estoque_atual or 0)
    reservado = quantidade_reservada(
        produto, empresa,
        excluir_os_id=excluir_os_id,
        excluir_requisicao_id=excluir_requisicao_id,
    )
    return atual - reservado
