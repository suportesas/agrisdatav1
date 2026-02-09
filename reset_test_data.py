import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.db import transaction
from decimal import Decimal

from empresas.models import Empresa
from compras.models import (
    SolicitacaoCompra,
    ItemSolicitacaoCompra,
    Cotacao,
    ItemCotacao,
    FornecedorCotacao,
    PedidoCompra,
    ItemPedidoCompra,
    RecebimentoCompra,
    ItemRecebimento,
    RecebimentoMensagem,
    SolicitacaoMensagem,
)
from estoque.models import (
    MovimentacaoEstoque,
    Lote,
    InventarioCiclico,
    InventarioCiclicoItem,
)
from produtos.models import Produto

empresa = Empresa.objects.first()
if not empresa:
    print('Nenhuma empresa encontrada. Operação cancelada.')
    raise SystemExit(1)

print(f'Empresa alvo: {empresa.nome} (ID {empresa.id})')

with transaction.atomic():
    # Compras - mensagens
    msgs_solic = SolicitacaoMensagem.objects.filter(solicitacao__empresa=empresa)
    msgs_receb = RecebimentoMensagem.objects.filter(recebimento__empresa=empresa)
    print(f'Mensagens solicitação: {msgs_solic.count()}')
    print(f'Mensagens recebimento: {msgs_receb.count()}')
    msgs_solic.delete()
    msgs_receb.delete()

    # Compras - itens dependentes
    itens_receb = ItemRecebimento.objects.filter(recebimento__empresa=empresa)
    print(f'Itens recebimento: {itens_receb.count()}')
    itens_receb.delete()

    # Compras - itens principais (ordem para respeitar PROTECT)
    itens_ped = ItemPedidoCompra.objects.filter(pedido__empresa=empresa)
    print(f'Itens pedido: {itens_ped.count()}')
    itens_ped.delete()

    propostas = FornecedorCotacao.objects.filter(item_cotacao__cotacao__empresa=empresa)
    print(f'Propostas cotação: {propostas.count()}')
    propostas.delete()

    itens_cot = ItemCotacao.objects.filter(cotacao__empresa=empresa)
    itens_sol = ItemSolicitacaoCompra.objects.filter(solicitacao__empresa=empresa)
    print(f'Itens cotação: {itens_cot.count()}')
    print(f'Itens solicitação: {itens_sol.count()}')
    itens_cot.delete()
    itens_sol.delete()

    # Compras - principais
    cotacoes = Cotacao.objects.filter(empresa=empresa)
    pedidos = PedidoCompra.objects.filter(empresa=empresa)
    recebimentos = RecebimentoCompra.objects.filter(empresa=empresa)
    solicitacoes = SolicitacaoCompra.objects.filter(empresa=empresa)
    print(f'Cotações: {cotacoes.count()}')
    print(f'Pedidos: {pedidos.count()}')
    print(f'Recebimentos: {recebimentos.count()}')
    print(f'Solicitações: {solicitacoes.count()}')
    recebimentos.delete()
    pedidos.delete()
    cotacoes.delete()
    solicitacoes.delete()

    # Estoque - inventários
    inv_itens = InventarioCiclicoItem.objects.filter(inventario__empresa=empresa)
    invs = InventarioCiclico.objects.filter(empresa=empresa)
    print(f'Itens inventário: {inv_itens.count()}')
    print(f'Inventários: {invs.count()}')
    inv_itens.delete()
    invs.delete()

    # Estoque - movimentações e lotes
    movs = MovimentacaoEstoque.objects.filter(empresa=empresa)
    lotes = Lote.objects.filter(empresa=empresa)
    print(f'Movimentações estoque: {movs.count()}')
    print(f'Lotes: {lotes.count()}')
    movs.delete()
    lotes.delete()

    # Zera estoque atual em produtos
    total_produtos = Produto.objects.update(estoque_atual=Decimal('0'))
    print(f'Produtos atualizados (estoque_atual=0): {total_produtos}')

print('RESET FINALIZADO COM SUCESSO.')
