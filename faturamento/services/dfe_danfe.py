"""
Geração de DANFE (PDF) para documentos de terceiros recebidos via Distribuição de DF-e.

Diferente do DANFE de nota própria (que vem pronto da IntegraNotas no momento da
emissão — ver `faturamento.views.nota_fiscal_danfe`), essas NF-e foram emitidas por
outra empresa: o único jeito de ter um PDF é montar o DANFE localmente a partir do
XML completo (nfeProc) baixado após a manifestação. Layout inspirado no mesmo
DANFE usado pra nota própria (`templates/faturamento/nota_fiscal/danfe_preview.html`),
mas com HTML/CSS compatível com xhtml2pdf (sem flexbox/grid, já que a conversão
aqui é automática no servidor, não "imprimir no navegador").
"""
from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from lxml import etree

logger = logging.getLogger(__name__)

NFE_NS = 'http://www.portalfiscal.inf.br/nfe'
_NS = {'nfe': NFE_NS}

FRETE_LABELS = {
    '0': '0-Por conta do Emit',
    '1': '1-Por conta do Dest',
    '2': '2-Por conta de Terceiros',
    '3': '3-Próprio Remetente',
    '4': '4-Próprio Destinatário',
    '9': '9-Sem Frete',
}


def _dec(txt: str | None) -> Decimal:
    if not txt:
        return Decimal('0')
    try:
        return Decimal(txt)
    except InvalidOperation:
        return Decimal('0')


def _t(el, tag: str) -> str:
    """Busca a primeira ocorrência da tag em qualquer nível abaixo de `el` — útil pra
    campos que só existem dentro de UM grupo variável (ex.: vICMS dentro de ICMS00/
    ICMS10/.../ICMS90, sem precisar saber qual grupo o item usa)."""
    if el is None:
        return ''
    found = el.find(f'.//nfe:{tag}', namespaces=_NS)
    return (found.text or '').strip() if found is not None else ''


def _t1(el, tag: str) -> str:
    """Busca só filho direto — usado onde a tag se repete em níveis diferentes do XML
    (ex.: CNPJ aparece em emit, dest e transporta)."""
    if el is None:
        return ''
    found = el.find(f'nfe:{tag}', namespaces=_NS)
    return (found.text or '').strip() if found is not None else ''


def _parse_dt(txt: str, *, only_date: bool = False):
    if not txt:
        return None
    try:
        dt = datetime.fromisoformat(txt.replace('Z', '+00:00'))
        return dt.date() if only_date else dt
    except ValueError:
        return None


def _montar_endereco(el_ender) -> str:
    if el_ender is None:
        return ''
    partes = [_t1(el_ender, 'xLgr')]
    if _t1(el_ender, 'nro'):
        partes.append(_t1(el_ender, 'nro'))
    endereco = ', '.join(p for p in partes if p)
    if _t1(el_ender, 'xCpl'):
        endereco += f" — {_t1(el_ender, 'xCpl')}"
    return endereco


def montar_dados_danfe(xml_str: str) -> SimpleNamespace | None:
    """Parseia o XML completo (nfeProc) da distribuição e monta a estrutura usada
    pelo template `faturamento/dfe_danfe.html`. Retorna None se não der pra ler."""
    try:
        raiz = etree.fromstring(xml_str.encode('utf-8'))
    except etree.XMLSyntaxError:
        logger.warning('XML da DF-e inválido ao montar dados do DANFE')
        return None

    inf_nfe = raiz.find('.//nfe:infNFe', namespaces=_NS)
    if inf_nfe is None:
        return None

    ide = inf_nfe.find('nfe:ide', namespaces=_NS)
    emit = inf_nfe.find('nfe:emit', namespaces=_NS)
    total = inf_nfe.find('nfe:total/nfe:ICMSTot', namespaces=_NS)
    transp = inf_nfe.find('nfe:transp', namespaces=_NS)
    cobr = inf_nfe.find('nfe:cobr', namespaces=_NS)
    inf_adic = inf_nfe.find('nfe:infAdic', namespaces=_NS)
    prot_infprot = raiz.find('.//nfe:protNFe/nfe:infProt', namespaces=_NS)

    chave_acesso = (inf_nfe.get('Id') or '').replace('NFe', '')

    ident = SimpleNamespace(
        numero=_t1(ide, 'nNF'),
        serie=_t1(ide, 'serie'),
        natureza_operacao=_t1(ide, 'natOp'),
        tipo_operacao=_t1(ide, 'tpNF'),
        chave_acesso=chave_acesso,
        data_emissao=_parse_dt(_t1(ide, 'dhEmi')),
        data_saida=_parse_dt(_t1(ide, 'dhSaiEnt')),
        protocolo_autorizacao=_t1(prot_infprot, 'nProt') if prot_infprot is not None else '',
        data_protocolo=_parse_dt(_t1(prot_infprot, 'dhRecbto')) if prot_infprot is not None else None,
    )

    ender_emit = emit.find('nfe:enderEmit', namespaces=_NS) if emit is not None else None
    emitente = SimpleNamespace(
        razao_social=_t1(emit, 'xNome'),
        cnpj=_t1(emit, 'CNPJ') or _t1(emit, 'CPF'),
        ie=_t1(emit, 'IE'),
        endereco=_montar_endereco(ender_emit),
        bairro=_t1(ender_emit, 'xBairro'),
        cep=_t1(ender_emit, 'CEP'),
        municipio=_t1(ender_emit, 'xMun'),
        uf=_t1(ender_emit, 'UF'),
        fone=_t1(ender_emit, 'fone'),
    )

    itens = []
    for det in inf_nfe.findall('nfe:det', namespaces=_NS):
        prod = det.find('nfe:prod', namespaces=_NS)
        imposto = det.find('nfe:imposto', namespaces=_NS)
        icms = imposto.find('nfe:ICMS', namespaces=_NS) if imposto is not None else None
        ipi = imposto.find('nfe:IPI', namespaces=_NS) if imposto is not None else None
        itens.append(SimpleNamespace(
            codigo=_t1(prod, 'cProd'),
            descricao=_t1(prod, 'xProd'),
            ncm=_t1(prod, 'NCM'),
            cfop=_t1(prod, 'CFOP'),
            origem_mercadoria=_t(icms, 'orig'),
            cst_icms=_t(icms, 'CST') or _t(icms, 'CSOSN'),
            unidade=_t1(prod, 'uCom'),
            quantidade=_dec(_t1(prod, 'qCom')),
            valor_unitario=_dec(_t1(prod, 'vUnCom')),
            valor_total=_dec(_t1(prod, 'vProd')),
            valor_desconto=_dec(_t1(prod, 'vDesc')),
            icms_base_calculo=_dec(_t(icms, 'vBC')),
            valor_icms=_dec(_t(icms, 'vICMS')),
            valor_ipi=_dec(_t(ipi, 'vIPI')),
            aliquota_icms=_dec(_t(icms, 'pICMS')),
            aliquota_ipi=_dec(_t(ipi, 'pIPI')),
        ))

    totais = SimpleNamespace(
        base_calculo_icms=_dec(_t1(total, 'vBC')),
        valor_icms=_dec(_t1(total, 'vICMS')),
        valor_icms_st=_dec(_t1(total, 'vST')),
        valor_produtos=_dec(_t1(total, 'vProd')),
        valor_frete=_dec(_t1(total, 'vFrete')),
        valor_seguro=_dec(_t1(total, 'vSeg')),
        valor_desconto=_dec(_t1(total, 'vDesc')),
        valor_ipi=_dec(_t1(total, 'vIPI')),
        valor_total=_dec(_t1(total, 'vNF')),
    )

    transporta = transp.find('nfe:transporta', namespaces=_NS) if transp is not None else None
    veic = transp.find('nfe:veicTransp', namespaces=_NS) if transp is not None else None
    vol = transp.find('nfe:vol', namespaces=_NS) if transp is not None else None
    mod_frete = _t1(transp, 'modFrete') if transp is not None else ''
    transportador = SimpleNamespace(
        nome=_t1(transporta, 'xNome'),
        cnpj=_t1(transporta, 'CNPJ') or _t1(transporta, 'CPF'),
        ie=_t1(transporta, 'IE'),
        endereco=_t1(transporta, 'xEnder'),
        municipio=_t1(transporta, 'xMun'),
        uf=_t1(transporta, 'UF'),
        rntc=_t1(transporta, 'RNTC') or _t1(vol, 'RNTC'),
        frete_label=FRETE_LABELS.get(mod_frete, mod_frete or '—'),
        placa=_t1(veic, 'placa'),
        veic_uf=_t1(veic, 'UF'),
        quantidade_volumes=_t1(vol, 'qVol'),
        especie_volumes=_t1(vol, 'esp'),
        marca_volumes=_t1(vol, 'marca'),
        numeracao_volumes=_t1(vol, 'nVol'),
        peso_bruto_kg=_dec(_t1(vol, 'pesoB')),
        peso_liquido_kg=_dec(_t1(vol, 'pesoL')),
    )

    duplicatas = []
    if cobr is not None:
        for dup in cobr.findall('nfe:dup', namespaces=_NS):
            duplicatas.append(SimpleNamespace(
                numero=_t1(dup, 'nDup'),
                vencimento=_parse_dt(_t1(dup, 'dVenc'), only_date=True),
                valor=_dec(_t1(dup, 'vDup')),
            ))

    informacoes_complementares = _t1(inf_adic, 'infCpl') if inf_adic is not None else ''

    return SimpleNamespace(
        ident=ident,
        emitente=emitente,
        itens=itens,
        totais=totais,
        transportador=transportador,
        duplicatas=duplicatas,
        informacoes_complementares=informacoes_complementares,
    )


def _gerar_barcode_svg(chave: str) -> str:
    if not chave:
        return ''
    try:
        from barcode import Code128
        from barcode.writer import SVGWriter
        buf = io.BytesIO()
        Code128(chave, writer=SVGWriter()).write(buf, options={
            'write_text': False,
            'module_height': 16.0,
            'quiet_zone': 2.0,
            'font_size': 0,
            'text_distance': 0,
            'module_width': 0.29,
        })
        svg = buf.getvalue().decode('utf-8')
        svg = re.sub(r'<[?]xml[^?]*[?]>', '', svg)
        svg = re.sub(r'<!DOCTYPE[^>]*>', '', svg)
        wm = re.search(r'width="([\d.]+)mm"', svg)
        hm = re.search(r'height="([\d.]+)mm"', svg)
        if wm and hm:
            w, h = wm.group(1), hm.group(1)
            svg = svg.replace(
                f'width="{w}mm" height="{h}mm"',
                f'viewBox="0 0 {w} {h}" preserveAspectRatio="none" style="width:100%;height:17mm;display:block"',
            )
        return svg.strip()
    except Exception:
        return ''


def gerar_danfe_pdf(xml_str: str, doc) -> bytes | None:
    """Gera o DANFE (PDF) de um `DfeRecebido` a partir do XML completo já baixado.

    Best-effort: nunca levanta — usada logo após o download do XML completo
    (`baixar_xml_completo_dfe`), sem poder atrapalhar o fluxo principal por causa
    de uma nota com formato inesperado.
    """
    dados = montar_dados_danfe(xml_str)
    if dados is None:
        return None

    try:
        from django.template.loader import render_to_string
        from xhtml2pdf import pisa

        html = render_to_string('faturamento/dfe_danfe.html', {
            'doc': doc,
            'empresa': doc.empresa,
            'dados': dados,
            'barcode_svg': _gerar_barcode_svg(doc.chave_acesso),
        })
        buf = io.BytesIO()
        resultado = pisa.pisaDocument(io.BytesIO(html.encode('utf-8')), buf)
        if resultado.err:
            logger.warning('xhtml2pdf falhou ao gerar DANFE da chave %s', doc.chave_acesso)
            return None
        return buf.getvalue()
    except Exception as exc:
        logger.warning('Falha ao gerar DANFE (PDF) da chave %s: %s', doc.chave_acesso, exc)
        return None
