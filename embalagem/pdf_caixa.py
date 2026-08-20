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
        'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=6.6, leading=8),
        'variedade': ParagraphStyle('variedade', fontName='Helvetica-Bold', fontSize=6.6, leading=8),
        'multilingue_nome': ParagraphStyle(
            'multilingue_nome', fontName=_DEJAVU_FONT_NAME, fontSize=5, leading=6, textColor=colors.black,
        ),
        'ian': ParagraphStyle(
            'ian', fontName='Helvetica-Bold', fontSize=17, leading=18, alignment=TA_CENTER,
        ),
        'origem': ParagraphStyle(
            'origem', fontName=_DEJAVU_FONT_NAME, fontSize=4.4, leading=5.2, textColor=colors.HexColor('#333333'),
        ),
        'ppwr_responsavel': ParagraphStyle(
            'ppwr_responsavel', fontName=_DEJAVU_FONT_NAME, fontSize=5.4, leading=6.4, textColor=colors.black,
        ),
        'packing_valor': ParagraphStyle('packing_valor', fontName='Helvetica-Bold', fontSize=13, leading=14),
        'reciclagem': ParagraphStyle('reciclagem', fontName='Helvetica-Bold', fontSize=4.2, leading=5, alignment=TA_CENTER),
    }


def _cell(styles, label, valor, sub=None):
    txt = (
        f'<font size="5" color="#333333">{escape(str(label))}</font><br/>'
        f'<font size="6.6"><b>{escape(str(valor))}</b></font>'
    )
    if sub:
        txt += f'<br/><font size="5.6" color="#333333">{escape(str(sub))}</font>'
    return Paragraph(txt, styles['cell'])


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


def _icone_reciclagem_cell(styles, codigo, tam=4.5 * mm):
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


def _endereco_fazenda(fazenda):
    """Endereço completo formatado da fazenda (preferindo o endereço marcado como
    padrão, ou o primeiro cadastrado); usado no bloco Packhouse da etiqueta —
    `Armazem.localizacao` é só um rótulo curto, não um endereço postal de verdade."""
    if not fazenda:
        return None
    endereco = fazenda.enderecos.filter(padrao=True).first() or fazenda.enderecos.first()
    return endereco.get_endereco_completo() if endereco else None


def _material_transporte(romaneio):
    """Material de embalagem tipo TRANSPORTE (TP) vinculado ao romaneio — fonte do
    código de reciclagem impresso junto ao aviso PPWR."""
    if not romaneio:
        return None
    item = romaneio.materiais_embalagem.filter(material__tipo='TRANSPORTE').select_related('material').first()
    return item.material if item else None


def _bloco_pallet(pallet, romaneio, largura, supplier_fazenda, material_transporte, lote_producao, endereco_packhouse, codigo_ian):
    styles = _styles()
    te = pallet.tipo_embalagem
    lp = lote_producao
    fazenda_growing = lp.talhao.fazenda if (lp and lp.talhao_id) else None
    ggn_growing = fazenda_growing.ggn_numero if fazenda_growing and fazenda_growing.ggn_numero else '—'
    codigo_producao = pallet.codigo_producao or '—'
    tp = romaneio.rastreabilidade_transporte if romaneio else None
    sp = romaneio.rastreabilidade_venda if romaneio else None

    nome_multilingue = te.cultura.nome_multilingue if te and te.cultura_id and te.cultura.nome_multilingue else '—'
    codigo_multilingue = codigo_ian or ''
    variedade = te.variedade if te and te.variedade else '—'
    classe = te.classe_categoria if te and te.classe_categoria else '—'
    peso = _fmt_kg(te.peso_liquido_cx) if te else '—'
    calibre = te.tipo_calibre if te and te.tipo_calibre else '—'
    chave_extra = te.codigo_chave_extra if te and te.codigo_chave_extra else ''
    chave_semana = pallet.codigo_chave_semana
    responsavel = romaneio.cliente.ppwr_responsavel if (romaneio and romaneio.cliente.ppwr_responsavel) else '—'

    armazem = pallet.armazem
    packhouse_nome = armazem.nome
    packhouse_endereco = endereco_packhouse or armazem.localizacao or '—'
    packhouse_ggn = armazem.ggn_numero or '—'

    supplier_nome = supplier_fazenda.nome if supplier_fazenda else '—'
    supplier_ggn = (supplier_fazenda.ggn_numero or '—') if supplier_fazenda else '—'

    # Etiqueta em formato horizontal, mesmo tamanho físico da etiqueta de pallet
    # (95x130mm) só que deitada (130x95mm). Grade única de 2 colunas x N linhas,
    # seguindo a referência real do cliente: nome (esquerda) empilhado com IAN +
    # Country of origin (direita); Supplier/GGN/Key em linhas próprias à esquerda,
    # com o aviso PPWR ocupando essas 3 linhas de uma vez à direita. Fontes e
    # espaçamento bem compactos — o conteúdo é denso (2 blocos de 23 idiomas) e
    # o espaço físico é pequeno.
    metade = largura / 2

    origem_html = f'<b>Country of origin: Brazil</b><br/>{escape(_ORIGEM_TEXTO)}'
    packhouse_html = (
        f'<font size="5" color="#333333">Packhouse</font><br/>'
        f'<font size="6.6"><b>{escape(packhouse_nome)}</b></font><br/>'
        f'<font size="5.4">{escape(packhouse_endereco)}</font><br/>'
        f'<font size="5.4">GGN {escape(packhouse_ggn)}</font>'
    )
    key_valor = f'<b>{escape(codigo_producao)}</b> <font size="4.6" color="#666666">farm code</font> <b>{escape(chave_semana)}</b>'
    if chave_extra:
        key_valor = f'<b>{escape(chave_extra)}</b> | ' + key_valor
    key_html = f'<font size="5" color="#333333">Key</font><br/><font size="6.6">{key_valor}</font>'
    ppwr_html = (
        f'<font size="4.4">{escape(_PPWR_TEXTO)}</font><br/>'
        f'<font size="5.2" color="#000000">{escape(responsavel)}</font>'
    )
    reciclagem_codigo = material_transporte.codigo_reciclagem if (material_transporte and material_transporte.codigo_reciclagem) else None
    icone_reciclagem = _icone_reciclagem_cell(styles, reciclagem_codigo) if reciclagem_codigo else ''

    grade = [
        [Paragraph(escape(nome_multilingue), styles['multilingue_nome']), Paragraph(escape(codigo_multilingue), styles['ian'])],
        ['', Paragraph(origem_html, styles['origem'])],
        [_cell(styles, 'Grower', f'GGN {ggn_growing}'), _cell(styles, 'Klasse/Class/Cat.', classe)],
        [Paragraph(packhouse_html, styles['cell']), Paragraph(escape(peso), styles['packing_valor'])],
        [_cell(styles, 'Trac. Transp.', tp or '—'), _cell(styles, 'Variety', variedade)],
        [_cell(styles, 'Trac. Sales', sp or '—'), _cell(styles, 'Size', calibre)],
        [_cell(styles, 'Supplier', supplier_nome), Paragraph(ppwr_html, styles['ppwr_responsavel'])],
        [_cell(styles, 'GGN', supplier_ggn), ''],
        [Paragraph(key_html, styles['cell']), ''],
        [icone_reciclagem, ''],
    ]

    outer = Table(grade, colWidths=[metade, metade])
    outer.setStyle(TableStyle([
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 6), (1, 8)),
        ('BOX', (0, 0), (-1, -1), 1.3, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.8, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2.2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2.2),
        ('TOPPADDING', (0, 0), (-1, -1), 1.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2),
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

    # Endereço do Packhouse: vem do EnderecoFazenda da fazenda vinculada ao armazém
    # (Armazem.localizacao é só um rótulo curto, não endereço postal).
    from cadastros.models import EnderecoFazenda
    fazenda_ids_packhouse = {
        ctx['pallet'].armazem.fazenda_id for ctx in pallets_ctx if ctx['pallet'].armazem.fazenda_id
    }
    endereco_por_fazenda = {}
    if fazenda_ids_packhouse:
        for e in (
            EnderecoFazenda.objects
            .filter(fazenda_id__in=fazenda_ids_packhouse)
            .order_by('fazenda_id', '-padrao', 'id')
        ):
            endereco_por_fazenda.setdefault(e.fazenda_id, e.get_endereco_completo())

    # Código IAN: atribuído por cliente (cada retailer tem seu próprio catálogo de
    # artigos), não é campo direto do TipoEmbalagem — ver TipoEmbalagemCliente.
    from .models import TipoEmbalagemCliente
    pares_ian = {
        (ctx['pallet'].tipo_embalagem_id, ctx['romaneio'].cliente_id)
        for ctx in pallets_ctx if ctx['pallet'].tipo_embalagem_id and ctx.get('romaneio')
    }
    ian_por_par = {}
    if pares_ian:
        tipo_ids = {p[0] for p in pares_ian}
        cliente_ids = {p[1] for p in pares_ian}
        for tec in TipoEmbalagemCliente.objects.filter(
            tipo_embalagem_id__in=tipo_ids, cliente_id__in=cliente_ids, ativo=True,
        ):
            ian_por_par[(tec.tipo_embalagem_id, tec.cliente_id)] = tec.codigo_ian

    largura_pagina = 130 * mm
    altura_pagina = 95 * mm
    margem = 2 * mm
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
        endereco_packhouse = endereco_por_fazenda.get(pallet.armazem.fazenda_id) if pallet.armazem.fazenda_id else None
        codigo_ian = (
            ian_por_par.get((pallet.tipo_embalagem_id, romaneio.cliente_id))
            if (pallet.tipo_embalagem_id and romaneio) else None
        )
        story.append(_bloco_pallet(
            pallet, romaneio, largura_util, supplier_fazenda, material_transporte,
            lote_producao, endereco_packhouse, codigo_ian,
        ))
        if i < len(pallets_ctx) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
