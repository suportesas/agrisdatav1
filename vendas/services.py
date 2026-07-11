def sincronizar_status_pedido(pedido):
    """Sincroniza `PedidoVenda.status` com o status do documento fiscal vinculado.

    O pedido só é considerado CONCLUIDO quando a NF-e/Invoice vinculada é
    efetivamente EMITIDA (não no instante em que o documento é criado em
    RASCUNHO). Se o documento for cancelado depois de o pedido já estar
    CONCLUIDO, o pedido reverte para CONFIRMADO (não para CANCELADO — o
    cancelamento do pedido em si continua sendo uma ação separada via
    `pedido_cancelar`).
    """
    documento = pedido.nota_fiscal or pedido.invoice
    if documento is None:
        return

    if documento.status == 'EMITIDA' and pedido.status != 'CONCLUIDO':
        pedido.status = 'CONCLUIDO'
        pedido.save(update_fields=['status'])
    elif documento.status == 'CANCELADA' and pedido.status == 'CONCLUIDO':
        pedido.status = 'CONFIRMADO'
        pedido.save(update_fields=['status'])
