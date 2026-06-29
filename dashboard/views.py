from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone


@login_required
def index(request):
    user = request.user
    is_saas_admin = user.is_superuser
    hoje = timezone.now().date()

    if is_saas_admin:
        context = _context_saas_admin(hoje)
    else:
        empresa = user.empresa
        if empresa is None:
            context = {}
        else:
            context = _context_empresa(empresa, hoje)

    context['is_saas_admin'] = is_saas_admin
    return render(request, 'dashboard/index.html', context)


def _context_saas_admin(hoje):
    from empresas.models import Empresa
    from usuarios.models import Usuario

    total_empresas = Empresa.objects.count()
    empresas_ativas = Empresa.objects.filter(ativa=True, bloqueada=False).count()
    empresas_bloqueadas = Empresa.objects.filter(Q(ativa=False) | Q(bloqueada=True)).count()

    total_usuarios = Usuario.objects.count()
    usuarios_ativos = Usuario.objects.filter(is_active=True).count()
    novos_usuarios_7d = Usuario.objects.filter(
        date_joined__date__gte=hoje - timedelta(days=7)
    ).count()
    usuarios_sem_empresa = Usuario.objects.filter(empresa__isnull=True, is_superuser=False).count()

    empresas_com_usuarios = (
        Empresa.objects
        .annotate(total_users=Count('usuarios'))
        .order_by('-total_users')[:5]
    )
    max_users = max((e.total_users for e in empresas_com_usuarios), default=1) or 1
    top_empresas_usuarios = [
        {'nome': e.nome, 'total_users': e.total_users, 'pct': int(e.total_users / max_users * 100)}
        for e in empresas_com_usuarios
    ]

    empresas_recentes = Empresa.objects.order_by('-id')[:6]

    return {
        'total_empresas': total_empresas,
        'empresas_ativas': empresas_ativas,
        'empresas_bloqueadas': empresas_bloqueadas,
        'total_usuarios': total_usuarios,
        'usuarios_ativos': usuarios_ativos,
        'novos_usuarios_7d': novos_usuarios_7d,
        'usuarios_sem_empresa': usuarios_sem_empresa,
        'top_empresas_usuarios': top_empresas_usuarios,
        'empresas_recentes': empresas_recentes,
    }


def _context_empresa(empresa, hoje):
    from cadastros.models import Cliente, Fazenda, Produtor
    from compras.models import PedidoCompra, SolicitacaoCompra
    from emprestimos.models import EmprestimoProdutor
    from estoque.models import Armazem
    from financeiro.models import ContaReceber, ParcelaContaPagar
    from usuarios.models import Usuario
    from vendas.models import PedidoVenda

    proximos_7d = hoje + timedelta(days=7)

    # — Financeiro: contas a pagar —
    parcelas_vencidas_qs = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__lt=hoje,
        status__in=['ABERTA', 'VENCIDA'],
    )
    parcelas_vencidas_count = parcelas_vencidas_qs.count()
    valor_vencido = parcelas_vencidas_qs.aggregate(
        total=Sum('valor_total_parcela')
    )['total'] or Decimal('0.00')

    parcelas_7d_qs = ParcelaContaPagar.objects.filter(
        conta_pagar__empresa=empresa,
        data_vencimento__gte=hoje,
        data_vencimento__lte=proximos_7d,
        status='ABERTA',
    )
    parcelas_a_vencer_7d_count = parcelas_7d_qs.count()
    valor_a_vencer_7d = parcelas_7d_qs.aggregate(
        total=Sum('valor_total_parcela')
    )['total'] or Decimal('0.00')

    # — Financeiro: contas a receber —
    receber_qs = ContaReceber.objects.filter(
        empresa=empresa,
        status__in=['ABERTA', 'VENCIDA'],
    )
    contas_receber_abertas = receber_qs.count()
    valor_a_receber = receber_qs.aggregate(
        total=Sum('valor_brl')
    )['total'] or Decimal('0.00')

    # — Compras —
    compras_mes_qs = PedidoCompra.objects.filter(
        empresa=empresa,
        data_pedido__year=hoje.year,
        data_pedido__month=hoje.month,
    )
    compras_mes_count = compras_mes_qs.count()
    compras_mes = compras_mes_qs.aggregate(
        total=Sum('valor_total')
    )['total'] or Decimal('0.00')
    solicitacoes_pendentes_count = SolicitacaoCompra.objects.filter(
        empresa=empresa, status='PENDENTE'
    ).count()

    # — Vendas —
    vendas_mes_qs = PedidoVenda.objects.filter(
        empresa=empresa,
        data_pedido__year=hoje.year,
        data_pedido__month=hoje.month,
    )
    vendas_mes_count = vendas_mes_qs.count()
    vendas_mes = vendas_mes_qs.aggregate(
        total=Sum('valor_total')
    )['total'] or Decimal('0.00')

    # — Operacional —
    total_fazendas = Fazenda.objects.filter(empresa=empresa).count()
    total_clientes = Cliente.objects.filter(empresa=empresa).count()
    total_produtores = Produtor.objects.filter(empresa=empresa).count()
    total_armazens = Armazem.objects.filter(empresa=empresa).count()
    total_usuarios = Usuario.objects.filter(empresa=empresa, is_active=True).count()

    # — Empréstimos com mensagens internas não lidas —
    emprestimos_com_nao_lidas = (
        EmprestimoProdutor.objects
        .filter(empresa=empresa)
        .annotate(
            unread_mensagens_interno_count=Count(
                'mensagens',
                filter=Q(
                    mensagens__perfil_autor='PRODUTOR',
                    mensagens__lido_interno_em__isnull=True,
                ),
            )
        )
        .filter(unread_mensagens_interno_count__gt=0)
        .select_related('produtor', 'produto', 'requisicao')
        .order_by('-data_emprestimo')[:10]
    )
    total_emprestimos_com_pendencia = emprestimos_com_nao_lidas.count()
    total_mensagens_produtor_nao_lidas = sum(
        e.unread_mensagens_interno_count for e in emprestimos_com_nao_lidas
    )

    return {
        # financeiro pagar
        'parcelas_vencidas_count': parcelas_vencidas_count,
        'valor_vencido': valor_vencido,
        'parcelas_a_vencer_7d_count': parcelas_a_vencer_7d_count,
        'valor_a_vencer_7d': valor_a_vencer_7d,
        # financeiro receber
        'contas_receber_abertas': contas_receber_abertas,
        'valor_a_receber': valor_a_receber,
        # compras
        'compras_mes': compras_mes,
        'compras_mes_count': compras_mes_count,
        'solicitacoes_pendentes_count': solicitacoes_pendentes_count,
        # vendas
        'vendas_mes': vendas_mes,
        'vendas_mes_count': vendas_mes_count,
        # operacional
        'total_fazendas': total_fazendas,
        'total_clientes': total_clientes,
        'total_produtores': total_produtores,
        'total_armazens': total_armazens,
        'total_usuarios': total_usuarios,
        # empréstimos
        'total_emprestimos_com_pendencia': total_emprestimos_com_pendencia,
        'pendencias_mensagens_emprestimo': emprestimos_com_nao_lidas,
        'total_mensagens_produtor_nao_lidas': total_mensagens_produtor_nao_lidas,
        'titulo_pendencias_emprestimo': 'Empréstimos com mensagens não lidas',
    }
