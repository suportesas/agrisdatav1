"""
Views para Dashboard Executivo do SaaS
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from core.pagination import paginate
from datetime import timedelta
from decimal import Decimal
import json

from empresas.models import Empresa, Plano
from usuarios.models import Usuario, LoginRegistro
from .models import (
    ConsumoRecurso, Alerta, MetricaDiaria, LogAcesso
)


def is_superuser(user):
    """Somente superusuário tem acesso"""
    return user.is_superuser


@login_required
@user_passes_test(is_superuser)
def dashboard_executivo(request):
    """
    Dashboard Executivo - Painel principal para superusuário
    Exibe KPIs e métricas do sistema SaaS
    """
    
    # Log de acesso
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    LogAcesso.objects.create(
        usuario=request.user,
        modulo='DASHBOARD',
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    # ========== KPIs PRINCIPAIS ==========
    
    # Total de empresas
    total_empresas = Empresa.objects.count()
    empresas_ativas = Empresa.objects.filter(ativa=True).count()
    empresas_inativas = Empresa.objects.filter(ativa=False).count()
    empresas_bloqueadas = Empresa.objects.filter(bloqueada=True).count()
    
    # Distribuição por plano
    distribuicao_planos = []
    cores = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
    for i, plano in enumerate(Plano.objects.filter(ativo=True).order_by('ordem')):
        count = Empresa.objects.filter(plano=plano).count()
        if count > 0:
            distribuicao_planos.append({
                'nome': plano.nome,
                'count': count,
                'percentual': (count / total_empresas * 100) if total_empresas > 0 else 0,
                'valor': float(plano.valor_mensal),
                'cor': cores[i % len(cores)]
            })
    
    # Total de usuários
    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(empresa__ativa=True).count()
    usuarios_superuser = Usuario.objects.filter(is_superuser=True).count()
    
    # Receita estimada (usar valor_mensalidade que é customizável por empresa)
    receita_mensal = Empresa.objects.filter(ativa=True).aggregate(
        total=Sum('valor_mensalidade')
    )['total'] or Decimal('0')
    
    receita_anual_projetada = receita_mensal * 12
    
    # ========== ALERTAS ==========
    alertas = Alerta.objects.filter(ativo=True).order_by('-data_criacao')[:10]
    alertas_count = Alerta.objects.filter(ativo=True).count()
    
    alertas_criticos = Alerta.objects.filter(
        ativo=True,
        severidade='CRÍTICA'
    ).count()
    
    alertas_altos = Alerta.objects.filter(
        ativo=True,
        severidade='ALTA'
    ).count()
    
    # ========== CONSUMO DE RECURSOS ==========
    consumo_recente = ConsumoRecurso.objects.select_related('empresa').filter(
        Q(alerta_fazendas=True) | Q(alerta_usuarios=True) | Q(alerta_talhoes=True) | Q(alerta_produtos=True)
    ).order_by('-data_calculo')[:5]
    
    # Empresas em alerta (para mostrar no dashboard)
    empresas_em_alerta = ConsumoRecurso.objects.select_related('empresa').filter(
        Q(alerta_fazendas=True) | Q(alerta_usuarios=True) | Q(alerta_talhoes=True) | Q(alerta_produtos=True)
    ).order_by('-data_calculo')[:10]
    
    # ========== ÚLTIMAS ATIVIDADES ==========
    logins_recentes = LoginRegistro.objects.select_related('usuario', 'empresa').order_by('-data_login')[:10]
    
    # Vencimentos próximos
    hoje = timezone.now().date()
    em_7_dias = hoje + timedelta(days=7)
    
    empresas_vencendo = Empresa.objects.filter(
        data_expiracao__gte=hoje,
        data_expiracao__lte=em_7_dias,
        ativa=True
    ).order_by('data_expiracao')
    
    # ========== ESTRUTURA PARA GRÁFICOS ==========
    # Distribuição por tipo de plano
    plano_data = {
        'pequeno': 0,
        'medio': 0,
        'grande': 0,
        'enterprise': 0,
        'receita_pequeno': 0,
        'receita_medio': 0,
        'receita_grande': 0,
        'receita_enterprise': 0,
    }
    
    for empresa in Empresa.objects.filter(ativa=True):
        if empresa.plano:
            plano_codigo = empresa.plano.codigo.lower()
            valor = float(empresa.plano.valor_mensal or 0)
            
            if plano_codigo.startswith('p'):
                plano_data['pequeno'] += 1
                plano_data['receita_pequeno'] += valor
            elif plano_codigo.startswith('m'):
                plano_data['medio'] += 1
                plano_data['receita_medio'] += valor
            elif plano_codigo.startswith('g'):
                plano_data['grande'] += 1
                plano_data['receita_grande'] += valor
            elif plano_codigo.startswith('e'):
                plano_data['enterprise'] += 1
                plano_data['receita_enterprise'] += valor
    
    # ========== ALERTAS CRÍTICOS E ALTOS ==========
    alertas_criticos_altos = Alerta.objects.filter(
        ativo=True,
        severidade__in=['CRÍTICA', 'ALTA']
    ).order_by('-data_criacao')[:5]
    
    # ========== CONTEXTO ==========
    context = {
        'page_title': 'Dashboard Executivo',
        
        # KPIs principais (cards)
        'total_empresas': total_empresas,
        'empresas_ativas': empresas_ativas,
        'empresas_inativas': empresas_inativas,
        'empresas_bloqueadas': empresas_bloqueadas,
        
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'usuarios_superuser': usuarios_superuser,
        
        'receita_mensal': float(receita_mensal),
        'receita_anual': float(receita_anual_projetada),
        
        # Distribuição de planos (para gráfico)
        'plano_json': json.dumps(plano_data),
        'distribuicao_planos': distribuicao_planos,
        
        # Alertas
        'alertas_criticos_altos': alertas_criticos_altos,
        'alertas_count': alertas_count,
        'alertas_ativos': alertas_criticos + alertas_altos,
        'alertas_criticos': alertas_criticos,
        
        # Consumo de recursos
        'consumos_alerta': empresas_em_alerta,
        
        # Últimas atividades
        'acessos_recentes': logins_recentes,
    }
    
    return render(request, 'metricas/dashboard_executivo.html', context)


@login_required
@user_passes_test(is_superuser)
def consumo_recursos_list(request):
    """
    Lista de consumo de recursos por empresa
    Com visualização de alertas
    """
    
    # Log de acesso
    LogAcesso.objects.create(
        usuario=request.user,
        modulo='METRICAS',
        ip_address=get_client_ip(request)
    )
    
    filtro = request.GET.get('filtro', '')
    busca = request.GET.get('busca', '')
    
    consumos = ConsumoRecurso.objects.select_related('empresa').order_by('-data_calculo')
    
    # Filtrar por alerta
    if filtro == 'com_alerta':
        consumos = consumos.filter(
            Q(alerta_fazendas=True) | 
            Q(alerta_usuarios=True) | 
            Q(alerta_talhoes=True) | 
            Q(alerta_produtos=True)
        )
    elif filtro == 'sem_alerta':
        consumos = consumos.exclude(
            Q(alerta_fazendas=True) | 
            Q(alerta_usuarios=True) | 
            Q(alerta_talhoes=True) | 
            Q(alerta_produtos=True)
        )
    
    # Buscar por empresa
    if busca:
        consumos = consumos.filter(Q(empresa__razao_social__icontains=busca) | Q(empresa__nome_fantasia__icontains=busca))
    
    # Paginação (mostrar últimos registros por empresa)
    ultimosPorEmpresa = []
    vistas = set()
    for consumo in consumos[:100]:  # Limitar a query
        if consumo.empresa_id not in vistas:
            ultimosPorEmpresa.append(consumo)
            vistas.add(consumo.empresa_id)
    
    # Estatísticas
    empresas_total = Empresa.objects.count()
    
    consumos_com_alerta = ConsumoRecurso.objects.filter(
        Q(alerta_fazendas=True) | 
        Q(alerta_usuarios=True) | 
        Q(alerta_talhoes=True) | 
        Q(alerta_produtos=True)
    ).values_list('empresa_id', flat=True).distinct()
    empresas_com_alerta = len(consumos_com_alerta)
    
    # Média de uso de todas as empresas
    media_uso = ConsumoRecurso.objects.aggregate(
        media=(
            (Avg('percentual_fazendas') + Avg('percentual_usuarios') + Avg('percentual_talhoes') + Avg('percentual_produtos')) / 4
        )
    )['media'] or 0
    
    # Empresas com >80% de uso (críticas)
    consumos_criticos = ConsumoRecurso.objects.filter(
        Q(alerta_fazendas=True) | 
        Q(alerta_usuarios=True) | 
        Q(alerta_talhoes=True) | 
        Q(alerta_produtos=True)
    ).values_list('empresa_id', flat=True).distinct()
    empresas_criticas = len(consumos_criticos)
    
    # Paginação
    page_obj, per_page, per_page_options = paginate(request, ultimosPorEmpresa)

    context = {
        'page_title': 'Consumo de Recursos',
        'page_obj': page_obj,
        'paginator': page_obj.paginator,
        'filtro': filtro,
        'busca': busca,
        'empresas_total': empresas_total,
        'empresas_com_alerta': empresas_com_alerta,
        'media_uso': media_uso,
        'empresas_criticas': empresas_criticas,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    
    return render(request, 'metricas/consumo_recursos_list.html', context)


@login_required
@user_passes_test(is_superuser)
def consumo_empresa_detail(request, empresa_id):
    """
    Detalhe de consumo de uma empresa específica
    """
    
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    # Consumo atual (último registro)
    consumo_atual = ConsumoRecurso.objects.filter(empresa=empresa).order_by('-data_calculo').first()
    
    # Histórico de 30 dias
    historico = ConsumoRecurso.objects.filter(
        empresa=empresa
    ).order_by('-data_calculo')[:30]
    
    # Gráfico de evolução (últimos 7 dias)
    data_limite = timezone.now() - timedelta(days=7)
    consumos_7dias = ConsumoRecurso.objects.filter(
        empresa=empresa,
        data_calculo__gte=data_limite
    ).order_by('data_calculo')
    
    dados_grafico = {
        'datas': [c.data_calculo.strftime('%d/%m') for c in consumos_7dias],
        'percentuais_fazendas': [float(c.percentual_fazendas) for c in consumos_7dias],
        'percentuais_usuarios': [float(c.percentual_usuarios) for c in consumos_7dias],
        'percentuais_talhoes': [float(c.percentual_talhoes) for c in consumos_7dias],
        'percentuais_produtos': [float(c.percentual_produtos) for c in consumos_7dias],
    }
    
    # Últimos acessos ao dashboard de métricas
    acessos_recentes = LogAcesso.objects.select_related('usuario').order_by('-data_acesso')[:10]
    
    context = {
        'page_title': f'Consumo - {empresa.razao_social}',
        'empresa': empresa,
        'consumo_atual': consumo_atual,
        'historico': historico,
        'acessos_recentes': acessos_recentes,
        'graph_json': json.dumps(dados_grafico),
    }
    
    return render(request, 'metricas/consumo_empresa_detail.html', context)


@login_required
@user_passes_test(is_superuser)
def alertas_list(request):
    """
    Lista de alertas do sistema
    """
    
    LogAcesso.objects.create(
        usuario=request.user,
        modulo='ALERTAS',
        ip_address=get_client_ip(request)
    )
    
    status = request.GET.get('status', '')
    tipo = request.GET.get('tipo', '')
    severidade = request.GET.get('severidade', '')
    
    alertas = Alerta.objects.all()
    
    if status == 'ativo':
        alertas = alertas.filter(ativo=True)
    elif status == 'lidos':
        alertas = alertas.filter(lido=True)
    
    if tipo:
        alertas = alertas.filter(tipo=tipo)
    
    if severidade:
        alertas = alertas.filter(severidade=severidade)
    
    alertas = alertas.order_by('-data_criacao')
    
    # Contadores
    total_alertas = Alerta.objects.count()
    alertas_ativos = Alerta.objects.filter(ativo=True).count()
    alertas_criticos = Alerta.objects.filter(ativo=True, severidade='CRÍTICA').count()
    alertas_lidos = Alerta.objects.filter(lido=True).count()
    
    # Paginação
    page_obj, per_page, per_page_options = paginate(request, alertas)

    context = {
        'page_title': 'Alertas do Sistema',
        'alertas': page_obj.object_list if page_obj else [],
        'page_obj': page_obj,
        'paginator': page_obj.paginator,
        'is_paginated': page_obj.has_other_pages() if page_obj else False,
        'status': status,
        'tipo': tipo,
        'severidade': severidade,
        'total_alertas': total_alertas,
        'alertas_ativos': alertas_ativos,
        'alertas_criticos': alertas_criticos,
        'alertas_lidos': alertas_lidos,
        'tipo_choices': Alerta.TIPOS,
        'severidade_choices': Alerta.SEVERIDADE,
        'per_page': per_page,
        'per_page_options': per_page_options,
    }
    
    return render(request, 'metricas/alertas_list.html', context)


def get_client_ip(request):
    """
    Extrai IP do cliente da request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
