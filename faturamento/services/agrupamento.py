"""Serviço de Faturamento Agrupado com Lógica Invertida.

Fluxo:
  Fase 1 — NF Filha (REMESSA): baixa estoque físico ao ser autorizada pela SEFAZ.
  Fase 2 — NF Mãe (FATURAMENTO): consolida fiscalmente as filhas, sem tocar estoque.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


# ---------------------------------------------------------------------------
# CFOP helpers
# ---------------------------------------------------------------------------

def _mesmo_estado(empresa, cliente):
    """Retorna True se emitente e destinatário estão no mesmo estado."""
    try:
        uf_empresa = empresa.estado or ''
    except AttributeError:
        uf_empresa = ''
    try:
        end = cliente.enderecos.filter(tipo='PRINCIPAL').first()
        uf_cliente = end.uf if end else ''
    except AttributeError:
        uf_cliente = ''
    return uf_empresa.upper() == uf_cliente.upper() if uf_empresa and uf_cliente else True


def inferir_cfop_remessa(empresa, cliente):
    """CFOP da Nota Filha de Remessa: 5949 (interno) ou 6949 (interestadual)."""
    return '5949' if _mesmo_estado(empresa, cliente) else '6949'


def inferir_cfop_faturamento(empresa, cliente, produto=None):
    """CFOP da Nota Mãe de Faturamento.

    Produção própria → 5116/6116.
    Mercadoria adquirida/revendida → 5117/6117.
    Sem produto → assume produção própria.
    """
    proprio = True
    if produto is not None:
        try:
            proprio = getattr(produto, 'producao_propria', True)
        except Exception:
            proprio = True
    interno = _mesmo_estado(empresa, cliente)
    if proprio:
        return '5116' if interno else '6116'
    return '5117' if interno else '6117'


# ---------------------------------------------------------------------------
# Validação da seleção
# ---------------------------------------------------------------------------

def validar_selecao_notas(notas_ids, empresa):
    """Valida e retorna a queryset de notas para fechamento.

    Regras:
    - Todas devem pertencer à empresa.
    - Todas devem ser tipo REMESSA, status EMITIDA, status_faturamento PENDENTE.
    - Todas devem ter chave_acesso preenchida (SEFAZ autorizou).
    - Todas devem ter o mesmo cliente.
    - Deve haver ao menos 1 nota.
    """
    from faturamento.models import NotaFiscal

    if not notas_ids:
        raise ValidationError('Selecione pelo menos uma nota de remessa.')

    notas = NotaFiscal.objects.filter(pk__in=notas_ids, empresa=empresa).select_related('cliente')

    if notas.count() != len(notas_ids):
        raise ValidationError('Uma ou mais notas não foram encontradas ou pertencem a outra empresa.')

    invalidas = []
    for nf in notas:
        erros = []
        if nf.tipo_operacao != 'REMESSA':
            erros.append('não é do tipo REMESSA')
        if nf.status != 'EMITIDA':
            erros.append(f'status é {nf.status} (deve ser EMITIDA)')
        if nf.status_faturamento != 'PENDENTE':
            erros.append(f'status_faturamento é {nf.status_faturamento} (deve ser PENDENTE)')
        if not nf.chave_acesso:
            erros.append('sem chave de acesso SEFAZ')
        if not nf.cliente_id:
            erros.append('sem cliente')
        if erros:
            invalidas.append(f'NF {nf.numero}: {", ".join(erros)}')

    if invalidas:
        raise ValidationError('Notas inválidas para faturamento: ' + '; '.join(invalidas))

    clientes = {nf.cliente_id for nf in notas}
    if len(clientes) > 1:
        raise ValidationError(
            'Todas as notas devem ser do mesmo cliente. '
            'Selecione apenas notas de um único cliente por fechamento.'
        )

    return notas


# ---------------------------------------------------------------------------
# Consolidação de itens por Produto + Lote
# ---------------------------------------------------------------------------

def consolidar_itens_para_nota_mae(notas_filhas):
    """Consolida os itens das notas filhas agrupando por (produto_id, lote_id).

    Retorna lista de dicts com os dados consolidados. O último item recebe
    ajuste de centavos para garantir Σ == total_financeiro_das_filhas.
    """
    from collections import defaultdict

    grupos = defaultdict(lambda: {
        'produto': None,
        'lote': None,
        'descricao': '',
        'ncm': '',
        'cfop': '',
        'unidade': 'UN',
        'quantidade': Decimal('0'),
        'valor_unitario': Decimal('0'),
        'valor_total': Decimal('0'),
        'aliquota_icms': Decimal('0'),
        'cst_icms': '',
        'cst_pis': '07',
        'cst_cofins': '07',
        'aliquota_pis': Decimal('0'),
        'aliquota_cofins': Decimal('0'),
        'origem_mercadoria': '0',
    })

    total_filhas = Decimal('0')

    for nf in notas_filhas:
        total_filhas += nf.valor_total
        for item in nf.itens.select_related('produto', 'lote'):
            chave = (item.produto_id, item.lote_id)
            g = grupos[chave]
            g['produto'] = item.produto
            g['lote'] = item.lote
            g['descricao'] = item.descricao
            g['ncm'] = item.ncm
            g['unidade'] = item.unidade
            g['quantidade'] += item.quantidade
            g['valor_total'] += item.valor_total
            # tributos — usa alíquotas do último item (assume uniformidade por produto)
            g['cst_icms'] = item.cst_icms
            g['aliquota_icms'] = item.aliquota_icms
            g['cst_pis'] = item.cst_pis
            g['aliquota_pis'] = item.aliquota_pis
            g['cst_cofins'] = item.cst_cofins
            g['aliquota_cofins'] = item.aliquota_cofins
            g['origem_mercadoria'] = item.origem_mercadoria

    itens = list(grupos.values())

    # Calcula valor_unitario médio ponderado e recalcula valor_total
    for g in itens:
        if g['quantidade']:
            g['valor_unitario'] = (g['valor_total'] / g['quantidade']).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            )

    # Ajuste de centavos: garante que soma dos itens == total das filhas
    soma_itens = sum(g['valor_total'] for g in itens)
    diferenca = total_filhas - soma_itens
    if itens and diferenca != Decimal('0'):
        itens[-1]['valor_total'] += diferenca

    return itens


# ---------------------------------------------------------------------------
# Texto de informações complementares
# ---------------------------------------------------------------------------

def gerar_infcpl_faturamento(notas_filhas):
    """Gera o texto das informações complementares da NF Mãe."""
    linhas = [
        f'NF {nf.numero:06d} em {nf.data_emissao:%d/%m/%Y} (Chave: {nf.chave_acesso})'
        for nf in notas_filhas
    ]
    return 'NF-e de Faturamento referente às remessas anteriores:\n' + '\n'.join(linhas)


# ---------------------------------------------------------------------------
# Criação da Nota Mãe
# ---------------------------------------------------------------------------

@transaction.atomic
def criar_nota_mae(notas_filhas, data_emissao, cfop, natureza_operacao,
                   informacoes_complementares, empresa, usuario):
    """Cria a NotaFiscal Mãe (RASCUNHO) com itens consolidados e NFeReferenciadas.

    Não emite para a SEFAZ — a emissão é feita na view gerar_nota_mae.
    """
    from faturamento.models import NotaFiscal, ItemNotaFiscal, NFeReferenciada

    cliente = notas_filhas[0].cliente

    # Valor total = soma das filhas (sem reprocessar — garantido por consolidar_itens)
    valor_total = sum(nf.valor_total for nf in notas_filhas)
    valor_produtos = sum(nf.valor_produtos for nf in notas_filhas)

    nota_mae = NotaFiscal.objects.create(
        empresa=empresa,
        cliente=cliente,
        tipo_operacao='FATURAMENTO',
        status='RASCUNHO',
        status_faturamento='NAO_APLICA',
        data_emissao=data_emissao,
        natureza_operacao=natureza_operacao,
        informacoes_complementares=informacoes_complementares,
        valor_produtos=valor_produtos,
        valor_total=valor_total,
        finalidade_nfe='1',
        presenca_comprador='9',
        criado_por=usuario,
        atualizado_por=usuario,
    )

    # Itens consolidados
    itens_consolidados = consolidar_itens_para_nota_mae(notas_filhas)
    for idx, g in enumerate(itens_consolidados, start=1):
        ItemNotaFiscal.objects.create(
            nota_fiscal=nota_mae,
            numero_item=idx,
            produto=g['produto'],
            lote=g['lote'],
            descricao=g['descricao'],
            ncm=g['ncm'],
            cfop=cfop,
            unidade=g['unidade'],
            quantidade=g['quantidade'],
            valor_unitario=g['valor_unitario'],
            valor_total=g['valor_total'],
            cst_icms=g['cst_icms'],
            aliquota_icms=g['aliquota_icms'],
            cst_pis=g['cst_pis'],
            aliquota_pis=g['aliquota_pis'],
            cst_cofins=g['cst_cofins'],
            aliquota_cofins=g['aliquota_cofins'],
            origem_mercadoria=g['origem_mercadoria'],
        )

    # NF-es referenciadas (uma por filha)
    for nf in notas_filhas:
        NFeReferenciada.objects.create(
            nota_fiscal=nota_mae,
            chave_acesso_referenciada=nf.chave_acesso,
            numero_referenciado=nf.numero,
            data_emissao_referenciada=nf.data_emissao,
        )

    return nota_mae


# ---------------------------------------------------------------------------
# Pós-autorização SEFAZ — Nota Filha (REMESSA)
# ---------------------------------------------------------------------------

@transaction.atomic
def processar_autorizacao_remessa(nota_filha):
    """Chamado após autorização SEFAZ de NF tipo REMESSA.

    Cria MovimentacaoEstoque de SAÍDA por item e seta status_faturamento=PENDENTE.
    Respeita configuração remessa_lote_obrigatorio da empresa.
    Se configurado, cria conta a receber da filha (NOTAS_FILHAS).
    """
    if nota_filha.tipo_operacao != 'REMESSA':
        return

    from estoque.services import criar_movimentacao

    try:
        config = nota_filha.empresa.configuracao_fiscal
        lote_obrigatorio = config.remessa_lote_obrigatorio
        financeiro_origem = config.financeiro_remessa_origem
    except Exception:
        lote_obrigatorio = True
        financeiro_origem = 'NOTA_MAE'

    for item in nota_filha.itens.select_related('produto', 'lote', 'lote__armazem'):
        if not item.produto:
            continue

        if lote_obrigatorio and not item.lote:
            raise ValidationError(
                f'Item "{item.descricao}" sem lote — '
                'configure "Lote obrigatório" como desativado na Configuração Fiscal '
                'se esta operação não exige rastreabilidade por lote.'
            )

        armazem = item.lote.armazem if item.lote else None

        criar_movimentacao(
            empresa=nota_filha.empresa,
            tipo='SAIDA',
            origem='REMESSA_FATURAMENTO',
            quantidade=item.quantidade,
            usuario=nota_filha.atualizado_por or nota_filha.criado_por,
            lote=item.lote,
            produto=item.produto,
            armazem_origem=armazem,
            documento=f'NF-e {nota_filha.numero}/{nota_filha.serie}',
            observacao=(
                f'Remessa para posterior faturamento — '
                f'Cliente: {nota_filha.cliente} — '
                f'Chave: {nota_filha.chave_acesso}'
            ),
        )

    nota_filha.status_faturamento = 'PENDENTE'
    nota_filha.save(update_fields=['status_faturamento'])

    if financeiro_origem == 'NOTAS_FILHAS':
        _criar_lancamento_financeiro(nota_filha)


# ---------------------------------------------------------------------------
# Pós-autorização SEFAZ — Nota Mãe (FATURAMENTO)
# ---------------------------------------------------------------------------

@transaction.atomic
def processar_autorizacao_faturamento(nota_mae):
    """Chamado após autorização SEFAZ de NF tipo FATURAMENTO.

    Marca todas as filhas como FATURADAS e vincula à nota mãe.
    NÃO movimenta estoque (regra central do fluxo invertido).
    Se configurado, cria conta a receber da mãe (NOTA_MAE).
    """
    if nota_mae.tipo_operacao != 'FATURAMENTO':
        return

    try:
        financeiro_origem = nota_mae.empresa.configuracao_fiscal.financeiro_remessa_origem
    except Exception:
        financeiro_origem = 'NOTA_MAE'

    # Vincula e marca as filhas referenciadas como FATURADAS
    from faturamento.models import NotaFiscal
    chaves_filhas = list(
        nota_mae.nfes_referenciadas.values_list('chave_acesso_referenciada', flat=True)
    )
    NotaFiscal.objects.filter(
        empresa=nota_mae.empresa,
        chave_acesso__in=chaves_filhas,
        status_faturamento='PENDENTE',
    ).update(
        status_faturamento='FATURADA',
        nota_mae=nota_mae,
    )

    if financeiro_origem == 'NOTA_MAE':
        _criar_lancamento_financeiro(nota_mae)


# ---------------------------------------------------------------------------
# Estorno de estoque ao cancelar Nota Filha PENDENTE
# ---------------------------------------------------------------------------

@transaction.atomic
def registrar_estorno_remessa(nota_filha):
    """Cria MovimentacaoEstoque de ENTRADA (estorno) ao cancelar NF Filha ainda PENDENTE."""
    if nota_filha.tipo_operacao != 'REMESSA' or nota_filha.status_faturamento != 'PENDENTE':
        return

    from estoque.services import criar_movimentacao

    for item in nota_filha.itens.select_related('produto', 'lote', 'lote__armazem'):
        if not item.produto:
            continue

        armazem = item.lote.armazem if item.lote else None

        criar_movimentacao(
            empresa=nota_filha.empresa,
            tipo='ENTRADA',
            origem='CANCELAMENTO_REMESSA',
            quantidade=item.quantidade,
            usuario=nota_filha.atualizado_por or nota_filha.criado_por,
            lote=item.lote,
            produto=item.produto,
            armazem_origem=armazem,
            documento=f'Estorno NF-e {nota_filha.numero}/{nota_filha.serie}',
            observacao=f'Estorno por cancelamento de remessa — Chave: {nota_filha.chave_acesso}',
        )

    nota_filha.status_faturamento = 'NAO_APLICA'
    nota_filha.save(update_fields=['status_faturamento'])


# ---------------------------------------------------------------------------
# Integração financeira (stub — expande conforme módulo financeiro)
# ---------------------------------------------------------------------------

def _criar_lancamento_financeiro(nota):
    """Cria conta a receber no módulo financeiro para a nota informada.

    Stub: implementação completa depende de financeiro.models e do fluxo de
    duplicatas/parcelas definido no projeto.
    """
    try:
        from financeiro.services import criar_conta_receber_nfe
        criar_conta_receber_nfe(nota)
    except (ImportError, AttributeError):
        pass
