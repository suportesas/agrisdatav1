"""Geração da etiqueta de caixa (GLOBALG.A.P./PPWR/Lidl IAN) via reportlab puro.

Não usa xhtml2pdf/HTML para este documento: o xhtml2pdf tem um bug confirmado no
subconjunto de glifos do reportlab quando um parágrafo mistura muitos alfabetos
diferentes (latim, grego, cirílico) — caracteres somem como "notdef" mesmo com uma
fonte Unicode registrada corretamente. O reportlab puro (Table/Paragraph, sem passar
pela camada HTML do xhtml2pdf) renderiza tudo certo com a mesma fonte, por isso a
etiqueta de caixa é montada diretamente com Platypus.

Layout segue o template oficial do Lidl "Traceability Label — regular, no logos"
(v.01.01.2025): Article name+IAN, Country of origin, Grower(GGN)+Class, Packhouse
(nome+endereço+GGN), TP/SP, Supplier(nome+GGN), Packaging+Size, Variety, Key
(farm code + batch number) e Other (aviso PPWR + código de reciclagem do material).
"""
import io
import math
import os
from xml.sax.saxutils import escape

import barcode as pybarcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Polygon
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


# Ordem de idiomas exigida pelo template Lidl: DE-EN, FR-ES, IT-PT, EL-NL, FI-SV,
# DA-HU, CS-PL, HR-SK, SL-BG, RO-LT, SR-LV, ET.
_ORIGEM_TEXTO = (
    'Brasilien - Brazil - Brésil - Brasil - Brasile - Brasil - Βραζιλία - Brazilië - Brasilia - '
    'Brasilien - Brasilien - Brazília - Brazílie - Brazylia - Brazil - Brazília - Brazilija - '
    'Бразилия - Brazilia - Brazilija - Brazil - Brazīlija - Brasiilia'
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
        'ian': ParagraphStyle(
            'ian', fontName='Helvetica-Bold', fontSize=21, leading=23, alignment=TA_CENTER,
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
        'packing_valor': ParagraphStyle('packing_valor', fontName='Helvetica-Bold', fontSize=16, leading=18),
        'reciclagem': ParagraphStyle('reciclagem', fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=TA_CENTER),
    }


def _cell(styles, label, valor, sub=None):
    txt = (
        f'<font size="6" color="#333333">{escape(str(label))}</font><br/>'
        f'<font size="8"><b>{escape(str(valor))}</b></font>'
    )
    if sub:
        txt += f'<br/><font size="5.6" color="#333333">{escape(str(sub))}</font>'
    return Paragraph(txt, styles['cell'])


def _cell_grande(styles, label, valor):
    """Variante de _cell com o valor em fonte bem maior (ex: packing unit, mínimo
    de 6mm de x-height no template Lidl) — label e valor em Paragraphs/estilos
    separados (não misturados num único Paragraph) para não estourar o leading
    fixo do estilo 'cell' e sobrepor as linhas."""
    label_p = Paragraph(f'<font size="6" color="#333333">{escape(str(label))}</font>', styles['cell'])
    valor_p = Paragraph(escape(str(valor)), styles['packing_valor'])
    t = Table([[label_p], [valor_p]], colWidths=[None])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


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


def _icone_reciclagem(tam=6 * mm):
    """Símbolo de reciclagem simplificado: 3 setas em loop triangular (versão
    vetorial aproximada do Möbius loop — reportlab.graphics não tem uma primitiva
    de seta curva, então usamos 3 triângulos sólidos distribuídos a 120°)."""
    d = Drawing(tam, tam)
    cx, cy = tam * 0.5, tam * 0.5
    raio = tam * 0.34
    comprimento = tam * 0.34
    for i in range(3):
        ang_centro = math.radians(90 - i * 120)
        bx = cx + raio * math.cos(ang_centro)
        by = cy + raio * math.sin(ang_centro)
        ang_tangente = ang_centro - math.pi / 2
        tip = (bx + comprimento * 0.6 * math.cos(ang_tangente), by + comprimento * 0.6 * math.sin(ang_tangente))
        back1_ang = ang_tangente + math.radians(150)
        back2_ang = ang_tangente - math.radians(150)
        p1 = (bx + comprimento * 0.5 * math.cos(back1_ang), by + comprimento * 0.5 * math.sin(back1_ang))
        p2 = (bx + comprimento * 0.5 * math.cos(back2_ang), by + comprimento * 0.5 * math.sin(back2_ang))
        d.add(Polygon([tip[0], tip[1], p1[0], p1[1], p2[0], p2[1]], fillColor=colors.black, strokeColor=None))
    return d


def _icone_reciclagem_cell(styles, codigo, tam=6 * mm):
    """Ícone de reciclagem empilhado com o código do material (ex: '20 PAP')."""
    icone = _icone_reciclagem(tam)
    partes = codigo.split(None, 1)
    linha1 = escape(partes[0]) if partes else ''
    linha2 = escape(partes[1]) if len(partes) > 1 else ''
    texto = Paragraph(f'{linha1}<br/>{linha2}', styles['reciclagem'])
    t = Table([[icone], [texto]], colWidths=[tam])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return t


def _supplier_fazenda(empresa):
    """Fazenda marcada como Supplier (nome + GGN, fixo por empresa) na etiqueta."""
    from cadastros.models import Fazenda
    return Fazenda.objects.filter(
        empresa=empresa, usar_como_supplier_etiqueta=True, ativa=True,
    ).first()


def _material_transporte(romaneio):
    """Material de embalagem tipo TRANSPORTE (TP) vinculado ao romaneio — fonte do
    código de reciclagem impresso junto ao aviso PPWR."""
    if not romaneio:
        return None
    item = romaneio.materiais_embalagem.filter(material__tipo='TRANSPORTE').select_related('material').first()
    return item.material if item else None


def _bloco_pallet(pallet, romaneio, largura, supplier_fazenda, material_transporte, lote_producao):
    styles = _styles()
    te = pallet.tipo_embalagem
    lp = lote_producao
    fazenda_growing = lp.talhao.fazenda if (lp and lp.talhao_id) else None
    ggn_growing = fazenda_growing.ggn_numero if fazenda_growing and fazenda_growing.ggn_numero else '—'
    codigo_producao = pallet.codigo_producao or '—'
    tp = romaneio.rastreabilidade_transporte if romaneio else None
    sp = romaneio.rastreabilidade_venda if romaneio else None

    nome_multilingue = (te.nome_multilingue if te and te.nome_multilingue else (te.descricao_completa if te else '—'))
    codigo_multilingue = te.codigo_multilingue if te and te.codigo_multilingue else ''
    variedade = te.variedade if te and te.variedade else '—'
    classe = te.classe_categoria if te and te.classe_categoria else '—'
    peso = _fmt_kg(te.peso_liquido_cx) if te else '—'
    calibre = te.tipo_calibre if te and te.tipo_calibre else '—'
    chave_extra = te.codigo_chave_extra if te and te.codigo_chave_extra else ''
    chave_semana = pallet.codigo_chave_semana
    responsavel = romaneio.cliente.ppwr_responsavel if (romaneio and romaneio.cliente.ppwr_responsavel) else '—'

    armazem = pallet.armazem
    packhouse_nome = armazem.nome
    packhouse_endereco = armazem.localizacao or '—'
    packhouse_ggn = armazem.ggn_numero or '—'

    supplier_nome = supplier_fazenda.nome if supplier_fazenda else '—'
    supplier_ggn = (supplier_fazenda.ggn_numero or '—') if supplier_fazenda else '—'

    linhas = []

    # 1. Article name (multilíngue) + IAN
    cw_ian = largura * 0.32
    linhas.append(_grid_row(styles, [
        Paragraph(escape(nome_multilingue), styles['multilingue_nome']),
        Paragraph(escape(codigo_multilingue), styles['ian']),
    ], [largura - cw_ian, cw_ian], largura))

    # 2. Country of origin (multilíngue)
    origem_html = f'<b>Country of origin: Brazil</b><br/>{escape(_ORIGEM_TEXTO)}'
    linhas.append(_linha_unica(styles, Paragraph(origem_html, styles['origem']), largura))

    # 3. Grower (GGN) + Class/Cat.
    linhas.append(_grid_row(styles, [
        _cell(styles, 'Grower', f'GGN {ggn_growing}'),
        _cell(styles, 'Class / Cat.', classe),
    ], [largura / 2, largura / 2], largura))

    # 4. Packhouse (nome + endereço + GGN)
    packhouse_html = (
        f'<font size="6" color="#333333">Packhouse</font><br/>'
        f'<font size="8"><b>{escape(packhouse_nome)}</b></font><br/>'
        f'<font size="6.5">{escape(packhouse_endereco)}</font><br/>'
        f'<font size="6.5">GGN {escape(packhouse_ggn)}</font>'
    )
    linhas.append(_linha_unica(styles, Paragraph(packhouse_html, styles['cell']), largura))

    # 5. TP / SP
    linhas.append(_grid_row(styles, [
        _cell(styles, 'Transport Traceability (TP)', tp or '—'),
        _cell(styles, 'Sales Traceability (SP)', sp or '—'),
    ], [largura / 2, largura / 2], largura))

    # 6. Supplier (nome + GGN)
    linhas.append(_linha_unica(
        styles, _cell(styles, 'Supplier', f'{supplier_nome} — GGN {supplier_ggn}'), largura,
    ))

    # 7. Packaging + Size
    linhas.append(_grid_row(styles, [
        _cell_grande(styles, 'Packaging', peso),
        _cell(styles, 'Size', calibre),
    ], [largura / 2, largura / 2], largura))

    # 8. Variety
    linhas.append(_linha_unica(styles, Paragraph(f'Variety: {escape(variedade)}', styles['variedade']), largura))

    # 9. Key (farm code + batch number)
    key_txt = 'Key: '
    if chave_extra:
        key_txt += f'{escape(chave_extra)} | '
    key_txt += f'{escape(codigo_producao)} &nbsp;&nbsp; {escape(chave_semana)}'
    linhas.append(_linha_unica(styles, Paragraph(key_txt, styles['key']), largura))

    # 10. Other (aviso PPWR + código de reciclagem)
    ppwr_html = (
        f'<font size="5.2">{escape(_PPWR_TEXTO)}</font><br/><br/>'
        f'<font size="6" color="#000000">{escape(responsavel)}</font>'
    )
    ppwr_paragrafo = Paragraph(ppwr_html, styles['ppwr_responsavel'])
    reciclagem_codigo = material_transporte.codigo_reciclagem if (material_transporte and material_transporte.codigo_reciclagem) else None
    if reciclagem_codigo:
        icone_col = 8 * mm
        linhas.append(_grid_row(styles, [
            _icone_reciclagem_cell(styles, reciclagem_codigo),
            ppwr_paragrafo,
        ], [icone_col, largura - icone_col], largura))
    else:
        linhas.append(_linha_unica(styles, ppwr_paragrafo, largura))

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
    from cadastros.models import Fazenda
    from .models import OrdemEmbalagem, RomaneioMaterialEmbalagem

    empresa_ids = {ctx['pallet'].empresa_id for ctx in pallets_ctx}
    supplier_por_empresa = {
        f.empresa_id: f
        for f in Fazenda.objects.filter(empresa_id__in=empresa_ids, usar_como_supplier_etiqueta=True, ativa=True)
    }

    romaneio_ids = {ctx['romaneio'].pk for ctx in pallets_ctx if ctx.get('romaneio')}
    material_por_romaneio = {}
    if romaneio_ids:
        for rme in (
            RomaneioMaterialEmbalagem.objects
            .filter(romaneio_id__in=romaneio_ids, material__tipo='TRANSPORTE')
            .select_related('material')
            .order_by('romaneio_id', 'id')
        ):
            material_por_romaneio.setdefault(rme.romaneio_id, rme.material)

    # Lote de produção efetivo por ordem: preferencialmente o vínculo cadastrado no
    # próprio Lote de origem (estoque.Lote.lote_producao); o campo legado
    # OrdemEmbalagem.lote_producao só serve de fallback (ver lote_producao_efetivo).
    ordem_ids = {ctx['pallet'].ordem_embalagem_id for ctx in pallets_ctx}
    ordens = {
        o.pk: o
        for o in OrdemEmbalagem.objects.filter(pk__in=ordem_ids)
        .select_related(
            'lote_producao__talhao__fazenda',
            'lote_origem__lote_producao__talhao__fazenda',
        )
    }
    lote_producao_por_ordem = {oid: o.lote_producao_efetivo() for oid, o in ordens.items()}

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
        pallet = ctx['pallet']
        romaneio = ctx.get('romaneio')
        supplier_fazenda = supplier_por_empresa.get(pallet.empresa_id)
        material_transporte = material_por_romaneio.get(romaneio.pk) if romaneio else None
        lote_producao = lote_producao_por_ordem.get(pallet.ordem_embalagem_id)
        story.append(_bloco_pallet(pallet, romaneio, largura_util, supplier_fazenda, material_transporte, lote_producao))
        if i < len(pallets_ctx) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
