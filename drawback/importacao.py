"""
Engine de leitura e validação de arquivos XLSX para importação drawback.
Retorna uma lista de dicts com status de cada linha para o preview.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, date


def _parse_date(value):
    if isinstance(value, (datetime, date)):
        return value.date() if isinstance(value, datetime) else value
    if isinstance(value, str):
        for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def _parse_decimal(value):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value).replace(',', '.').strip())
    except InvalidOperation:
        return None


def _str(value):
    if value is None:
        return ''
    return str(value).strip()


# ── ENTRADAS ──────────────────────────────────────────────────────────────────

def validar_entradas(workbook, ato_concessorio, empresa):
    """
    Lê a aba 'Entradas' do workbook e valida cada linha contra o AC.
    Retorna lista de dicts:
      { linha, tipo_compra, fornecedor_str, numero_nf, serie_nf, data_nf,
        data_recebimento, produto_str, quantidade, unidade_str, valor_unitario,
        observacoes, produto_ac (obj ou None), fornecedor (obj ou None),
        saldo_antes, saldo_depois, erros, ok }
    """
    from .models import DrawbackProdutoAC
    from cadastros.models import Fornecedor

    try:
        ws = workbook['Entradas']
    except KeyError:
        return [], ['Aba "Entradas" não encontrada no arquivo.']

    # mapa de produtos do AC por tipo: (nome_lower, tipo_produto) → DrawbackProdutoAC
    # Apenas insumos (importação e mercado interno) são válidos para entradas
    _qs_entradas = DrawbackProdutoAC.objects.filter(
        ato_concessorio=ato_concessorio,
        tipo_produto__in=['IMPORTACAO', 'MERCADO_INTERNO'],
    ).select_related('produto', 'unidade_medida')
    produtos_ac_por_tipo = {
        (p.produto.nome.lower(), p.tipo_produto): p
        for p in _qs_entradas
    }
    # Fallback: mapa apenas por nome (para retrocompatibilidade quando tipo não distingue)
    produtos_ac_por_nome = {}
    for p in _qs_entradas:
        produtos_ac_por_nome[p.produto.nome.lower()] = p

    # mapa de fornecedores: nome_lower → Fornecedor (e cnpj)
    fornecedores = {}
    for f in Fornecedor.objects.filter(empresa=empresa, ativa=True):
        fornecedores[f.nome_fantasia.lower()] = f
        cnpj = (f.cnpj or '').replace('.', '').replace('/', '').replace('-', '')
        if cnpj:
            fornecedores[cnpj] = f

    resultados = []
    saldo_acumulado = {p.id: p.saldo_compra for p in produtos_ac_por_nome.values()}

    TIPOS_VALIDOS = {'IMPORTACAO', 'MERCADO_INTERNO'}

    for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        # Ignora linhas completamente vazias
        if all(c is None or _str(c) == '' for c in row):
            continue

        tipo_compra_raw = _str(row[0]).upper() if len(row) > 0 else ''
        fornecedor_str = _str(row[1]) if len(row) > 1 else ''
        numero_nf = _str(row[2]) if len(row) > 2 else ''
        serie_nf = _str(row[3]) if len(row) > 3 else '1'
        data_nf_raw = row[4] if len(row) > 4 else None
        data_rec_raw = row[5] if len(row) > 5 else None
        produto_str = _str(row[6]) if len(row) > 6 else ''
        quantidade_raw = row[7] if len(row) > 7 else None
        unidade_str = _str(row[8]) if len(row) > 8 else ''
        valor_unit_raw = row[9] if len(row) > 9 else None
        observacoes = _str(row[10]) if len(row) > 10 else ''

        erros = []

        # Validações campo a campo
        tipo_compra = tipo_compra_raw if tipo_compra_raw in TIPOS_VALIDOS else None
        if not tipo_compra:
            erros.append(f'Tipo de compra inválido: "{tipo_compra_raw}". Use IMPORTACAO ou MERCADO_INTERNO.')

        if not numero_nf:
            erros.append('Número da NF é obrigatório.')

        data_nf = _parse_date(data_nf_raw)
        if not data_nf:
            erros.append(f'Data da NF inválida: "{data_nf_raw}". Use DD/MM/AAAA.')

        data_recebimento = _parse_date(data_rec_raw)
        if not data_recebimento:
            erros.append(f'Data de recebimento inválida: "{data_rec_raw}". Use DD/MM/AAAA.')

        if data_recebimento and data_recebimento > ato_concessorio.data_fim_efetiva:
            erros.append(
                f'Data de recebimento ({data_recebimento:%d/%m/%Y}) fora da vigência do AC '
                f'(até {ato_concessorio.data_fim_efetiva:%d/%m/%Y}).'
            )

        quantidade = _parse_decimal(quantidade_raw)
        if not quantidade or quantidade <= 0:
            erros.append(f'Quantidade inválida: "{quantidade_raw}".')

        valor_unitario = _parse_decimal(valor_unit_raw)

        # Busca produto no AC — tenta match por (nome, tipo_compra) primeiro
        produto_ac = (
            produtos_ac_por_tipo.get((produto_str.lower(), tipo_compra))
            or produtos_ac_por_nome.get(produto_str.lower())
        ) if tipo_compra else produtos_ac_por_nome.get(produto_str.lower())
        if not produto_ac:
            erros.append(f'Produto "{produto_str}" não encontrado nos insumos autorizados deste AC.')

        # Busca fornecedor
        forn_key = fornecedor_str.lower().replace('.', '').replace('/', '').replace('-', '')
        fornecedor_obj = fornecedores.get(fornecedor_str.lower()) or fornecedores.get(forn_key)
        aviso_fornecedor = None
        if not fornecedor_obj:
            aviso_fornecedor = f'Fornecedor "{fornecedor_str}" não encontrado no ERP (será salvo como texto).'

        # Verifica saldo acumulado
        saldo_antes = None
        saldo_depois = None
        if produto_ac and quantidade and not erros:
            pid = produto_ac.id
            if pid not in saldo_acumulado:
                saldo_acumulado[pid] = produto_ac.saldo_compra
            saldo_antes = saldo_acumulado[pid]
            saldo_depois = saldo_antes - quantidade
            if saldo_depois < 0:
                erros.append(
                    f'Saldo insuficiente: disponível {saldo_antes}, solicitado {quantidade}.'
                )
            else:
                saldo_acumulado[pid] = saldo_depois

        resultados.append({
            'linha': i,
            'tipo_compra': tipo_compra or tipo_compra_raw,
            'fornecedor_str': fornecedor_str,
            'fornecedor_obj': fornecedor_obj,
            'aviso_fornecedor': aviso_fornecedor,
            'numero_nf': numero_nf,
            'serie_nf': serie_nf or '1',
            'data_nf': data_nf,
            'data_recebimento': data_recebimento,
            'produto_str': produto_str,
            'produto_ac': produto_ac,
            'quantidade': quantidade,
            'unidade_str': unidade_str,
            'valor_unitario': valor_unitario,
            'observacoes': observacoes,
            'saldo_antes': saldo_antes,
            'saldo_depois': saldo_depois,
            'erros': erros,
            'ok': len(erros) == 0,
        })

    return resultados, []


# ── SAÍDAS ────────────────────────────────────────────────────────────────────

def validar_saidas(workbook, ato_concessorio, empresa):
    """
    Lê a aba 'Saídas' do workbook e valida cada linha.
    """
    from .models import DrawbackProdutoAC
    from cadastros.models import Cliente

    try:
        ws = workbook['Saídas']
    except KeyError:
        try:
            ws = workbook['Saidas']
        except KeyError:
            return [], ['Aba "Saídas" não encontrada no arquivo.']

    # Apenas produtos de EXPORTACAO são válidos para saídas
    produtos_ac = {
        p.produto.nome.lower(): p
        for p in DrawbackProdutoAC.objects.filter(
            ato_concessorio=ato_concessorio,
            tipo_produto='EXPORTACAO',
        ).select_related('produto', 'unidade_medida')
    }

    clientes = {c.nome_fantasia.lower(): c
                for c in Cliente.objects.filter(empresa=empresa, ativo=True)}

    saldo_acumulado = {p.id: p.saldo_exportacao for p in produtos_ac.values()}

    resultados = []

    for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        if all(c is None or _str(c) == '' for c in row):
            continue

        cliente_str = _str(row[0]) if len(row) > 0 else ''
        numero_nfe = _str(row[1]) if len(row) > 1 else ''
        numero_re = _str(row[2]) if len(row) > 2 else ''
        numero_due = _str(row[3]) if len(row) > 3 else ''
        data_emb_raw = row[4] if len(row) > 4 else None
        produto_str = _str(row[5]) if len(row) > 5 else ''
        quantidade_raw = row[6] if len(row) > 6 else None
        unidade_str = _str(row[7]) if len(row) > 7 else ''
        fob_raw = row[8] if len(row) > 8 else None
        observacoes = _str(row[9]) if len(row) > 9 else ''

        erros = []

        data_embarque = _parse_date(data_emb_raw)
        if not data_embarque:
            erros.append(f'Data de embarque inválida: "{data_emb_raw}". Use DD/MM/AAAA.')

        if data_embarque and data_embarque > ato_concessorio.data_fim_efetiva:
            erros.append(
                f'Data de embarque ({data_embarque:%d/%m/%Y}) fora da vigência do AC '
                f'(até {ato_concessorio.data_fim_efetiva:%d/%m/%Y}).'
            )

        quantidade = _parse_decimal(quantidade_raw)
        if not quantidade or quantidade <= 0:
            erros.append(f'Quantidade inválida: "{quantidade_raw}".')

        valor_fob = _parse_decimal(fob_raw)

        produto_ac = produtos_ac.get(produto_str.lower())
        if not produto_ac:
            erros.append(f'Produto "{produto_str}" não encontrado nos itens de Exportação deste AC.')

        cliente_obj = clientes.get(cliente_str.lower())

        saldo_antes = None
        saldo_depois = None
        if produto_ac and quantidade and not erros:
            pid = produto_ac.id
            if pid not in saldo_acumulado:
                saldo_acumulado[pid] = produto_ac.saldo_exportacao
            saldo_antes = saldo_acumulado[pid]
            saldo_depois = saldo_antes - quantidade
            if saldo_depois < 0:
                erros.append(
                    f'Saldo para exportar insuficiente: disponível {saldo_antes}, solicitado {quantidade}.'
                )
            else:
                saldo_acumulado[pid] = saldo_depois

        resultados.append({
            'linha': i,
            'cliente_str': cliente_str,
            'cliente_obj': cliente_obj,
            'numero_nfe': numero_nfe,
            'numero_re': numero_re,
            'numero_due': numero_due,
            'data_embarque': data_embarque,
            'produto_str': produto_str,
            'produto_ac': produto_ac,
            'quantidade': quantidade,
            'unidade_str': unidade_str,
            'valor_fob_usd': valor_fob,
            'observacoes': observacoes,
            'saldo_antes': saldo_antes,
            'saldo_depois': saldo_depois,
            'erros': erros,
            'ok': len(erros) == 0,
        })

    return resultados, []
