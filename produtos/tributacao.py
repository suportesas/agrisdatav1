"""
Resolução automática de CFOP/tributação para itens de venda.

Dado um produto, a empresa (emissor) e o cliente/tipo de venda (destino),
determina qual ProdutoTributacao cadastrada no produto deve ser usada —
sem depender de o usuário digitar CFOP/NCM manualmente no item do pedido.
"""
from dataclasses import dataclass
from typing import Optional

FAMILIA_LABELS = {
    '5': 'dentro do estado',
    '6': 'fora do estado',
    '7': 'exportação',
}


@dataclass
class ResultadoTributacao:
    ok: bool
    tributacao: Optional[object] = None
    ncm_codigo: str = ''
    cfop_codigo: str = ''
    mensagem: str = ''
    cfop_familia: str = ''
    produto_id: Optional[int] = None


def resolver_tributacao_venda(produto, empresa, cliente, tipo_venda):
    """Resolve a ProdutoTributacao aplicável a uma venda de `produto` de
    `empresa` para `cliente`, dado `tipo_venda` ('MERCADO_INTERNO' ou
    'EXPORTACAO'). Nunca adivinha: se não houver tributação cadastrada para
    a operação (ou houver ambiguidade), retorna ok=False com uma mensagem
    explicando o que falta cadastrar."""
    if not empresa.uf:
        return ResultadoTributacao(
            ok=False,
            mensagem='Empresa sem UF cadastrada — configure o endereço da empresa antes de vender.',
        )

    if tipo_venda == 'EXPORTACAO':
        familia = '7'
    else:
        uf_cliente = cliente.uf_fiscal() if cliente else None
        if uf_cliente is None:
            return ResultadoTributacao(
                ok=False,
                mensagem='Cliente sem UF cadastrada (nenhum endereço padrão definido).',
            )
        if uf_cliente == 'EX':
            return ResultadoTributacao(
                ok=False,
                mensagem='Tipo de venda é Mercado Interno, mas o cliente está cadastrado como '
                         'exterior/importador — revise o tipo de venda ou o cadastro do cliente.',
            )
        familia = '5' if uf_cliente == empresa.uf else '6'

    candidatos = list(
        produto.tributacoes.select_related('cfop').filter(ativo=True, cfop__codigo__startswith=familia)
    )

    if not candidatos:
        rotulo = FAMILIA_LABELS[familia]
        return ResultadoTributacao(
            ok=False,
            mensagem=f'Produto "{produto.nome}" não tem tributação cadastrada para venda {rotulo} '
                     f'(CFOP {familia}xxx).',
            cfop_familia=familia,
            produto_id=produto.pk,
        )

    if len(candidatos) > 1:
        padrao = [c for c in candidatos if c.padrao]
        if len(padrao) != 1:
            rotulo = FAMILIA_LABELS[familia]
            return ResultadoTributacao(
                ok=False,
                mensagem=f'Produto "{produto.nome}" tem mais de uma tributação cadastrada para venda '
                         f'{rotulo} (CFOP {familia}xxx) — marque uma delas como padrão.',
                cfop_familia=familia,
                produto_id=produto.pk,
            )
        escolhido = padrao[0]
    else:
        escolhido = candidatos[0]

    return ResultadoTributacao(
        ok=True,
        tributacao=escolhido,
        ncm_codigo=produto.ncm.codigo,
        cfop_codigo=escolhido.cfop.codigo,
        cfop_familia=familia,
        produto_id=produto.pk,
    )
