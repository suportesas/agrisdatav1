from datetime import date
from decimal import Decimal


def parse_cnab240(file_obj):
    """
    Parseia arquivo de retorno CNAB 240 (FEBRABAN padrão).
    Suporta Bradesco, Itaú, Santander, BB e Sicoob (posições base FEBRABAN).

    Retorno: mesmo formato que parse_ofx().
    """
    conteudo = file_obj.read()
    if isinstance(conteudo, bytes):
        for enc in ('latin-1', 'cp1252', 'utf-8'):
            try:
                conteudo = conteudo.decode(enc)
                break
            except UnicodeDecodeError:
                continue

    linhas = conteudo.splitlines()
    lancamentos = []
    header_info = {}
    erros = 0

    for num_linha, linha in enumerate(linhas, 1):
        if len(linha) < 240:
            continue

        tipo_registro = linha[7]  # posição 8 (0-indexed: 7)

        # Header de arquivo (tipo 0)
        if tipo_registro == '0':
            header_info['codigo_banco'] = linha[0:3].strip()
            header_info['nome_empresa'] = linha[72:102].strip()
            header_info['data_geracao'] = _parse_data_ddmmaaaa(linha[143:151])
            continue

        # Detalhe (tipo 3) — segmentos P, Q, R, T, U, J
        if tipo_registro == '3':
            segmento = linha[13] if len(linha) > 13 else ''

            if segmento == 'P':
                try:
                    lancamento = _parse_segmento_p(linha, num_linha)
                    if lancamento:
                        lancamentos.append(lancamento)
                except Exception:
                    erros += 1
                    continue

            elif segmento == 'T':
                # Segmento T — crédito em conta (recebimentos)
                try:
                    lancamento = _parse_segmento_t(linha, num_linha)
                    if lancamento:
                        lancamentos.append(lancamento)
                except Exception:
                    erros += 1
                    continue

    datas = [l['data'] for l in lancamentos if l['data']]
    return {
        'banco': header_info.get('nome_empresa', '') or header_info.get('codigo_banco', ''),
        'conta': '',
        'data_inicio': min(datas) if datas else None,
        'data_fim': max(datas) if datas else None,
        'lancamentos': lancamentos,
        '_erros_parse': erros,
    }


def _parse_segmento_p(linha, num_linha):
    """Segmento P — pagamento (débito). Posições FEBRABAN padrão."""
    # Posições padrão (0-indexed):
    # 73-92: número do documento (20 chars)
    # 93-100: data do pagamento DDMMAAAA (8 chars)
    # 119-131: valor do pagamento (13 dígitos, 2 decimais implícitos)
    # 230-239: ocorrências (10 chars)

    num_doc = linha[73:93].strip()
    data_str = linha[93:101]
    valor_str = linha[119:132].strip()
    ocorrencia = linha[230:240].strip() if len(linha) >= 240 else ''

    data = _parse_data_ddmmaaaa(data_str)
    if not data:
        return None

    try:
        valor = Decimal(valor_str) / Decimal('100')
    except Exception:
        return None

    if valor <= 0:
        return None

    return {
        'fit_id': f'CNAB_P_{num_doc}_{data_str}_{num_linha}',
        'tipo': 'DEBITO',
        'valor': valor,
        'data': data,
        'descricao': f'CNAB240 Pagamento — Ocorrência: {ocorrencia or "000"}',
        'numero_documento': num_doc,
    }


def _parse_segmento_t(linha, num_linha):
    """Segmento T — crédito em conta (cobrança/recebimento)."""
    # Posições padrão para segmento T de retorno de cobrança:
    # 73-92: número do documento / nosso número
    # 143-150: data de crédito DDMMAAAA
    # 153-165: valor do crédito (13 dígitos, 2 decimais)

    num_doc = linha[73:93].strip()
    data_str = linha[143:151] if len(linha) > 151 else ''
    valor_str = linha[153:166].strip() if len(linha) > 166 else ''

    data = _parse_data_ddmmaaaa(data_str)
    if not data:
        return None

    try:
        valor = Decimal(valor_str) / Decimal('100')
    except Exception:
        return None

    if valor <= 0:
        return None

    return {
        'fit_id': f'CNAB_T_{num_doc}_{data_str}_{num_linha}',
        'tipo': 'CREDITO',
        'valor': valor,
        'data': data,
        'descricao': f'CNAB240 Crédito / Cobrança',
        'numero_documento': num_doc,
    }


def _parse_data_ddmmaaaa(s):
    """Converte string DDMMAAAA em date. Retorna None se inválida."""
    if not s or len(s) < 8:
        return None
    try:
        d, m, a = int(s[0:2]), int(s[2:4]), int(s[4:8])
        if d == 0 or m == 0 or a == 0:
            return None
        return date(a, m, d)
    except (ValueError, TypeError):
        return None
