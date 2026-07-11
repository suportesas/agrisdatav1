"""Serviços de negócio do módulo de compras.

Reaproveitados tanto pelo fluxo formal (pedido_gerar) quanto pelos atalhos
permissionados que montam uma Cotacao sintética sem passar por uma request
HTTP (Pedido Direto, Regularização Posterior via Entrada Direta de NF-e).
"""
from datetime import timedelta

from django.utils import timezone


def gerar_pedidos_de_cotacao(cotacao, usuario):
    """Gera um PedidoCompra por fornecedor vencedor de uma Cotacao concluída.

    Agrupa as propostas selecionadas (FornecedorCotacao.selecionado=True) por
    fornecedor e cria um PedidoCompra + ItemPedidoCompra para cada grupo,
    marca os itens da solicitação de origem como APROVADO e a solicitação
    como EM_COMPRA.

    Levanta ValueError com mensagem amigável em caso de erro de negócio
    (cotação não concluída, pedidos já gerados, nenhuma proposta vencedora).
    Retorna (pedidos_criados, avisos_credito) — avisos_credito é uma lista de
    strings para o chamador decidir como exibir (messages, log, etc).
    """
    from .models import PedidoCompra, ItemPedidoCompra, FornecedorCotacao

    if cotacao.status != 'CONCLUIDA':
        raise ValueError('A cotação ainda não está concluída.')

    if PedidoCompra.objects.filter(cotacao=cotacao).exists():
        raise ValueError('Pedidos já foram gerados para esta cotação.')

    propostas_vencedoras = FornecedorCotacao.objects.filter(
        item_cotacao__cotacao=cotacao,
        selecionado=True
    ).select_related('fornecedor', 'item_cotacao__item_solicitacao')

    if not propostas_vencedoras.exists():
        raise ValueError('Nenhum fornecedor foi selecionado na cotação.')

    pedidos_por_fornecedor = {}
    for proposta in propostas_vencedoras:
        fornecedor_id = proposta.fornecedor.id
        if fornecedor_id not in pedidos_por_fornecedor:
            pedidos_por_fornecedor[fornecedor_id] = {
                'fornecedor': proposta.fornecedor,
                'propostas': [],
                'prazo': proposta.prazo_entrega or 0,
                'forma_pagamento': proposta.forma_pagamento or '',
                'condicao_pagamento': proposta.condicao_pagamento or '',
            }
        pedidos_por_fornecedor[fornecedor_id]['propostas'].append(proposta)

    pedidos_criados = []
    avisos_credito = []
    for dados in pedidos_por_fornecedor.values():
        pedido = PedidoCompra.objects.create(
            empresa=cotacao.empresa,
            cotacao=cotacao,
            fornecedor=dados['fornecedor'],
            comprador=usuario,
            status='PENDENTE',
            prazo_entrega_dias=dados['prazo'],
            forma_pagamento=dados['forma_pagamento'],
            condicao_pagamento=dados['condicao_pagamento'],
            data_entrega_prevista=timezone.now().date() + timedelta(days=dados['prazo'])
        )

        for proposta in dados['propostas']:
            item_solicitacao = proposta.item_cotacao.item_solicitacao
            ItemPedidoCompra.objects.create(
                pedido=pedido,
                proposta_fornecedor=proposta,
                produto=item_solicitacao.produto,
                quantidade_pedida=proposta.item_cotacao.quantidade,
                unidade_medida=item_solicitacao.unidade_medida,
                preco_unitario=proposta.preco_unitario,
                preco_total=proposta.preco_unitario * proposta.item_cotacao.quantidade,
                especificacao=proposta.item_cotacao.especificacao or '',
                marca=proposta.marca or '',
            )

        total_pedido = pedido.calcular_total()
        limite_credito = dados['fornecedor'].limite_credito or 0
        if limite_credito and total_pedido > limite_credito:
            avisos_credito.append(
                f'Alerta de crédito: o pedido {pedido.numero} para "{dados["fornecedor"].nome}" '
                f'(R$ {total_pedido:,.2f}) ultrapassa o limite aprovado de R$ {limite_credito:,.2f}.'
            )

        pedidos_criados.append(pedido)

    itens_enviados_ids = set()
    for dados in pedidos_por_fornecedor.values():
        for proposta in dados['propostas']:
            if hasattr(proposta, 'item_cotacao') and hasattr(proposta.item_cotacao, 'item_solicitacao'):
                itens_enviados_ids.add(proposta.item_cotacao.item_solicitacao.id)
    for item in cotacao.solicitacao.itens.all():
        if item.id in itens_enviados_ids:
            item.status_item = 'APROVADO'
            item.save(update_fields=['status_item'])

    cotacao.solicitacao.status = 'EM_COMPRA'
    cotacao.solicitacao.save()

    return pedidos_criados, avisos_credito


def resolver_ou_criar_pedido_para_entrada_direta(empresa, usuario, fornecedor, pedido_id, itens_nf, justificativa):
    """Resolve o PedidoCompra de uma Entrada Direta de NF-e.

    Usado tanto para vincular a um pedido já existente quanto para o caso de
    "Regularização Posterior" (compra feita fora do processo, descoberta só
    quando a nota chega): monta retroativamente SolicitacaoCompra + Cotacao +
    PedidoCompra a partir dos dados já extraídos da NF, preservando a mesma
    cadeia de rastreabilidade do fluxo formal.

    itens_nf: lista de dicts {produto_id, quantidade, preco_unitario, unidade_medida_id}.

    Levanta ValueError se não houver pedido_id nem justificativa.
    Retorna (pedido, mapa_produto_id_para_item_pedido) — o mapa é usado para
    popular ItemRecebimento.item_pedido corretamente em cada item da entrada.
    """
    from .models import PedidoCompra, SolicitacaoCompra, Cotacao, ItemSolicitacaoCompra, ItemCotacao, FornecedorCotacao

    if pedido_id:
        pedido = PedidoCompra.objects.get(pk=pedido_id, empresa=empresa, fornecedor=fornecedor)
        mapa = {item.produto_id: item for item in pedido.itens.all()}
        return pedido, mapa

    if not justificativa:
        raise ValueError('Justificativa é obrigatória para registrar uma entrada sem pedido vinculado.')

    solicitacao = SolicitacaoCompra.objects.create(
        empresa=empresa,
        solicitante=usuario,
        status='APROVADA',
        aprovador=usuario,
        data_aprovacao=timezone.now(),
        data_necessidade=timezone.now().date(),
        justificativa=justificativa,
        origem='REGULARIZACAO_POSTERIOR',
    )
    cotacao = Cotacao.objects.create(
        empresa=empresa,
        solicitacao=solicitacao,
        comprador=usuario,
        status='CONCLUIDA',
    )
    for item_nf in itens_nf:
        item_sol = ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto_id=item_nf['produto_id'],
            quantidade=item_nf['quantidade'],
            unidade_medida_id=item_nf['unidade_medida_id'],
            status_item='COTADO',
        )
        item_cot = ItemCotacao.objects.create(
            cotacao=cotacao,
            item_solicitacao=item_sol,
            produto_id=item_nf['produto_id'],
            quantidade=item_nf['quantidade'],
            unidade_medida_id=item_nf['unidade_medida_id'],
        )
        FornecedorCotacao.objects.create(
            item_cotacao=item_cot,
            fornecedor=fornecedor,
            preco_unitario=item_nf['preco_unitario'],
            preco_total=item_nf['preco_unitario'] * item_nf['quantidade'],
            prazo_entrega=0,
            selecionado=True,
        )

    pedidos, _avisos_credito = gerar_pedidos_de_cotacao(cotacao, usuario)
    pedido = pedidos[0]
    pedido.status = 'RECEBIDO'
    pedido.data_entrega_real = timezone.now().date()
    pedido.save(update_fields=['status', 'data_entrega_real'])

    mapa = {item.produto_id: item for item in pedido.itens.all()}
    return pedido, mapa
