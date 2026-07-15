# -*- coding: utf-8 -*-
"""
Views Simplificadas para Estoque
Modo Simples: Entrada/Saída direta sem complexidade
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from core.models_config import ConfiguracaoSistema
from produtos.models import Produto
from cadastros.models import Fornecedor
from .models import (
    LocalEstocagem, Lote, MovimentacaoEstoque, Armazem
)


@login_required
def entrada_rapida(request):
    """
    Entrada rápida no estoque (Modo Simples)
    - Seleciona produtos e quantidades
    - Cria lote automaticamente
    - Dá entrada direta no estoque
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    # Verifica se modo simples está ativo
    if not config.modo_estoque_simples_ativo():
        messages.error(request, 'Modo de entrada rápida não está habilitado. Use o fluxo formal.')
        return redirect('estoque:movimentacao_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Dados gerais
                local_id = request.POST.get('local_estocagem')
                fornecedor_id = request.POST.get('fornecedor')
                nota_fiscal = request.POST.get('nota_fiscal', '')
                observacao = request.POST.get('observacao', '')
                
                local = get_object_or_404(LocalEstocagem, pk=local_id, armazem__empresa=request.user.empresa)
                fornecedor = None
                if fornecedor_id:
                    fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id, empresa=request.user.empresa)
                
                # Processar produtos
                produtos_ids = request.POST.getlist('produto_id')
                quantidades = request.POST.getlist('quantidade')
                precos = request.POST.getlist('preco_unitario')
                
                total_itens = 0
                for produto_id, quantidade, preco in zip(produtos_ids, quantidades, precos):
                    if not produto_id or not quantidade:
                        continue
                    
                    produto = get_object_or_404(Produto, pk=produto_id, categoria__empresa=request.user.empresa)
                    qtd = Decimal(quantidade)
                    preco_unit = Decimal(preco) if preco else Decimal('0.00')
                    
                    # Criar lote automaticamente se configurado
                    if config.gerar_lote_automatico:
                        numero_lote = gerar_numero_lote(produto)
                    else:
                        numero_lote = request.POST.get(f'lote_{produto_id}', gerar_numero_lote(produto))
                    
                    # Buscar ou criar lote
                    lote, created = Lote.objects.get_or_create(
                        produto=produto,
                        numero_lote=numero_lote,
                        armazem=local,
                        defaults={
                            'empresa': request.user.empresa,
                            'unidade_medida': produto.unidade_medida,
                            'data_fabricacao': timezone.now().date(),
                            'quantidade_inicial': qtd,
                            'quantidade_atual': qtd,
                            'valor_unitario': preco_unit if preco_unit > 0 else None,
                        }
                    )

                    if not created:
                        # Lote já existe, atualiza quantidade e custo do lote
                        lote.quantidade_atual += qtd
                        if preco_unit and preco_unit > 0:
                            lote.valor_unitario = preco_unit
                        lote.save()

                    # Criar movimentação de entrada
                    MovimentacaoEstoque.objects.create(
                        empresa=request.user.empresa,
                        tipo='ENTRADA',
                        origem='COMPRA',
                        produto=produto,
                        lote=lote,
                        quantidade=qtd,
                        data_movimentacao=timezone.now()
                    )

                    total_itens += 1
                
                messages.success(
                    request,
                    f'✅ Entrada realizada com sucesso! {total_itens} produto(s) adicionado(s) ao estoque.'
                )
                return redirect('estoque:movimentacao_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao processar entrada: {str(e)}')
    
    # GET - Renderizar formulário
    context = {
        'config': config,
        'produtos': Produto.objects.filter(
            categoria__empresa=request.user.empresa,
            ativo=True
        ).select_related('categoria', 'unidade_compra'),
        'locais': LocalEstocagem.objects.filter(armazem__empresa=request.user.empresa, ativo=True),
        'fornecedores': Fornecedor.objects.filter(empresa=request.user.empresa, ativa=True),
    }
    
    return render(request, 'estoque/entrada_rapida.html', context)


@login_required
def saida_rapida(request):
    """
    Saída rápida do estoque (Modo Simples)
    - Seleciona produtos e quantidades
    - Baixa automaticamente dos lotes disponíveis
    - FIFO automático
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    if not config.modo_estoque_simples_ativo():
        messages.error(request, 'Modo de saída rápida não está habilitado.')
        return redirect('estoque:movimentacao_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Dados gerais
                local_id = request.POST.get('local_estocagem')
                motivo = request.POST.get('motivo', 'Saída manual')
                observacao = request.POST.get('observacao', '')
                
                local = get_object_or_404(LocalEstocagem, pk=local_id, armazem__empresa=request.user.empresa)
                
                # Processar produtos
                produtos_ids = request.POST.getlist('produto_id')
                quantidades = request.POST.getlist('quantidade')
                
                total_itens = 0
                for produto_id, quantidade in zip(produtos_ids, quantidades):
                    if not produto_id or not quantidade:
                        continue
                    
                    produto = get_object_or_404(Produto, pk=produto_id, categoria__empresa=request.user.empresa)
                    qtd_solicitada = Decimal(quantidade)
                    
                    # Buscar lotes disponíveis (FIFO - First In, First Out)
                    lotes_disponiveis = Lote.objects.filter(
                        produto=produto,
                        armazem=local,
                        quantidade_atual__gt=0
                    ).order_by('data_fabricacao')
                    
                    # Verificar estoque disponível
                    estoque_disponivel = sum(lote.quantidade_atual for lote in lotes_disponiveis)
                    
                    if estoque_disponivel < qtd_solicitada and not config.permitir_estoque_negativo:
                        messages.error(
                            request,
                            f'❌ Estoque insuficiente para {produto.descricao}. '
                            f'Disponível: {estoque_disponivel} {produto.unidade_compra.sigla}'
                        )
                        raise Exception('Estoque insuficiente')
                    
                    # Baixar dos lotes (FIFO)
                    qtd_restante = qtd_solicitada
                    
                    for lote in lotes_disponiveis:
                        if qtd_restante <= 0:
                            break
                        
                        qtd_a_baixar = min(lote.quantidade_atual, qtd_restante)
                        
                        # Atualizar lote
                        lote.quantidade_atual -= qtd_a_baixar
                        lote.save()
                        
                        # Criar movimentação de saída
                        MovimentacaoEstoque.objects.create(
                            empresa=request.user.empresa,
                            tipo='SAIDA',
                            origem='VENDA',
                            produto=produto,
                            lote=lote,
                            quantidade=-qtd_a_baixar,
                            data_movimentacao=timezone.now()
                        )
                        
                        qtd_restante -= qtd_a_baixar
                    
                    # Recalcula estoque_atual apos baixar dos lotes
                    produto.recalcular_estoque()

                    total_itens += 1
                
                messages.success(
                    request,
                    f'✅ Saída realizada com sucesso! {total_itens} produto(s) baixado(s) do estoque.'
                )
                return redirect('estoque:movimentacao_list')
                
        except Exception as e:
            messages.error(request, f'Erro ao processar saída: {str(e)}')
    
    # GET - Renderizar formulário
    context = {
        'config': config,
        'produtos': Produto.objects.filter(
            categoria__empresa=request.user.empresa,
            ativo=True
        ).select_related('categoria', 'unidade_compra'),
        'locais': LocalEstocagem.objects.filter(armazem__empresa=request.user.empresa, ativo=True),
    }
    
    return render(request, 'estoque/saida_rapida.html', context)


@login_required
def ajuste_rapido(request):
    """
    Ajuste rápido de estoque (Modo Simples)
    - Corrige quantidades diretamente
    - Útil para inventários e acertos
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    if not config.modo_estoque_simples_ativo():
        messages.error(request, 'Modo de ajuste rápido não está habilitado.')
        return redirect('estoque:movimentacao_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                produto_id = request.POST.get('produto_id')
                tipo_ajuste = request.POST.get('tipo_ajuste')
                quantidade = Decimal(request.POST.get('quantidade'))
                motivo = request.POST.get('motivo', 'Ajuste de inventário')
                
                # Buscar o produto
                produto = get_object_or_404(Produto, pk=produto_id, categoria__empresa=request.user.empresa)
                
                # Buscar lotes disponíveis do produto com quantidade > 0
                lotes = Lote.objects.filter(
                    produto=produto,
                    armazem__empresa=request.user.empresa,
                    quantidade_atual__gt=0
                ).order_by('data_fabricacao')

                # Processar o ajuste
                if tipo_ajuste == 'ENTRADA':
                    lote = lotes.first()
                    if not lote:
                        # Sem lotes com qty > 0: cria lote de ajuste
                        armazem = Armazem.objects.filter(empresa=request.user.empresa).first()
                        if not armazem:
                            raise Exception('Nenhum armazém configurado para a empresa.')
                        numero_lote = f"ADJ-{produto.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
                        lote = Lote.objects.create(
                            empresa=request.user.empresa,
                            produto=produto,
                            numero_lote=numero_lote,
                            armazem=armazem,
                            data_fabricacao=timezone.now().date(),
                            quantidade_inicial=quantidade,
                            quantidade_atual=quantidade,
                        )
                    else:
                        lote.quantidade_atual += quantidade
                        lote.save()

                    MovimentacaoEstoque.objects.create(
                        empresa=request.user.empresa,
                        tipo='AJUSTE',
                        origem='AJUSTE_ENTRADA',
                        produto=produto,
                        lote=lote,
                        armazem_origem=lote.armazem,
                        quantidade=quantidade,
                        observacao=motivo,
                        status='EXECUTADO',
                        executado_por=request.user,
                        data_movimentacao=timezone.now(),
                    )

                    messages.success(
                        request,
                        f'✅ Entrada de ajuste realizada! {produto.descricao} + {quantidade}'
                    )

                else:  # SAIDA
                    if not lotes.exists():
                        messages.error(request, f'Nenhum lote disponível para {produto.descricao}')
                        raise Exception('Sem lotes disponíveis')

                    estoque_disponivel = sum(l.quantidade_atual for l in lotes)
                    if estoque_disponivel < quantidade and not config.permitir_estoque_negativo:
                        messages.error(
                            request,
                            f'❌ Estoque insuficiente para {produto.descricao}. '
                            f'Disponível: {estoque_disponivel}'
                        )
                        raise Exception('Estoque insuficiente')

                    # Saída: remove dos lotes (FIFO)
                    qtd_restante = quantidade
                    for lote in lotes:
                        if qtd_restante <= 0:
                            break

                        qtd_a_baixar = min(lote.quantidade_atual, qtd_restante)
                        lote.quantidade_atual -= qtd_a_baixar
                        lote.save()

                        MovimentacaoEstoque.objects.create(
                            empresa=request.user.empresa,
                            tipo='AJUSTE',
                            origem='AJUSTE_SAIDA',
                            produto=produto,
                            lote=lote,
                            armazem_origem=lote.armazem,
                            quantidade=qtd_a_baixar,
                            observacao=motivo,
                            status='EXECUTADO',
                            executado_por=request.user,
                            data_movimentacao=timezone.now(),
                        )

                        qtd_restante -= qtd_a_baixar

                    messages.success(
                        request,
                        f'✅ Saída de ajuste realizada! {produto.descricao} - {quantidade}'
                    )

                # Recalcula estoque_atual do produto
                produto.recalcular_estoque()
                
                return redirect('estoque:ajuste_rapido')
                
        except Exception as e:
            messages.error(request, f'Erro ao processar ajuste: {str(e)}')
    
    # GET - Renderizar formulário
    context = {
        'config': config,
        'produtos': Produto.objects.filter(
            categoria__empresa=request.user.empresa,
            ativo=True
        ).select_related('categoria', 'unidade_compra'),
    }
    
    return render(request, 'estoque/ajuste_rapido.html', context)


@login_required
def escolher_modo_estoque(request):
    """
    Tela de escolha entre modo simples e formal (quando configurado como HÍBRIDO)
    """
    config = ConfiguracaoSistema.get_config(request.user.empresa)
    
    if config.modo_estoque != 'HIBRIDO':
        # Redirecionar automaticamente baseado no modo
        if config.modo_estoque == 'SIMPLES':
            return redirect('estoque:entrada_rapida')
        else:
            return redirect('estoque:movimentacao_create')
    
    context = {
        'config': config,
    }
    
    return render(request, 'estoque/escolher_modo.html', context)


def gerar_numero_lote(produto):
    """
    Gera número de lote automático
    Formato: PROD-YYYYMMDD-XXXX
    """
    from datetime import datetime
    
    hoje = datetime.now().strftime('%Y%m%d')
    prefixo = produto.codigo[:4].upper() if produto.codigo else 'PROD'
    
    # Buscar último lote do dia para este produto
    ultimo_lote = Lote.objects.filter(
        produto=produto,
        numero_lote__startswith=f'{prefixo}-{hoje}'
    ).order_by('-numero_lote').first()
    
    if ultimo_lote:
        # Extrair sequencial
        try:
            seq = int(ultimo_lote.numero_lote.split('-')[-1]) + 1
        except:
            seq = 1
    else:
        seq = 1
    
    return f'{prefixo}-{hoje}-{seq:04d}'
