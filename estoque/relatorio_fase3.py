"""
Novas views para FASE 3 - Relatórios Avançados de Estoque
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q, Case, When, DecimalField, FloatField
from django.db.models.functions import Cast
from datetime import timedelta, datetime
import json
from decimal import Decimal

from .models import MovimentacaoEstoque, Lote, Armazem, LocalEstocagem
from produtos.models import Produto
from compras.models import PedidoCompra


@login_required
def relatorio_analise_abc(request):
    """
    Análise ABC de Produtos (Pareto)
    Classifica produtos por valor total movimentado
    """
    empresa = request.user.empresa
    
    # Pegar produtos com seus valores de movimentação
    produtos = Produto.objects.filter(
        ativo=True,
        empresa=empresa
    ).annotate(
        total_entrada=Sum(
            'movimentacao_estoque__quantidade',
            filter=Q(movimentacao_estoque__tipo='ENTRADA', movimentacao_estoque__status='EXECUTADO')
        ),
        total_saida=Sum(
            'movimentacao_estoque__quantidade',
            filter=Q(movimentacao_estoque__tipo='SAIDA', movimentacao_estoque__status='EXECUTADO')
        ),
        valor_estoque=F('estoque_atual') * F('preco_custo')
    ).filter(
        movimentacao_estoque__isnull=False
    ).distinct()
    
    # Calcular valor total movimentado (entrada + saída) * preço médio
    produtos_com_valor = []
    valor_total_geral = Decimal('0')
    
    for produto in produtos:
        total_entrada = produto.total_entrada or 0
        total_saida = produto.total_saida or 0
        total_quantidade = total_entrada + total_saida
        
        valor_estoque = produto.preco_custo * produto.estoque_atual if produto.estoque_atual else 0
        valor_total_geral += valor_estoque
        
        produtos_com_valor.append({
            'produto': produto,
            'quantidade_total': total_quantidade,
            'valor_estoque': valor_estoque,
            'estoque_atual': produto.estoque_atual,
            'preco_custo': produto.preco_custo,
        })
    
    # Ordenar por valor de estoque descendente
    produtos_com_valor.sort(key=lambda x: float(x['valor_estoque']), reverse=True)
    
    # Calcular percentuais acumulados e classificar ABC
    acumulado = Decimal('0')
    for item in produtos_com_valor:
        acumulado += item['valor_estoque']
        percentual_acumulado = float((acumulado / valor_total_geral * 100)) if valor_total_geral > 0 else 0
        
        # Classificação ABC
        if percentual_acumulado <= 80:
            item['classe'] = 'A'
        elif percentual_acumulado <= 95:
            item['classe'] = 'B'
        else:
            item['classe'] = 'C'
        
        item['percentual_acumulado'] = round(percentual_acumulado, 2)
        item['percentual_valor'] = round(float((item['valor_estoque'] / valor_total_geral * 100)), 2) if valor_total_geral > 0 else 0
    
    # Contar por classe
    classe_a = len([p for p in produtos_com_valor if p['classe'] == 'A'])
    classe_b = len([p for p in produtos_com_valor if p['classe'] == 'B'])
    classe_c = len([p for p in produtos_com_valor if p['classe'] == 'C'])
    
    context = {
        'produtos': produtos_com_valor[:20],  # Top 20
        'valor_total_geral': valor_total_geral,
        'classe_a_count': classe_a,
        'classe_b_count': classe_b,
        'classe_c_count': classe_c,
        'total_produtos': len(produtos_com_valor),
        'title': 'Análise ABC de Produtos',
    }
    
    return render(request, 'estoque/relatorio_abc.html', context)


@login_required
def relatorio_comparativo_periodos(request):
    """
    Comparativo de movimentações entre períodos
    """
    empresa = request.user.empresa
    
    # Período padrão: últimos 3 meses
    data_fim = timezone.now().date()
    data_inicio = data_fim - timedelta(days=90)
    
    if request.method == 'POST':
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
    
    # Dividir em 3 períodos iguais
    dias_total = (datetime.strptime(data_fim, '%Y-%m-%d').date() - datetime.strptime(data_inicio, '%Y-%m-%d').date()).days if isinstance(data_inicio, str) else (data_fim - data_inicio).days
    dias_periodo = dias_total // 3
    
    if isinstance(data_inicio, str):
        data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    periodo_1_inicio = data_inicio
    periodo_1_fim = data_inicio + timedelta(days=dias_periodo)
    
    periodo_2_inicio = periodo_1_fim + timedelta(days=1)
    periodo_2_fim = periodo_2_inicio + timedelta(days=dias_periodo)
    
    periodo_3_inicio = periodo_2_fim + timedelta(days=1)
    periodo_3_fim = data_fim
    
    # Dados por período
    def obter_dados_periodo(data_ini, data_fim):
        entradas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='ENTRADA',
            status='EXECUTADO',
            data_criacao__date__gte=data_ini,
            data_criacao__date__lte=data_fim
        ).aggregate(
            quantidade=Sum('quantidade'),
            valor=Sum(F('quantidade') * F('produto__preco_custo'), output_field=DecimalField())
        )
        
        saidas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='SAIDA',
            status='EXECUTADO',
            data_criacao__date__gte=data_ini,
            data_criacao__date__lte=data_fim
        ).aggregate(
            quantidade=Sum('quantidade'),
            valor=Sum(F('quantidade') * F('produto__preco_custo'), output_field=DecimalField())
        )
        
        return {
            'entradas_qtd': entradas['quantidade'] or 0,
            'entradas_val': float(entradas['valor'] or 0),
            'saidas_qtd': saidas['quantidade'] or 0,
            'saidas_val': float(saidas['valor'] or 0),
        }
    
    periodo_1 = obter_dados_periodo(periodo_1_inicio, periodo_1_fim)
    periodo_2 = obter_dados_periodo(periodo_2_inicio, periodo_2_fim)
    periodo_3 = obter_dados_periodo(periodo_3_inicio, periodo_3_fim)
    
    # Calcular variações
    periodo_1['label'] = f'{periodo_1_inicio.strftime("%d/%m")} a {periodo_1_fim.strftime("%d/%m")}'
    periodo_2['label'] = f'{periodo_2_inicio.strftime("%d/%m")} a {periodo_2_fim.strftime("%d/%m")}'
    periodo_3['label'] = f'{periodo_3_inicio.strftime("%d/%m")} a {periodo_3_fim.strftime("%d/%m")}'
    
    context = {
        'periodo_1': periodo_1,
        'periodo_2': periodo_2,
        'periodo_3': periodo_3,
        'data_inicio': data_inicio.strftime('%Y-%m-%d'),
        'data_fim': data_fim.strftime('%Y-%m-%d'),
        'title': 'Comparativo de Períodos',
    }
    
    return render(request, 'estoque/relatorio_comparativo.html', context)


@login_required
def relatorio_auditoria(request):
    """
    Auditoria de transações de estoque
    Quem fez o quê, quando e onde
    """
    empresa = request.user.empresa
    
    # Filtros
    tipo = request.GET.get('tipo', '')
    usuario = request.GET.get('usuario', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    movimentacoes = MovimentacaoEstoque.objects.filter(
        empresa=empresa
    ).select_related(
        'produto', 'criado_por', 'armazem'
    ).order_by('-data_criacao')
    
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    
    if usuario:
        movimentacoes = movimentacoes.filter(criado_por__username__icontains=usuario)
    
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_criacao__date__gte=data_inicio)
    
    if data_fim:
        movimentacoes = movimentacoes.filter(data_criacao__date__lte=data_fim)
    
    # Paginação manual (primeiras 100)
    movimentacoes = movimentacoes[:100]
    
    context = {
        'movimentacoes': movimentacoes,
        'tipos_movimento': MovimentacaoEstoque.TIPO_CHOICES,
        'title': 'Auditoria de Transações',
        'filtros_ativos': bool(tipo or usuario or data_inicio or data_fim),
    }
    
    return render(request, 'estoque/relatorio_auditoria.html', context)


@login_required
def relatorio_rastreamento_lote(request, lote_id=None):
    """
    Rastreamento completo de um lote
    Mostra toda a jornada: entrada -> saídas
    """
    empresa = request.user.empresa
    
    if lote_id:
        lote = get_object_or_404(Lote, pk=lote_id, empresa=empresa)
        
        # Histórico do lote
        movimentacoes = MovimentacaoEstoque.objects.filter(
            lote=lote
        ).order_by('data_criacao')
        
        # Dados do lote
        dados_lote = {
            'numero': lote.numero,
            'produto': lote.produto.nome,
            'quantidade_inicial': lote.quantidade_inicial,
            'quantidade_atual': lote.quantidade_atual,
            'status': lote.get_status_display(),
            'data_entrada': lote.data_entrada,
            'data_validade': lote.data_validade,
            'armazem': lote.armazem.nome,
            'local': str(lote.local_estocagem) if lote.local_estocagem else 'Não definido',
        }
        
        context = {
            'lote': dados_lote,
            'movimentacoes': movimentacoes,
            'title': f'Rastreamento do Lote {lote.numero}',
        }
        
        return render(request, 'estoque/relatorio_rastreamento_lote.html', context)
    
    else:
        # Lista todos os lotes para seleção
        lotes = Lote.objects.filter(
            empresa=empresa
        ).select_related('produto', 'armazem')
        
        context = {
            'lotes': lotes,
            'title': 'Rastreamento de Lotes',
        }
        
        return render(request, 'estoque/lista_lotes_rastreamento.html', context)


@login_required
def relatorio_baixo_estoque_alertas(request):
    """
    Alertas de estoque baixo com sugestão de reposição
    """
    empresa = request.user.empresa
    
    # Produtos com estoque abaixo do mínimo
    produtos_baixos = Produto.objects.filter(
        ativo=True,
        empresa=empresa,
        estoque_atual__lt=F('estoque_minimo')
    ).annotate(
        diferenca=F('estoque_minimo') - F('estoque_atual'),
        dias_consumo=Case(
            When(movimentacao_estoque__tipo='SAIDA', movimentacao_estoque__status='EXECUTADO', then=30),
            default=0
        )
    ).select_related('unidade_medida')
    
    # Produtos chegando ao mínimo (entre 80% e 100% do mínimo)
    produtos_alerta = Produto.objects.filter(
        ativo=True,
        empresa=empresa,
        estoque_atual__gte=F('estoque_minimo') * 0.8,
        estoque_atual__lt=F('estoque_minimo')
    ).select_related('unidade_medida')
    
    # Produtos críticos (zerados ou negativos)
    produtos_criticos = Produto.objects.filter(
        ativo=True,
        empresa=empresa,
        estoque_atual__lte=0
    ).select_related('unidade_medida')
    
    context = {
        'produtos_criticos': produtos_criticos,
        'produtos_baixos': produtos_baixos,
        'produtos_alerta': produtos_alerta,
        'total_problemas': produtos_criticos.count() + produtos_baixos.count(),
        'title': 'Alertas de Estoque Baixo',
    }
    
    return render(request, 'estoque/relatorio_alertas.html', context)


@login_required
def api_dashboard_dados(request):
    """
    API para retornar dados do dashboard em JSON
    Para gráficos em tempo real
    """
    empresa = request.user.empresa
    
    # Últimos 30 dias
    data_inicio = timezone.now() - timedelta(days=30)
    
    # Movimentações por dia
    movimentacoes_dia = []
    datas = []
    
    for i in range(30):
        data = data_inicio + timedelta(days=i)
        entradas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='ENTRADA',
            status='EXECUTADO',
            data_criacao__date=data.date()
        ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        
        saidas = MovimentacaoEstoque.objects.filter(
            empresa=empresa,
            tipo='SAIDA',
            status='EXECUTADO',
            data_criacao__date=data.date()
        ).aggregate(Sum('quantidade'))['quantidade__sum'] or 0
        
        movimentacoes_dia.append({
            'data': data.strftime('%d/%m'),
            'entradas': float(entradas),
            'saidas': float(saidas),
        })
    
    # Produtos com menor estoque
    produtos_menor = Produto.objects.filter(
        ativo=True,
        empresa=empresa
    ).order_by('estoque_atual')[:5]
    
    produtos_lista = [{
        'nome': p.nome,
        'estoque': p.estoque_atual,
        'minimo': p.estoque_minimo,
        'alerta': p.estoque_atual < p.estoque_minimo
    } for p in produtos_menor]
    
    return JsonResponse({
        'movimentacoes': movimentacoes_dia,
        'produtos_baixos': produtos_lista,
    })
