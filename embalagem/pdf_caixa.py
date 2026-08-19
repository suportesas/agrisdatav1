"""Geração da etiqueta de caixa (GLOBALG.A.P./PPWR) via reportlab puro.

Não usa xhtml2pdf/HTML para este documento: o xhtml2pdf tem um bug confirmado no
subconjunto de glifos do reportlab quando um parágrafo mistura muitos alfabetos
diferentes (latim, grego, cirílico) — caracteres somem como "notdef" mesmo com uma
fonte Unicode registrada corretamente. O reportlab puro (Table/Paragraph, sem passar
pela camada HTML do xhtml2pdf) renderiza tudo certo com a mesma fonte, por isso a
etiqueta de caixa é montada diretamente com Platypus.
"""
import io
import os
from xml.sax.saxutils import escape

import barcode as pybarcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

_DEJAVU_REGISTERED = False
_DEJAVU_FONT_NAME = 'DejaVuSansMono'


def _registrar_fonte_dejavu():
    """Registra a fonte DejaVu (já embutida via dependência python-barcode) sob
    demanda. Usada nos 3 blocos com tradução (nome multi-idioma, país de origem,
    aviso PPWR), que podem conter grego, cirílico e latim estendido."""
    global _DEJAVU_REGISTERED
    if _DEJAVU_REGISTERED:
        return
    font_path = os.path.join(os.path.dirname(pybarcode.__file__), 'fonts', 'DejaVuSansMono.ttf')
    pdfmetrics.registerFont(TTFont(_DEJAVU_FONT_NAME, font_path))
    _DEJAVU_REGISTERED = True


_ORIGEM_TEXTO = (
    'Brasilien - Brasil - Brésil - Brasil - Brasile - Brasil - Βραζιλία - Brazilië - Brasilia - '
    'Brasilien - Brasilien - Brazília - Brazílie - Brazylia - Brazil - Brazília - Brazilija - '
    'Бразилия - Brasilia - Brazilija - Brazil - Brazīlija - Brasiilia'
)

_PPWR_TEXTO = (
    'Erzeuger gemäß PPWR / Manufacturer according to PPWR / Fabricant selon PPWR / '
    'Fabricante conforme a PPWR / Fabbricante ai sensi del PPWR / Fabricante de acordo com o PPWR / '
    'Κατασκευαστής σύμφωνα με τον Κανονισμό PPWR / Fabrikant volgens PPWR / '
    'PPWR:n mukainen valmistaja / Tillverkare i enlighet med PPWR / Fabrikant i henhold til PPWR / '
    'PPWR szerinti előállító / Výrobce dle Nařízení o obalech (PPWR) / Wytwórca zgodnie z PPWR / '
    'Izrađivač u skladu s PPWR-om / Izdelovalec v skladu s PPWR / Произвеждащ оператор по PPWR / '
    'Fabricant în conformitate cu PPWR / Fizinis gamintojas pagal PPAR / '
    'Valmistaja vastavalt pakendimäärusele:'
)


def _fmt_kg(valor):
    if valor is None:
        return '—'
    return f'{float(valor):.1f}'.replace('.', ',') + ' kg'


def _styles():
    _registrar_fonte_dejavu()
    return {
        'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=8, leading=10),
        'variedade': ParagraphStyle('variedade', fontName='Helvetica-Bold', fontSize=8, leading=10),
        'multilingue_nome': ParagraphStyle(
            'multilingue_nome', fontName=_DEJAVU_FONT_NAME, fontSize=6, leading=7.5, textColor=colors.black,
        ),
        'multilingue_codigo': ParagraphStyle(
            'multilingue_codigo', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_CENTER,
        ),
        'origem': ParagraphStyle(
            'origem', fontName=_DEJAVU_FONT_NAME, fontSize=5.6, leading=7, textColor=colors.HexColor('#333333'),
        ),
        'ppwr_titulo': ParagraphStyle(
            'ppwr_titulo', fontName=_DEJAVU_FONT_NAME, fontSize=5.2, leading=6.6,
            textColor=colors.HexColor('#333333'),
        ),
        'ppwr_responsavel': ParagraphStyle(
            'ppwr_responsavel', fontName=_DEJAVU_FONT_NAME, fontSize=6, leading=7.5, textColor=colors.black,
        ),
        'key': ParagraphStyle('key', fontName='Helvetica', fontSize=7, leading=9),
        'resumo': ParagraphStyle('resumo', fontName='Helvetica-Bold', fontSize=6.5, leading=8, alignment=TA_CENTER),
    }


def _cell(styles, label, valor, sub=None):
    txt = (
        f'<font size="6" color="#333333">{escape(str(label))}</font><br/>'
        f'<font size="8"><b>{escape(str(valor))}</b></font>'
    )
    if sub:
        txt += f'<br/><font size="5.6" color="#333333">{escape(str(sub))}</font>'
    return Paragraph(txt, styles['cell'])


def _grid_row(styles, cells, col_widths, largura):
    t = Table([cells], colWidths=col_widths)
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 3.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEAFTER', (0, 0), (-2, 0), 0.8, colors.black),
    ]))
    return t


def _linha_unica(styles, flowable, largura):
    t = Table([[flowable]], colWidths=[largura])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 3.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def _bloco_pallet(pallet, romaneio, largura):
    styles = _styles()
    te = pallet.tipo_embalagem
    lp = pallet.ordem_embalagem.lote_producao
    fazenda = lp.talhao.fazenda if (lp and lp.talhao_id) else None
    ggn = fazenda.ggn_numero if fazenda and fazenda.ggn_numero else '—'
    codigo_producao = pallet.codigo_producao or '—'
    tp = romaneio.rastreabilidade_transporte if romaneio else None
    sp = romaneio.rastreabilidade_venda if romaneio else None

    nome_multilingue = (te.nome_multilingue if te and te.nome_multilingue else (te.descricao_completa if te else '—'))
    codigo_multilingue = te.codigo_multilingue if te and te.codigo_multilingue else ''
    variedade = te.variedade if te and te.variedade else '—'
    classe = te.classe_categoria if te and te.classe_categoria else '—'
    peso = _fmt_kg(te.peso_liquido_cx) if te else '—'
    calibre = te.tipo_calibre if te and te.tipo_calibre else '—'
    talhao_codigo = lp.talhao.codigo if (lp and lp.talhao_id and lp.talhao.codigo) else ''
    chave_extra = te.codigo_chave_extra if te and te.codigo_chave_extra else ''
    chave_semana = pallet.codigo_chave_semana
    responsavel = romaneio.cliente.ppwr_responsavel if (romaneio and romaneio.cliente.ppwr_responsavel) else '—'
    empresa_nome = pallet.empresa.nome

    linhas = []

    # Cabeçalho de rastreabilidade (3 colunas)
    cw = largura / 3
    linhas.append(_grid_row(styles, [
        _cell(styles, 'Production Traceability', codigo_producao),
        _cell(styles, 'Transport Traceability', tp or '—'),
        _cell(styles, 'Sales Traceability', sp or '—'),
    ], [cw, cw, cw], largura))

    linhas.append(_linha_unica(styles, Paragraph(f'Variety: {escape(variedade)}', styles['variedade']), largura))

    linhas.append(_grid_row(styles, [
        Paragraph(escape(nome_multilingue), styles['multilingue_nome']),
        Paragraph(escape(codigo_multilingue), styles['multilingue_codigo']),
    ], [largura - 15 * mm, 15 * mm], largura))

    origem_html = f'<b>Country of origin: Brazil</b><br/>{escape(_ORIGEM_TEXTO)}'
    linhas.append(_linha_unica(styles, Paragraph(origem_html, styles['origem']), largura))

    linhas.append(_grid_row(styles, [
        _cell(styles, 'Grower', f'GGN {ggn}'),
        _cell(styles, 'Class / Cat.', classe),
    ], [largura / 2, largura / 2], largura))

    linhas.append(_grid_row(styles, [
        _cell(styles, 'Packhouse', empresa_nome, sub=f'GGN {ggn}'),
        _cell(styles, 'Supplier', empresa_nome, sub=f'GGN {ggn}'),
    ], [largura / 2, largura / 2], largura))

    linhas.append(_grid_row(styles, [
        _cell(styles, 'Packaging', peso),
        _cell(styles, 'Size', calibre),
    ], [largura / 2, largura / 2], largura))

    key_txt = 'Key: '
    if chave_extra:
        key_txt += f'{escape(chave_extra)} | '
    key_txt += f'{escape(codigo_producao)} &nbsp;&nbsp; {escape(chave_semana)}'
    linhas.append(_linha_unica(styles, Paragraph(key_txt, styles['key']), largura))

    ppwr_html = (
        f'<font size="5.2">{escape(_PPWR_TEXTO)}</font><br/><br/>'
        f'<font size="6" color="#000000">{escape(responsavel)}</font>'
    )
    linhas.append(_linha_unica(styles, Paragraph(ppwr_html, styles['ppwr_responsavel']), largura))

    resumo = f'Production: {codigo_producao} — Transport package: {tp or "—"} — Sales package: {sp or "—"}'
    linhas.append(_linha_unica(styles, Paragraph(escape(resumo), styles['resumo']), largura))

    outer = Table([[l] for l in linhas], colWidths=[largura])
    outer.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.3, colors.black),
        ('LINEBELOW', (0, 0), (-1, -2), 0.8, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return outer


def render_etiquetas_caixa_pdf(pallets_ctx):
    """pallets_ctx: lista de dicts {'pallet': PalletEmbalado, 'romaneio': RomaneioVenda|None}."""
    largura_pagina = 100 * mm
    altura_pagina = 150 * mm
    margem = 3 * mm
    largura_util = largura_pagina - 2 * margem

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=(largura_pagina, altura_pagina),
        leftMargin=margem, rightMargin=margem, topMargin=margem, bottomMargin=margem,
    )
    story = []
    for i, ctx in enumerate(pallets_ctx):
        story.append(_bloco_pallet(ctx['pallet'], ctx.get('romaneio'), largura_util))
        if i < len(pallets_ctx) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
