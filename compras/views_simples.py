# -*- coding: utf-8 -*-
"""
Views para Fluxo Simples de Compras
Processo otimizado: Pedido Rápido → Recebimento → Estoque
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from cadastros.models import Fornecedor
from produtos.models import Produto
from estoque.models import Armazem, LocalEstocagem
from core.models_config import ConfiguracaoSistema
from .models import PedidoCompra, ItemPedidoCompra, RecebimentoCompra, ItemRecebimento


@login_required
def compra_rapida(request):
    """
    Tela de compra rápida - estilo "carrinho de compras"
    Permite adicionar produtos, definir fornecedor e criar pedido em 1 tela
    Também lista pedidos recentes para editar/excluir
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    # Verifica se modo simples está habilitado
    if not config.modo_simples_ativo():
        messages.warning(request, 'Modo simples não está habilitado. Use o fluxo formal.')
        return redirect('compras:solicitacao_create')
    
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True)
    produtos = Produto.objects.filter(ativo=True).select_related('categoria', 'unidade_medida')
    
    # Listar pedidos recentes (últimos 10 dias) que não foram recebidos
    pedidos_recentes = PedidoCompra.objects.filter(
        empresa=request.user.empresa,
        status__in=['PENDENTE_RECEBIMENTO', 'ADICIONANDO_ITENS']
    ).order_by('-data_pedido')[:20]
    
    if request.method == 'POST':
        try:
            # Verificar se é uma ação de exclusão
            action = request.POST.get('action')
            if action == 'delete':
                pedido_id = request.POST.get('pedido_id')
                pedido = get_object_or_404(
                    PedidoCompra,
                    pk=pedido_id,
                    empresa=request.user.empresa,
                    status__in=['PENDENTE_RECEBIMENTO', 'ADICIONANDO_ITENS']
                )
                numero_pedido = pedido.numero
                pedido.delete()
                messages.success(request, f'✅ Pedido {numero_pedido} excluído com sucesso!')
                return redirect('compras:compra_rapida')
            
            with transaction.atomic():
                # Validações básicas
                fornecedor_id = request.POST.get('fornecedor')
                if not fornecedor_id:
                    messages.error(request, 'Selecione um fornecedor')
                    return redirect('compras:compra_rapida')
                
                fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id, empresa=request.user.empresa)
                
                # Coletar itens
                produtos_ids = request.POST.getlist('produto_id[]')
                quantidades = request.POST.getlist('quantidade[]')
                precos = request.POST.getlist('preco[]')
                descontos = request.POST.getlist('desconto[]')

                if not produtos_ids:
                    messages.error(request, 'Adicione pelo menos um produto')
                    return redirect('compras:compra_rapida')

                # Criar pedido (número é gerado automaticamente no model)
                pedido = PedidoCompra.objects.create(
                    empresa=request.user.empresa,
                    fornecedor=fornecedor,
                    comprador=request.user,
                    data_pedido=timezone.now(),
                    data_entrega_prevista=timezone.now().date() + timezone.timedelta(days=7),
                    cotacao=None,  # Sem cotação no modo simples
                    status='PENDENTE_RECEBIMENTO',
                    observacoes=request.POST.get('observacoes', '')
                )

                # Adicionar itens
                valor_total = Decimal('0')
                for i, (prod_id, qtd, preco) in enumerate(zip(produtos_ids, quantidades, precos)):
                    if not prod_id or not qtd or not preco:
                        continue

                    desconto_str = descontos[i] if i < len(descontos) else '0'
                    produto = Produto.objects.get(pk=prod_id)
                    quantidade = Decimal(qtd)
                    preco_unit = Decimal(preco)
                    desconto   = max(Decimal('0'), Decimal(desconto_str or '0'))
                    preco_tot  = max(Decimal('0'), quantidade * preco_unit - desconto)

                    ItemPedidoCompra.objects.create(
                        pedido=pedido,
                        produto=produto,
                        quantidade_pedida=quantidade,
                        unidade_medida=produto.unidade_medida,
                        preco_unitario=preco_unit,
                        valor_desconto=desconto,
                        proposta_fornecedor=None  # Sem proposta no modo simples
                    )
                    valor_total += preco_tot

                pedido.calcular_total()

                limite_credito = fornecedor.limite_credito or Decimal('0')
                if limite_credito > 0 and valor_total > limite_credito:
                    messages.warning(
                        request,
                        (
                            f'⚠️ Alerta de crédito: o pedido {pedido.numero} (R$ {valor_total:,.2f}) '
                            f'ultrapassa o limite aprovado do fornecedor '
                            f'(R$ {limite_credito:,.2f}).'
                        )
                    )
                
                messages.success(
                    request,
                    f'Pedido {pedido.numero} criado com sucesso! Valor: R$ {valor_total:,.2f}'
                )
                
                # Redireciona para recebimento se configurado
                if config.permitir_recebimento_sem_pedido:
                    messages.info(request, 'Agora você pode registrar o recebimento')
                    return redirect('compras:recebimento_rapido_pedido', pedido_pk=pedido.pk)
                
                return redirect('compras:pedido_detail', pk=pedido.pk)
                
        except Exception as e:
            messages.error(request, f'Erro ao criar pedido: {str(e)}')
            return redirect('compras:compra_rapida')
    
    context = {
        'fornecedores': fornecedores,
        'produtos': produtos,
        'config': config,
        'pedidos_recentes': pedidos_recentes,
    }
    return render(request, 'compras/compra_rapida.html', context)


@login_required
def pedido_edit(request, pk):
    """
    Edita um pedido de compra criado no modo simples
    Permite modificar produtos, quantidades e preços
    """
    pedido = get_object_or_404(
        PedidoCompra,
        pk=pk,
        empresa=request.user.empresa,
        status__in=['PENDENTE_RECEBIMENTO', 'ADICIONANDO_ITENS']
    )
    
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True)
    produtos = Produto.objects.filter(ativo=True).select_related('categoria', 'unidade_medida')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Atualizar informações básicas
                fornecedor_id = request.POST.get('fornecedor')
                if not fornecedor_id:
                    messages.error(request, 'Selecione um fornecedor')
                    return redirect('compras:pedido_edit', pk=pedido.pk)
                
                fornecedor = get_object_or_404(
                    Fornecedor,
                    pk=fornecedor_id,
                    empresa=request.user.empresa,
                    ativa=True
                )
                
                pedido.fornecedor = fornecedor
                pedido.observacoes = request.POST.get('observacoes', '')
                pedido.save()
                
                # Coletar itens
                produtos_ids = request.POST.getlist('produto_id[]')
                quantidades  = request.POST.getlist('quantidade[]')
                precos       = request.POST.getlist('preco[]')
                descontos    = request.POST.getlist('desconto[]')
                item_ids     = request.POST.getlist('item_id[]')

                # Deletar itens removidos
                items_novos_ids = [iid for iid in item_ids if iid]
                ItemPedidoCompra.objects.filter(
                    pedido=pedido
                ).exclude(
                    id__in=items_novos_ids
                ).delete()

                # Atualizar ou criar itens
                valor_total = Decimal('0')
                for idx, (prod_id, qtd, preco, item_id) in enumerate(
                    zip(produtos_ids, quantidades, precos, item_ids)
                ):
                    if not prod_id or not qtd or not preco:
                        continue

                    desconto_str = descontos[idx] if idx < len(descontos) else '0'
                    produto    = get_object_or_404(Produto, pk=prod_id, ativo=True)
                    quantidade = Decimal(qtd)
                    preco_unit = Decimal(preco)
                    desconto   = max(Decimal('0'), Decimal(desconto_str or '0'))

                    if item_id:
                        item = ItemPedidoCompra.objects.get(pk=item_id, pedido=pedido)
                        item.quantidade_pedida = quantidade
                        item.preco_unitario    = preco_unit
                        item.valor_desconto    = desconto
                        item.save()
                    else:
                        ItemPedidoCompra.objects.create(
                            pedido=pedido,
                            produto=produto,
                            quantidade_pedida=quantidade,
                            unidade_medida=produto.unidade_medida,
                            preco_unitario=preco_unit,
                            valor_desconto=desconto,
                            proposta_fornecedor=None
                        )

                    valor_total += max(Decimal('0'), quantidade * preco_unit - desconto)
                
                pedido.calcular_total()
                
                messages.success(
                    request,
                    f'✅ Pedido {pedido.numero} atualizado com sucesso!'
                )
                return redirect('compras:pedido_detail', pk=pedido.pk)
                
        except Exception as e:
            messages.error(request, f'Erro ao atualizar pedido: {str(e)}')
            return redirect('compras:pedido_edit', pk=pedido.pk)
    
    context = {
        'pedido': pedido,
        'fornecedores': fornecedores,
        'produtos': produtos,
    }
    return render(request, 'compras/pedido_edit.html', context)


@login_required
def recebimento_rapido(request, pedido_pk=None):
    """
    Recebimento rápido - registra recebimento e já dá entrada no estoque
    Pode ser com ou sem pedido prévio
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    pedido = None
    if pedido_pk:
        pedido = get_object_or_404(PedidoCompra, pk=pedido_pk, empresa=request.user.empresa)
    
    armazens = Armazem.objects.filter(empresa=request.user.empresa, ativo=True)
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True)
    produtos = Produto.objects.filter(ativo=True)
    locais = LocalEstocagem.objects.filter(
        armazem__empresa=request.user.empresa, ativo=True
    ).select_related('armazem').order_by('armazem__nome', 'codigo')
    pedidos = PedidoCompra.objects.filter(
        empresa=request.user.empresa,
        status__in=['PENDENTE_RECEBIMENTO', 'ADICIONANDO_ITENS'],
    ).select_related('fornecedor').prefetch_related('itens').order_by('-data_pedido')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                fornecedor_id = request.POST.get('fornecedor')
                nota_fiscal = request.POST.get('nota_fiscal')
                data_emissao = request.POST.get('data_emissao')
                armazem_id = request.POST.get('armazem')
                
                if not all([fornecedor_id, nota_fiscal, armazem_id]):
                    messages.error(request, 'Preencha todos os campos obrigatórios')
                    return redirect(request.path)
                
                fornecedor = Fornecedor.objects.get(pk=fornecedor_id)
                armazem = Armazem.objects.get(pk=armazem_id)
                
                # Pegar primeiro local do armazém
                local_estoque = LocalEstocagem.objects.filter(armazem=armazem).first()
                if not local_estoque:
                    messages.error(request, f'Armazém {armazem.nome} não tem locais de estocagem cadastrados')
                    return redirect(request.path)
                
                # Criar recebimento (número é gerado automaticamente no model)
                recebimento = RecebimentoCompra.objects.create(
                    empresa=request.user.empresa,
                    pedido=pedido,
                    fornecedor=fornecedor,
                    nota_fiscal=nota_fiscal,
                    data_emissao_nf=data_emissao or timezone.now(),
                    data_recebimento=timezone.now(),
                    recebido_por=request.user,
                    valor_total_nf=Decimal(request.POST.get('valor_total', '0')),
                    status='CRIADO'
                )
                
                # Adicionar itens
                produtos_ids = request.POST.getlist('produto_id[]')
                quantidades = request.POST.getlist('quantidade[]')
                precos = request.POST.getlist('preco[]')
                
                for prod_id, qtd, preco in zip(produtos_ids, quantidades, precos):
                    if not all([prod_id, qtd, preco]):
                        continue
                    
                    produto = Produto.objects.get(pk=prod_id)
                    quantidade = Decimal(qtd)
                    preco_unit = Decimal(preco)
                    
                    item = ItemRecebimento.objects.create(
                        recebimento=recebimento,
                        item_pedido=None,  # Pode ser None
                        produto=produto,
                        quantidade_recebida=quantidade,
                        unidade_medida=produto.unidade_medida,
                        preco_unitario=preco_unit,
                        local_estoque=local_estoque
                    )
                    
                    # Entrada automática no estoque se configurado
                    if config.entrada_estoque_automatica:
                        item.registrar_movimento_estoque()
                
                # Finalizar automaticamente se entrada automática está ativa
                if config.entrada_estoque_automatica:
                    recebimento.status = 'FINALIZADO'
                    recebimento.save()
                    messages.success(
                        request,
                        f'Recebimento {recebimento.numero} criado e estoque atualizado automaticamente!'
                    )
                else:
                    recebimento.status = 'CONFERIDO'
                    recebimento.save()
                    messages.success(
                        request,
                        f'Recebimento {recebimento.numero} criado! Aguardando entrada no estoque.'
                    )
                
                return redirect('compras:recebimento_detail', pk=recebimento.pk)
                
        except Exception as e:
            messages.error(request, f'Erro ao criar recebimento: {str(e)}')
            import traceback
            traceback.print_exc()
            return redirect(request.path)
    
    context = {
        'pedido': pedido,
        'pedidos': pedidos,
        'armazens': armazens,
        'locais': locais,
        'fornecedores': fornecedores,
        'produtos': produtos,
        'config': config,
    }
    return render(request, 'compras/recebimento_rapido.html', context)


@login_required
def escolher_modo_compra(request):
    """
    Tela para escolher entre modo simples ou formal
    Apenas para modo HÍBRIDO
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    if config.modo_compras != 'HIBRIDO':
        # Redireciona direto para o modo configurado
        if config.modo_compras == 'SIMPLES':
            return redirect('compras:compra_rapida')
        else:
            return redirect('compras:solicitacao_create')
    
    context = {
        'config': config,
    }
    return render(request, 'compras/escolher_modo.html', context)


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
    from datetime import timedelta
    
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

        from django.db import transaction
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
