from django.db.models import Q

from .models import DrawbackProdutoAC


def produto_do_recebimento(item_recebimento):
    if item_recebimento.produto_id:
        return item_recebimento.produto
    if item_recebimento.item_pedido_id:
        return item_recebimento.item_pedido.produto
    return None


def _produto_ou_base_q(produto):
    """Q que casa tanto o produto exato quanto o produto principal dele (caso
    seja uma variante) — o AC pode estar cadastrado em qualquer um dos dois."""
    if produto.produto_base_id:
        return Q(produto_id__in=[produto.pk, produto.produto_base_id])
    return Q(produto=produto)


def sugerir_vinculo_entrada(item_recebimento, empresa):
    """Retorna o DrawbackProdutoAC mais adequado para vincular este item de
    recebimento, ou None se não houver nenhum AC ativo com saldo de compra
    disponível para o produto (ou para o produto principal, se o item for
    uma variante). Prioriza o AC que vence mais cedo."""
    produto = produto_do_recebimento(item_recebimento)
    if not produto:
        return None
    candidatos = DrawbackProdutoAC.objects.filter(
        _produto_ou_base_q(produto),
        tipo_produto__in=['IMPORTACAO', 'MERCADO_INTERNO'],
        ato_concessorio__empresa=empresa,
        ato_concessorio__status='ATIVO',
    ).select_related('ato_concessorio').order_by('ato_concessorio__data_vencimento')
    for candidato in candidatos:
        if candidato.saldo_compra > 0:
            return candidato
    return None


def sugerir_vinculo_saida(item_nfe, empresa):
    """Retorna o DrawbackProdutoAC mais adequado para vincular este item de
    NF-e de exportação, ou None se não houver nenhum AC ativo com saldo de
    exportação disponível para o produto (ou para o produto principal, se o
    item for uma variante). Prioriza o AC que vence mais cedo."""
    if not item_nfe.produto_id:
        return None
    candidatos = DrawbackProdutoAC.objects.filter(
        _produto_ou_base_q(item_nfe.produto),
        tipo_produto='EXPORTACAO',
        ato_concessorio__empresa=empresa,
        ato_concessorio__status='ATIVO',
    ).select_related('ato_concessorio').order_by('ato_concessorio__data_vencimento')
    for candidato in candidatos:
        if candidato.saldo_exportacao > 0:
            return candidato
    return None
