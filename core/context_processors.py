"""Context processors para adicionar dados globais aos templates"""
from django.db.models import Count, Q, Sum, F, Case, When, DecimalField, ExpressionWrapper, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.core.cache import cache
from decimal import Decimal

_ZEROS = {
    'alertas_criticos': 0,
    'alertas_excesso': 0,
    'total_alertas': 0,
}


def alertas_estoque(request):
    """Adiciona contadores de alertas de estoque ao contexto global"""
    if not request.user.is_authenticated:
        return {'alertas_estoque': _ZEROS}

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return {'alertas_estoque': _ZEROS}

    cache_key = f'alertas_estoque_{empresa.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return {'alertas_estoque': cached}

    alertas = dict(_ZEROS)
    try:
        from estoque.models import Produto, Lote, MovimentacaoEstoque

        lotes_sq = Lote.objects.filter(
            produto=OuterRef('pk'),
            status__in=['DISPONIVEL', 'BLOQUEADO']
        ).values('produto').annotate(total=Sum('quantidade_atual')).values('total')

        entradas_sq = MovimentacaoEstoque.objects.filter(
            produto=OuterRef('pk'),
            lote__isnull=True,
            tipo='ENTRADA',
            status='EXECUTADO'
        ).values('produto').annotate(total=Sum('quantidade')).values('total')

        saidas_sq = MovimentacaoEstoque.objects.filter(
            produto=OuterRef('pk'),
            lote__isnull=True,
            tipo='SAIDA',
            status='EXECUTADO'
        ).values('produto').annotate(total=Sum('quantidade')).values('total')

        _zero = Decimal('0')
        _dec = DecimalField(max_digits=20, decimal_places=4)

        resultado = Produto.objects.filter(
            ativo=True, categoria__empresa=empresa
        ).annotate(
            _lotes=Coalesce(Subquery(lotes_sq), _zero, output_field=_dec),
            _entradas=Coalesce(Subquery(entradas_sq), _zero, output_field=_dec),
            _saidas=Coalesce(Subquery(saidas_sq), _zero, output_field=_dec),
        ).annotate(
            saldo=ExpressionWrapper(
                F('_lotes') + F('_entradas') - F('_saidas'),
                output_field=_dec,
            )
        ).aggregate(
            alertas_criticos=Count(Case(When(saldo__lte=0, then=1))),
            alertas_excesso=Count(Case(When(
                Q(saldo__gt=F('estoque_maximo')) & Q(estoque_maximo__gt=0),
                then=1,
            ))),
        )

        criticos = resultado['alertas_criticos'] or 0
        excesso = resultado['alertas_excesso'] or 0
        alertas = {
            'alertas_criticos': criticos,
            'alertas_excesso': excesso,
            'total_alertas': criticos + excesso,
        }
    except Exception:
        pass

    cache.set(cache_key, alertas, timeout=180)
    return {'alertas_estoque': alertas}


def notificacoes_emprestimo(request):
    """Adiciona contadores globais de mensagens não lidas de empréstimos no menu interno."""
    payload = {
        'total_nao_lidas': 0,
        'emprestimos_com_pendencia': 0,
    }

    if not request.user.is_authenticated or request.user.is_superuser:
        return {'notificacoes_emprestimo': payload}

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return {'notificacoes_emprestimo': payload}

    cache_key = f'notif_emprestimo_{empresa.pk}_{request.user.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return {'notificacoes_emprestimo': cached}

    try:
        from emprestimos.models import EmprestimoMensagem

        mensagens = EmprestimoMensagem.objects.filter(
            empresa=empresa,
            perfil_autor='PRODUTOR',
            lido_interno_em__isnull=True,
        )

        if request.user.tipo not in ['ADMIN', 'GERENTE']:
            mensagens = mensagens.filter(emprestimo__liberado_por=request.user)

        resumo = mensagens.aggregate(
            total_nao_lidas=Count('id'),
            emprestimos_com_pendencia=Count('emprestimo_id', distinct=True),
        )
        payload['total_nao_lidas'] = resumo.get('total_nao_lidas') or 0
        payload['emprestimos_com_pendencia'] = resumo.get('emprestimos_com_pendencia') or 0
    except Exception:
        pass

    cache.set(cache_key, payload, timeout=120)
    return {'notificacoes_emprestimo': payload}


def requisicoes_aguardando_atendimento(request):
    """Adiciona contador de requisições aprovadas aguardando liberação pelo almoxarifado."""
    payload = {'total_aguardando': 0}

    if not request.user.is_authenticated or request.user.is_superuser:
        return {'requisicoes_aguardando_atendimento': payload}

    empresa = getattr(request.user, 'empresa', None)
    if not empresa:
        return {'requisicoes_aguardando_atendimento': payload}

    cache_key = f'req_aguardando_{empresa.pk}'
    cached = cache.get(cache_key)
    if cached is not None:
        return {'requisicoes_aguardando_atendimento': cached}

    try:
        from cadastros.models import Requisicao

        payload['total_aguardando'] = Requisicao.objects.filter(empresa=empresa, status='APROVADA').count()
    except Exception:
        pass

    cache.set(cache_key, payload, timeout=60)
    return {'requisicoes_aguardando_atendimento': payload}
