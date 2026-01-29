"""
Views para o Sistema de Cotações Inteligente
Busca automática de fornecedores por produto
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, Min, Max, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models_cotacao import (
    CotacaoInteligente, CotacaoInteligenteItem, CotacaoInteligenteFornecedor, 
    CotacaoInteligenteProposta, HistoricoPrecoFornecedor
)
from produtos.models import Produto, ProdutoFornecedor
from cadastros.models import Fornecedor


@login_required
def cotacao_list(request):
    """Lista todas as cotações"""
    empresa = request.user.empresa
    
    # Filtros
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    cotacoes = CotacaoInteligente.objects.filter(empresa=empresa)
    
    if status:
        cotacoes = cotacoes.filter(status=status)
    
    if search:
        cotacoes = cotacoes.filter(
            Q(numero__icontains=search) |
            Q(observacoes__icontains=search)
        )
    
    cotacoes = cotacoes.select_related('criado_por').prefetch_related('itens', 'propostas')
    
    # Card de cotações pendentes (EM_ANDAMENTO)
    cotacoes_pendentes = CotacaoInteligente.objects.filter(empresa=empresa, status='em_andamento').count()
    
    context = {
        'cotacoes': cotacoes,
        'status_filter': status,
        'search': search,
        'status_choices': CotacaoInteligente.STATUS_CHOICES,
        'cotacoes_pendentes': cotacoes_pendentes
    }
    
    return render(request, 'compras/cotacao/cotacao_list.html', context)


@login_required
def cotacao_create_step1(request):
    """Passo 1: Selecionar produtos para cotação"""
    empresa = request.user.empresa
    
    if request.method == 'POST':
        produtos_ids = request.POST.getlist('produtos')
        
        if not produtos_ids:
            messages.error(request, 'Selecione pelo menos um produto para cotar.')
            return redirect('compras:cotacao_create_step1')
        
        # Salvar na sessão e ir para próximo passo
        request.session['cotacao_produtos'] = produtos_ids
        return redirect('compras:cotacao_create_step2')
    
    # Buscar todos os produtos ativos (com ou sem fornecedores)
    produtos = Produto.objects.filter(
        categoria__empresa=empresa,
        ativo=True
    ).select_related(
        'categoria', 'subcategoria', 'unidade_medida'
    ).prefetch_related(
        'fornecedores_relacionados__fornecedor'
    ).annotate(
        total_fornecedores=Count('fornecedores_relacionados', filter=Q(fornecedores_relacionados__ativo=True))
    ).order_by('nome')
    
    # Filtro de busca
    search = request.GET.get('search', '')
    if search:
        produtos = produtos.filter(
            Q(nome__icontains=search) |
            Q(codigo__icontains=search)
        )
    
    context = {
        'produtos': produtos,
        'search': search,
    }
    
    return render(request, 'compras/cotacao/cotacao_create_step1.html', context)


@login_required
def cotacao_create_step2(request):
    """Passo 2: Buscar fornecedores automaticamente e definir quantidades"""
    empresa = request.user.empresa
    
    produtos_ids = request.session.get('cotacao_produtos', [])
    if not produtos_ids:
        messages.warning(request, 'Nenhum produto selecionado.')
        return redirect('compras:cotacao_create_step1')
    
    if request.method == 'POST':
        # Criar cotação
        numero = gerar_numero_cotacao(empresa)
        data_validade = request.POST.get('data_validade')
        observacoes = request.POST.get('observacoes', '')
        condicoes_pagamento = request.POST.get('condicoes_pagamento', '')
        prazo_entrega_desejado = request.POST.get('prazo_entrega_desejado') or None
        
        cotacao = CotacaoInteligente.objects.create(
            empresa=empresa,
            numero=numero,
            data_validade=data_validade,
            observacoes=observacoes,
            condicoes_pagamento=condicoes_pagamento,
            prazo_entrega_desejado=prazo_entrega_desejado,
            status='rascunho',
            criado_por=request.user
        )
        
        # Criar itens da cotação
        fornecedores_set = set()
        
        for produto_id in produtos_ids:
            quantidade = request.POST.get(f'quantidade_{produto_id}')
            especificacao = request.POST.get(f'especificacao_{produto_id}', '')
            
            if not quantidade or Decimal(quantidade) <= 0:
                continue
            
            produto = Produto.objects.get(pk=produto_id)
            
            # Buscar preço de referência (último preço pago)
            ultimo_historico = HistoricoPrecoFornecedor.objects.filter(
                produto=produto
            ).order_by('-data_cotacao').first()
            
            preco_referencia = ultimo_historico.preco_unitario if ultimo_historico else None
            
            item = CotacaoInteligenteItem.objects.create(
                cotacao=cotacao,
                produto=produto,
                quantidade=quantidade,
                unidade_medida=produto.unidade_medida,
                especificacao=especificacao,
                preco_referencia=preco_referencia
            )
            
            # Buscar fornecedores cadastrados para este produto
            fornecedores_produto = ProdutoFornecedor.objects.filter(
                produto=produto,
                ativo=True,
                fornecedor__ativa=True
            ).select_related('fornecedor')
            
            # Adicionar fornecedores selecionados
            fornecedores_selecionados = request.POST.getlist(f'fornecedores_{produto_id}')
            
            for pf in fornecedores_produto:
                if str(pf.fornecedor.id) in fornecedores_selecionados:
                    fornecedores_set.add(pf.fornecedor.id)
        
        # Criar relacionamentos com fornecedores
        for fornecedor_id in fornecedores_set:
            CotacaoInteligenteFornecedor.objects.create(
                cotacao=cotacao,
                fornecedor_id=fornecedor_id
            )
        
        # Limpar sessão
        del request.session['cotacao_produtos']
        
        messages.success(request, f'Cotação {numero} criada com sucesso!')
        return redirect('compras:cotacao_detail', pk=cotacao.pk)
    
    # GET - Exibir formulário
    produtos = Produto.objects.filter(
        pk__in=produtos_ids,
        categoria__empresa=empresa
    ).select_related(
        'categoria', 'subcategoria', 'unidade_medida'
    ).prefetch_related(
        'fornecedores_relacionados__fornecedor'
    )
    
    # Buscar TODOS os fornecedores ativos para seleção manual
    todos_fornecedores = Fornecedor.objects.filter(
        empresa=empresa,
        ativa=True
    ).order_by('nome')
    
    # Preparar dados dos produtos com fornecedores
    produtos_data = []
    for produto in produtos:
        fornecedores = produto.fornecedores_relacionados.filter(
            ativo=True,
            fornecedor__ativa=True
        ).select_related('fornecedor').order_by('-fornecedor_preferencial', 'fornecedor__nome')
        
        # Buscar último preço
        ultimo_historico = HistoricoPrecoFornecedor.objects.filter(
            produto=produto
        ).order_by('-data_cotacao').first()
        
        produtos_data.append({
            'produto': produto,
            'fornecedores': fornecedores,
            'ultimo_preco': ultimo_historico.preco_unitario if ultimo_historico else None,
            'ultima_data': ultimo_historico.data_cotacao if ultimo_historico else None,
        })
    
    # Data de validade padrão (15 dias)
    data_validade_padrao = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
    
    context = {
        'produtos_data': produtos_data,
        'data_validade_padrao': data_validade_padrao,
        'todos_fornecedores': todos_fornecedores,
    }
    
    return render(request, 'compras/cotacao/cotacao_create_step2.html', context)


@login_required
def cotacao_detail(request, pk):
    """Detalhes da cotação com comparação de propostas"""
    cotacao = get_object_or_404(CotacaoInteligente, pk=pk, empresa=request.user.empresa)
    
    # Itens com propostas agrupadas
    itens_data = []
    for item in cotacao.itens.all():
        propostas = item.propostas.all().select_related('fornecedor').order_by('preco_unitario')
        
        # Estatísticas de preços
        if propostas.exists():
            precos = [p.preco_unitario for p in propostas]
            menor_preco = min(precos)
            maior_preco = max(precos)
            preco_medio = sum(precos) / len(precos)
        else:
            menor_preco = maior_preco = preco_medio = None
        
        itens_data.append({
            'item': item,
            'propostas': propostas,
            'menor_preco': menor_preco,
            'maior_preco': maior_preco,
            'preco_medio': preco_medio,
        })
    
    # Fornecedores envolvidos
    fornecedores = cotacao.cotacao_fornecedores.all().select_related('fornecedor')
    
    context = {
        'cotacao': cotacao,
        'itens_data': itens_data,
        'fornecedores': fornecedores,
    }
    
    return render(request, 'compras/cotacao/cotacao_detail.html', context)


@login_required
def proposta_create(request, cotacao_pk, item_pk):
    """Adiciona proposta de fornecedor via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
    
    try:
        cotacao = get_object_or_404(CotacaoInteligente, pk=cotacao_pk, empresa=request.user.empresa)
        item = get_object_or_404(CotacaoInteligenteItem, pk=item_pk, cotacao=cotacao)
        
        data = json.loads(request.body)
        
        fornecedor_id = data.get('fornecedor_id')
        preco_unitario = Decimal(data.get('preco_unitario', 0))
        prazo_entrega = int(data.get('prazo_entrega', 0))
        
        if not fornecedor_id or preco_unitario <= 0:
            return JsonResponse({'success': False, 'error': 'Dados inválidos'}, status=400)
        
        fornecedor = get_object_or_404(Fornecedor, pk=fornecedor_id, empresa=request.user.empresa, ativa=True)
        
        # Criar ou atualizar proposta
        proposta, created = CotacaoInteligenteProposta.objects.update_or_create(
            cotacao=cotacao,
            item=item,
            fornecedor=fornecedor,
            defaults={
                'preco_unitario': preco_unitario,
                'prazo_entrega': prazo_entrega,
                'quantidade_minima': data.get('quantidade_minima') or None,
                'condicao_pagamento': data.get('condicao_pagamento', ''),
                'frete': Decimal(data.get('frete', 0)),
                'impostos': Decimal(data.get('impostos', 0)),
                'observacoes': data.get('observacoes', ''),
                'cadastrado_por': request.user
            }
        )
        
        # Registrar no histórico de preços
        HistoricoPrecoFornecedor.objects.create(
            produto=item.produto,
            fornecedor=fornecedor,
            preco_unitario=preco_unitario,
            quantidade=item.quantidade,
            data_cotacao=timezone.now().date(),
            cotacao=cotacao,
            prazo_entrega=prazo_entrega,
            condicao_pagamento=data.get('condicao_pagamento', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Proposta registrada com sucesso!',
            'created': created
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def proposta_selecionar(request, proposta_pk):
    """Seleciona a melhor proposta para um item"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)
    
    try:
        proposta = get_object_or_404(CotacaoInteligenteProposta, pk=proposta_pk)
        
        if proposta.cotacao.empresa != request.user.empresa:
            return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
        
        data = json.loads(request.body)
        motivo = data.get('motivo', '')
        
        # Desmarcar outras propostas do mesmo item
        CotacaoInteligenteProposta.objects.filter(
            cotacao=proposta.cotacao,
            item=proposta.item
        ).update(selecionada=False, motivo_selecao='')
        
        # Marcar esta como selecionada
        proposta.selecionada = True
        proposta.motivo_selecao = motivo
        proposta.save()
        
        # Atualizar preço no ProdutoFornecedor
        ProdutoFornecedor.objects.filter(
            produto=proposta.item.produto,
            fornecedor=proposta.fornecedor
        ).update(preco_compra=proposta.preco_unitario)
        
        return JsonResponse({
            'success': True,
            'message': 'Proposta selecionada com sucesso!'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def historico_precos(request, produto_pk):
    """Exibe histórico de preços de um produto por fornecedor"""
    produto = get_object_or_404(Produto, pk=produto_pk)
    
    if produto.categoria.empresa != request.user.empresa:
        return JsonResponse({'success': False, 'error': 'Não autorizado'}, status=403)
    
    historico = HistoricoPrecoFornecedor.objects.filter(
        produto=produto
    ).select_related('fornecedor', 'cotacao').order_by('-data_cotacao')[:50]
    
    # Agrupar por fornecedor
    historico_por_fornecedor = {}
    for h in historico:
        if h.fornecedor.nome not in historico_por_fornecedor:
            historico_por_fornecedor[h.fornecedor.nome] = []
        
        historico_por_fornecedor[h.fornecedor.nome].append({
            'data': h.data_cotacao.strftime('%d/%m/%Y'),
            'preco': float(h.preco_unitario),
            'quantidade': float(h.quantidade),
            'prazo': h.prazo_entrega,
            'cotacao': h.cotacao.numero if h.cotacao else h.documento_referencia
        })
    
    return JsonResponse({
        'success': True,
        'produto': produto.nome,
        'historico': historico_por_fornecedor
    })


def gerar_numero_cotacao(empresa):
    """Gera número sequencial de cotação"""
    ano = datetime.now().year
    ultima = CotacaoInteligente.objects.filter(
        empresa=empresa,
        numero__startswith=f'COT/{ano}/'
    ).order_by('-numero').first()
    
    if ultima:
        ultimo_num = int(ultima.numero.split('/')[-1])
        proximo = ultimo_num + 1
    else:
        proximo = 1
    
    return f"COT/{ano}/{proximo:05d}"
