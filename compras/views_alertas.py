"""Geração de Solicitação de Compra em lote a partir dos Alertas de Estoque.

Ação disparada pelo Relatório de Alertas de Estoque (estoque:relatorio_alertas_estoque):
permite ao comprador (com permissão) selecionar em lote produtos críticos e
gerar, de uma vez, uma SolicitacaoCompra (origem=ESTOQUE_MINIMO) já aprovada,
pulando o preenchimento manual do almoxarifado — sem perder a rastreabilidade
da cadeia formal (a cotação segue sendo criada normalmente via
compras:cotacao_create).
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.utils import timezone

from produtos.models import Produto
from .models import SolicitacaoCompra, ItemSolicitacaoCompra
from empresas.acesso import programa_required


@programa_required('compras:central_alertas_gerar_solicitacao')
@transaction.atomic
def central_alertas_gerar_solicitacao(request):
    """Gera 1 SolicitacaoCompra (origem=ESTOQUE_MINIMO) com os produtos selecionados em lote."""
    if request.method != 'POST':
        return redirect('estoque:relatorio_alertas_estoque')

    empresa = request.user.empresa
    produtos_ids = request.POST.getlist('produto_id[]')
    if not produtos_ids:
        messages.warning(request, 'Selecione ao menos um produto.')
        return redirect('estoque:relatorio_alertas_estoque')

    solicitacao = SolicitacaoCompra.objects.create(
        empresa=empresa,
        solicitante=request.user,
        status='APROVADA',
        aprovador=request.user,
        data_aprovacao=timezone.now(),
        data_necessidade=timezone.now().date() + timedelta(days=7),
        justificativa='Gerado automaticamente pelo Relatório de Alertas de Estoque.',
        origem='ESTOQUE_MINIMO',
    )

    total_itens = 0
    for produto_id in produtos_ids:
        produto = Produto.objects.get(id=produto_id, categoria__empresa=empresa)

        try:
            quantidade = Decimal(request.POST.get(f'quantidade_{produto_id}', ''))
        except (TypeError, InvalidOperation):
            quantidade = None
        if not quantidade or quantidade <= 0:
            quantidade = max(produto.estoque_minimo - produto.calcular_saldo_real(), Decimal('1'))

        ItemSolicitacaoCompra.objects.create(
            solicitacao=solicitacao,
            produto=produto,
            quantidade=quantidade,
            unidade_medida=produto.unidade_medida,
            status_item='SELECIONADO',
            selecionado_para_cotar=True,
        )
        total_itens += 1

    messages.success(
        request,
        f'Solicitação {solicitacao.numero} gerada com {total_itens} item(ns). Prossiga para a cotação.'
    )
    return redirect('compras:cotacao_create', solicitacao_pk=solicitacao.pk)
