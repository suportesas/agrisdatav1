from decimal import Decimal


def parse_ofx(file_obj):
    """
    Parseia um arquivo OFX e retorna dict padronizado.
    Tenta usar ofxparse; se falhar, faz parsing básico por texto.

    Retorno:
        {
            'banco': str,
            'conta': str,
            'data_inicio': date | None,
            'data_fim': date | None,
            'lancamentos': [
                {
                    'fit_id': str,
                    'tipo': 'DEBITO' | 'CREDITO',
                    'valor': Decimal (sempre positivo),
                    'data': date,
                    'descricao': str,
                    'numero_documento': str,
                }
            ]
        }
    """
    try:
        return _parse_com_ofxparse(file_obj)
    except Exception:
        file_obj.seek(0)
        return _parse_texto_ofx(file_obj)


def _parse_com_ofxparse(file_obj):
    from ofxparse import OfxParser

    file_obj.seek(0)
    ofx = OfxParser.parse(file_obj)
    account = ofx.account
    statement = account.statement

    lancamentos = []
    for t in statement.transactions:
        amount = Decimal(str(t.amount))
        tipo = 'DEBITO' if amount < 0 else 'CREDITO'
        data = t.date.date() if hasattr(t.date, 'date') else t.date

        memo = ''
        for attr in ('memo', 'payee', 'name'):
            val = getattr(t, attr, None)
            if val:
                memo = str(val).strip()
                break

        lancamentos.append({
            'fit_id': str(t.id) if t.id else '',
            'tipo': tipo,
            'valor': abs(amount),
            'data': data,
            'descricao': memo or 'Sem descrição',
            'numero_documento': str(t.checknum) if getattr(t, 'checknum', None) else '',
        })

    banco = ''
    try:
        banco = ofx.account.institution.organization
    except Exception:
        pass

    data_inicio = None
    data_fim = None
    try:
        data_inicio = statement.start_date.date() if statement.start_date else None
        data_fim = statement.end_date.date() if statement.end_date else None
    except Exception:
        pass

    return {
        'banco': banco,
        'conta': getattr(account, 'account_id', ''),
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'lancamentos': lancamentos,
    }


def _parse_texto_ofx(file_obj):
    """Fallback: parsing básico por tags de texto para OFX/QFX sem SGML válido."""
    import re
    from datetime import date

    conteudo = file_obj.read()
    if isinstance(conteudo, bytes):
        for enc in ('utf-8', 'latin-1', 'cp1252'):
            try:
                conteudo = conteudo.decode(enc)
                break
            except UnicodeDecodeError:
                continue

    def tag(nome, texto):
        m = re.search(rf'<{nome}>\s*([^\r\n<]+)', texto, re.IGNORECASE)
        return m.group(1).strip() if m else ''

    def parse_data(s):
        try:
            s = s[:8]
            return date(int(s[0:4]), int(s[4:6]), int(s[6:8]))
        except Exception:
            return None

    lancamentos = []
    blocos = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', conteudo, re.DOTALL | re.IGNORECASE)
    for bloco in blocos:
        trntype = tag('TRNTYPE', bloco).upper()
        dtposted = tag('DTPOSTED', bloco)
        trnamt = tag('TRNAMT', bloco).replace(',', '.')
        fitid = tag('FITID', bloco)
        memo = tag('MEMO', bloco) or tag('NAME', bloco) or 'Sem descrição'
        checknum = tag('CHECKNUM', bloco)

        try:
            amount = Decimal(trnamt)
        except Exception:
            continue

        tipo = 'DEBITO' if amount < 0 else 'CREDITO'
        lancamentos.append({
            'fit_id': fitid,
            'tipo': tipo,
            'valor': abs(amount),
            'data': parse_data(dtposted),
            'descricao': memo,
            'numero_documento': checknum,
        })

    lancamentos = [l for l in lancamentos if l['data'] is not None]
    datas = [l['data'] for l in lancamentos]

    return {
        'banco': tag('ORG', conteudo) or tag('FID', conteudo),
        'conta': tag('ACCTID', conteudo),
        'data_inicio': min(datas) if datas else None,
        'data_fim': max(datas) if datas else None,
        'lancamentos': lancamentos,
    }
