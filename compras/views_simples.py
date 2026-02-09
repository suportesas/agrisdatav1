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
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    # Verifica se modo simples está habilitado
    if not config.modo_simples_ativo():
        messages.warning(request, 'Modo simples não está habilitado. Use o fluxo formal.')
        return redirect('compras:solicitacao_create')
    
    fornecedores = Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True)
    produtos = Produto.objects.filter(ativo=True).select_related('categoria', 'unidade_medida')
    
    if request.method == 'POST':
        try:
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
                
                if not produtos_ids:
                    messages.error(request, 'Adicione pelo menos um produto')
                    return redirect('compras:compra_rapida')
                
                # Criar pedido
                from ..models import gerar_numero_pedido
                pedido = PedidoCompra.objects.create(
                    empresa=request.user.empresa,
                    numero=gerar_numero_pedido(request.user.empresa),
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
                for prod_id, qtd, preco in zip(produtos_ids, quantidades, precos):
                    if not prod_id or not qtd or not preco:
                        continue
                    
                    produto = Produto.objects.get(pk=prod_id)
                    quantidade = Decimal(qtd)
                    preco_unit = Decimal(preco)
                    preco_tot = quantidade * preco_unit
                    
                    ItemPedidoCompra.objects.create(
                        pedido=pedido,
                        produto=produto,
                        quantidade_pedida=quantidade,
                        unidade_medida=produto.unidade_medida,
                        preco_unitario=preco_unit,
                        preco_total=preco_tot,
                        proposta_fornecedor=None  # Sem proposta no modo simples
                    )
                    valor_total += preco_tot
                
                messages.success(
                    request,
                    f'Pedido {pedido.numero} criado com sucesso! Valor: R$ {valor_total:,.2f}'
                )
                
                # Redireciona para recebimento se configurado
                if config.permitir_recebimento_sem_pedido:
                    messages.info(request, 'Agora você pode registrar o recebimento')
                    return redirect('compras:recebimento_rapido', pedido_pk=pedido.pk)
                
                return redirect('compras:pedido_detail', pk=pedido.pk)
                
        except Exception as e:
            messages.error(request, f'Erro ao criar pedido: {str(e)}')
            return redirect('compras:compra_rapida')
    
    context = {
        'fornecedores': fornecedores,
        'produtos': produtos,
        'config': config,
    }
    return render(request, 'compras/compra_rapida.html', context)


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
                
                # Criar recebimento
                from ..models import gerar_numero_recebimento
                recebimento = RecebimentoCompra.objects.create(
                    empresa=request.user.empresa,
                    numero=gerar_numero_recebimento(request.user.empresa),
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
        'armazens': armazens,
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
