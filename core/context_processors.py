"""Context processors para adicionar dados globais aos templates"""
from django.db.models import Count, Q, Sum
from decimal import Decimal


def alertas_estoque(request):
    """Adiciona contadores de alertas de estoque ao contexto global"""
    alertas = {
        'alertas_criticos': 0,
        'alertas_excesso': 0,
        'total_alertas': 0,
    }
    
    # Se o usuário estiver autenticado e tiver empresa
    if request.user.is_authenticated and hasattr(request.user, 'empresa') and request.user.empresa:
        try:
            from estoque.models import Produto, Lote, MovimentacaoEstoque
            from django.db.models import DecimalField
            from django.db.models.functions import Coalesce
            
            empresa = request.user.empresa
            produtos = Produto.objects.filter(ativo=True, categoria__empresa=empresa)
            
            # Contadores de alertas
            alertas_criticos = 0
            alertas_excesso = 0
            
            for produto in produtos:
                # 1. Total de lotes disponiveis/bloqueados
                total_lotes = Lote.objects.filter(
                    produto=produto,
                    status__in=['DISPONIVEL', 'BLOQUEADO']
                ).aggregate(total=Sum('quantidade_atual'))['total'] or Decimal('0')
                
                # 2. Movimentacoes diretas (sem lote) EXECUTADAS
                movs_diretas_entrada = MovimentacaoEstoque.objects.filter(
                    produto=produto,
                    lote__isnull=True,
                    tipo='ENTRADA',
                    status='EXECUTADO'
                ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
                
                movs_diretas_saida = MovimentacaoEstoque.objects.filter(
                    produto=produto,
                    lote__isnull=True,
                    tipo='SAIDA',
                    status='EXECUTADO'
                ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')
                
                # Saldo = Lotes + (Entradas diretas - Saidas diretas)
                saldo = Decimal(total_lotes) + (Decimal(movs_diretas_entrada) - Decimal(movs_diretas_saida))
                
                # Categoriza alertas
                if saldo <= 0:
                    alertas_criticos += 1
                elif produto.estoque_maximo > 0 and saldo > produto.estoque_maximo:
                    alertas_excesso += 1
            
            alertas = {
                'alertas_criticos': alertas_criticos,
                'alertas_excesso': alertas_excesso,
                'total_alertas': alertas_criticos + alertas_excesso,
            }
        except Exception as e:
            # Se houver erro ao carregar dados, retorna zeros
            pass
    
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

    try:
        from cadastros.models import EmprestimoMensagem

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

    return {'notificacoes_emprestimo': payload}
