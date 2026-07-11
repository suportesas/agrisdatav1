# -*- coding: utf-8 -*-
"""
Faturamento de recebimentos de compra.

As views de "Modo Simples" (compra_rapida, pedido_edit, recebimento_rapido,
escolher_modo_compra) que viviam neste arquivo foram removidas — a criação de
pedidos/recebimentos sem passar pela cadeia formal (Solicitação → Cotação →
Pedido → Recebimento) agora é feita pelos atalhos permissionados em
compras/views.py (pedido_direto_create) e compras/views_alertas.py (Central
de Alertas de Estoque Mínimo), que preservam a rastreabilidade completa.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from decimal import Decimal

from .models import RecebimentoCompra


@login_required
@transaction.atomic
def faturar_recebimento(request, recebimento_pk):
    """
    Registra a Nota Fiscal do recebimento e cria automaticamente
    a ContaPagar no módulo financeiro com parcelas profissionais.

    Fluxo:
    1. Usuário registra número da NF, série, valor e número de parcelas
    2. Sistema calcula automaticamente valor e datas de cada parcela
    3. Usuário seleciona forma de pagamento para cada parcela (Boleto, PIX, etc)
    4. Sistema cria ContaPagar vinculada à empresa
    5. Sistema cria ParcelaContaPagar com forma de pagamento
    6. Redireciona para detalhe da conta a pagar
    """
    from financeiro.models import ContaPagar, ParcelaContaPagar, FormaPagemento

    recebimento = get_object_or_404(
        RecebimentoCompra,
        pk=recebimento_pk,
        empresa=request.user.empresa
    )

    # Garante que o recebimento está em estado válido para faturamento
    if recebimento.status not in ['CONFERIDO', 'PENDENTE', 'FINALIZADO']:
        messages.error(request, f'Recebimento {recebimento.numero} não está pronto para faturar.')
        return redirect('compras:recebimento_detail', pk=recebimento.pk)

    # Se já está FINALIZADO, só permite se ainda não tem ContaPagar (recuperação de falha anterior)
    if recebimento.status == 'FINALIZADO':
        if ContaPagar.objects.filter(recebimento=recebimento).exists():
            messages.error(request, f'Recebimento {recebimento.numero} já foi faturado.')
            return redirect('compras:recebimento_detail', pk=recebimento.pk)

    if request.method == 'GET':
        # Pré-preencher com dados já salvos se existir
        dados_nf = {
            'numero_nf': recebimento.nota_fiscal,
            'serie': recebimento.serie_nota,
            'data_emissao': recebimento.data_emissao_nf,
            'valor_nf': recebimento.valor_total_nf,
        }

        formas_pagamento = FormaPagemento.objects.filter(ativo=True).order_by('ordem_exibicao')

        context = {
            'recebimento': recebimento,
            'dados_nf': dados_nf,
            'formas_pagamento': formas_pagamento,
            'parcelas_padrao': [
                {'valor': 1, 'label': '1x (à vista)', 'dias': [0]},
                {'valor': 2, 'label': '2x (30 dias)', 'dias': [0, 30]},
                {'valor': 3, 'label': '3x (30 dias)', 'dias': [0, 30, 60]},
                {'valor': 4, 'label': '4x (30 dias)', 'dias': [0, 30, 60, 90]},
            ]
        }
        return render(request, 'compras/faturar_recebimento.html', context)

    # POST - Registra a NF e cria ContaPagar
    try:
        numero_nf = request.POST.get('numero_nf')
        serie_nf = request.POST.get('serie', '1')
        data_emissao = request.POST.get('data_emissao')
        valor_nf = Decimal(request.POST.get('valor_nf', '0'))
        num_parcelas = int(request.POST.get('num_parcelas', '1'))
        juros = Decimal(request.POST.get('juros', '0'))
        multa = Decimal(request.POST.get('multa', '0'))
        desconto = Decimal(request.POST.get('desconto', '0'))

        if not all([numero_nf, data_emissao, valor_nf]):
            messages.error(request, 'Preencha todos os campos obrigatórios.')
            return redirect('compras:faturar_recebimento', recebimento_pk=recebimento.pk)

        if valor_nf <= 0:
            messages.error(request, 'O valor da NF deve ser maior que zero.')
            return redirect('compras:faturar_recebimento', recebimento_pk=recebimento.pk)

        # Determinar fornecedor antes de iniciar a transação
        fornecedor = recebimento.pedido.fornecedor if recebimento.pedido else recebimento.fornecedor
        if not fornecedor:
            messages.error(request, 'Recebimento não possui fornecedor vinculado.')
            return redirect('compras:faturar_recebimento', recebimento_pk=recebimento.pk)

        # Ler arrays de parcelas enviados pelo frontend
        from datetime import datetime as dt
        vencimentos      = request.POST.getlist('vencimentos[]')
        valores_parcelas = request.POST.getlist('valores_parcelas[]')
        formas_pgto      = request.POST.getlist('formas_pagamento[]')

        if not vencimentos:
            messages.error(request, 'Adicione pelo menos uma parcela.')
            return redirect('compras:faturar_recebimento', recebimento_pk=recebimento.pk)

        # valor_final = soma das parcelas definidas pelo usuário
        valor_final = sum(Decimal(v or '0') for v in valores_parcelas)

        with transaction.atomic():
            # Atualizar dados da NF no recebimento
            recebimento.nota_fiscal = numero_nf
            recebimento.serie_nota = serie_nf
            recebimento.valor_total_nf = valor_nf
            recebimento.status = 'FINALIZADO'
            recebimento.save()

            # Criar ContaPagar
            conta = ContaPagar.objects.create(
                recebimento=recebimento,
                empresa=request.user.empresa,
                fornecedor=fornecedor,
                numero=f"NF-{numero_nf}",
                valor_total=valor_final,
                valor_ajustado=valor_final,
                desconto_negociado=desconto,
                data_emissao=data_emissao,
                requer_aprovacao=True,
                observacoes=f"Gerada automaticamente do recebimento {recebimento.numero}\nNF: {numero_nf} - Série: {serie_nf}"
            )

            # Criar parcelas com datas e valores definidos pelo usuário
            for i, (venc_str, valor_str, forma_id) in enumerate(
                    zip(vencimentos, valores_parcelas, formas_pgto), start=1):
                valor_calc = Decimal(valor_str or '0')
                data_vencimento = dt.strptime(venc_str, '%Y-%m-%d').date()
                forma_pagamento = None
                if forma_id:
                    try:
                        forma_pagamento = FormaPagemento.objects.get(pk=forma_id)
                    except FormaPagemento.DoesNotExist:
                        pass
                ParcelaContaPagar.objects.create(
                    conta_pagar=conta,
                    numero_parcela=i,
                    forma_pagamento=forma_pagamento,
                    valor_parcela=valor_calc,
                    valor_total_parcela=valor_calc,
                    data_vencimento=data_vencimento,
                    status='ABERTA'
                )

        messages.success(
            request,
            f'✅ Conta a Pagar criada com sucesso!\n'
            f'NF: {numero_nf} | Fornecedor: {fornecedor.nome}\n'
            f'Valor: R$ {valor_final:,.2f} em {len(vencimentos)}x'
        )

        return redirect('financeiro:conta_pagar_detail', pk=conta.id)

    except Exception as e:
        messages.error(request, f'Erro ao faturar: {str(e)}')
        return redirect('compras:faturar_recebimento', recebimento_pk=recebimento.pk)
