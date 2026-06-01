from datetime import timedelta
from decimal import Decimal

from financeiro.models import PagamentoContaPagar, RecebimentoContaReceber


def sugerir_matches(lancamento, empresa):
    """
    Retorna lista de dicts com candidatos de matching para um ExtratoLancamento.

    Campos de cada dict:
        tipo_operacao: 'CONTA_PAGAR' | 'CONTA_RECEBER'
        operacao_id: int (pk do Pagamento ou Recebimento)
        objeto: instância do model
        descricao: str formatado para exibição
        score: int 0-100
        score_label: str
        score_class: str (Bootstrap color)
    """
    data_inicio = lancamento.data_lancamento - timedelta(days=30)
    data_fim = lancamento.data_lancamento + timedelta(days=30)

    if lancamento.tipo == 'DEBITO':
        candidatos = _candidatos_debito(empresa, data_inicio, data_fim)
        tipo_operacao = 'CONTA_PAGAR'
    else:
        candidatos = _candidatos_credito(empresa, data_inicio, data_fim)
        tipo_operacao = 'CONTA_RECEBER'

    resultado = []
    for obj in candidatos:
        score = _calcular_score(lancamento, obj, tipo_operacao)
        if score < 30:
            continue
        resultado.append({
            'tipo_operacao': tipo_operacao,
            'operacao_id': obj.pk,
            'objeto': obj,
            'descricao': _descricao(obj, tipo_operacao),
            'score': score,
            'score_label': _label(score),
            'score_class': _css_class(score),
        })

    return sorted(resultado, key=lambda x: x['score'], reverse=True)[:10]


def _candidatos_debito(empresa, data_inicio, data_fim):
    return (
        PagamentoContaPagar.objects
        .filter(
            conta_pagar__empresa=empresa,
            data_pagamento__range=(data_inicio, data_fim),
        )
        .exclude(conciliacoes__isnull=False)
        .select_related('conta_pagar', 'conta_pagar__fornecedor', 'parcela')
    )


def _candidatos_credito(empresa, data_inicio, data_fim):
    return (
        RecebimentoContaReceber.objects
        .filter(
            conta_receber__empresa=empresa,
            data_pagamento__range=(data_inicio, data_fim),
        )
        .exclude(conciliacoes__isnull=False)
        .select_related('conta_receber', 'conta_receber__cliente', 'parcela')
    )


def _calcular_score(lancamento, obj, tipo_operacao):
    score = 0

    if tipo_operacao == 'CONTA_PAGAR':
        valor_obj = getattr(obj, 'valor_pago', Decimal('0'))
        data_obj = obj.data_pagamento
        banco_obj = getattr(obj, 'banco', '') or ''
        num_doc_obj = getattr(obj, 'numero_documento', '') or ''
    else:
        valor_obj = getattr(obj, 'valor_recebido_brl', Decimal('0'))
        data_obj = obj.data_pagamento
        banco_obj = getattr(obj, 'banco', '') or ''
        num_doc_obj = getattr(obj, 'numero_documento', '') or ''

    # Critério 1: valor exato (+50)
    if valor_obj == lancamento.valor:
        score += 50

    # Critério 2: data (+20 exata, +10 tolerância 3 dias)
    if data_obj == lancamento.data_lancamento:
        score += 20
    elif abs((data_obj - lancamento.data_lancamento).days) <= 3:
        score += 10

    # Critério 3: número do documento (+20)
    if lancamento.numero_documento and num_doc_obj:
        if lancamento.numero_documento.strip() == num_doc_obj.strip():
            score += 20

    # Critério 4: banco da operação contém nome da conta bancária (+10)
    nome_conta = lancamento.conta_bancaria.banco.lower()
    if banco_obj and nome_conta:
        banco_lower = banco_obj.lower()
        if nome_conta in banco_lower or banco_lower in nome_conta:
            score += 10

    return min(score, 100)


def _descricao(obj, tipo_operacao):
    if tipo_operacao == 'CONTA_PAGAR':
        try:
            cp = obj.conta_pagar
            fornecedor = cp.fornecedor.razao_social if hasattr(cp.fornecedor, 'razao_social') else str(cp.fornecedor)
            return f'CP {cp.numero} — {fornecedor} — R$ {obj.valor_pago:.2f} ({obj.data_pagamento:%d/%m/%Y})'
        except Exception:
            return f'Pagamento #{obj.pk}'
    else:
        try:
            cr = obj.conta_receber
            cliente = cr.cliente.razao_social if hasattr(cr.cliente, 'razao_social') else str(cr.cliente)
            return f'CR {cr.numero} — {cliente} — R$ {obj.valor_recebido_brl:.2f} ({obj.data_pagamento:%d/%m/%Y})'
        except Exception:
            return f'Recebimento #{obj.pk}'


def _label(score):
    if score >= 80:
        return 'Sugestão Forte'
    if score >= 50:
        return 'Sugestão Moderada'
    return 'Sugestão Fraca'


def _css_class(score):
    if score >= 80:
        return 'success'
    if score >= 50:
        return 'warning'
    return 'secondary'
