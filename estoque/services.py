from estoque.models import MovimentacaoEstoque


def criar_movimentacao(
    empresa,
    tipo,
    origem,
    quantidade,
    usuario,
    lote=None,
    produto=None,
    armazem_origem=None,
    documento='',
    observacao='',
):
    """Cria e executa uma MovimentacaoEstoque, atualizando de fato o saldo do lote/produto.

    `MovimentacaoEstoque.objects.create(status='EXECUTADO')` grava só o registro de
    auditoria — quem realmente decrementa/incrementa `Lote.quantidade_atual` é
    `_atualizar_estoque()`, chamado apenas por `.executar(usuario)` (ver
    `MovimentacaoEstoque.executar`/`_atualizar_estoque`). Por isso esta função sempre
    cria em PENDENTE e executa em seguida, em vez de criar direto em EXECUTADO.
    """
    movimentacao = MovimentacaoEstoque.objects.create(
        empresa=empresa,
        produto=produto,
        lote=lote,
        tipo=tipo,
        origem=origem,
        quantidade=quantidade,
        armazem_origem=armazem_origem,
        documento=documento,
        observacao=observacao,
        status='PENDENTE',
        cadastrado_por=usuario,
    )
    movimentacao.executar(usuario)
    return movimentacao
