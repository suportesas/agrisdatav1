"""Geração da etiqueta avulsa via reportlab puro — mesmo padrão visual e mesmo
motivo do embalagem/pdf_pallet.py (evita o bug do xhtml2pdf e dá controle preciso
de layout para o tamanho físico real da etiqueta, 95x130mm). Ícones e bandeira são
desenhados como vetor (reportlab.graphics) em vez de fonte de ícones/emoji.

A etiqueta avulsa não nasce de uma OrdemEmbalagem/Romaneio (pallet pronto de
terceiro ou gerado fora do fluxo normal de embalagem), por isso os campos de
rastreabilidade de transporte/venda e o tipo de embalagem cadastrado não existem
aqui — os campos equivalentes vêm do cabeçalho do lote (LoteEtiquetaAvulsa) e da
própria etiqueta avulsa (EtiquetaAvulsa). Ver embalagem/pdf_pallet.py para o
layout de referência.

A etiqueta NUNCA quebra para uma segunda página (não faz sentido fisicamente para
uma etiqueta impressa): o conteúdo é montado a fator de fonte 1.0 e, se não
couber, o fator é reduzido em passos até caber; se sobrar espaço, as linhas são
esticadas (só a altura, não a fonte) para preencher a página inteira.
"""
import base64
import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, Rect
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Table, TableStyle,
)

from core.barcode_utils import barcode_b64, qrcode_b64

LARGURA_PAGINA = 95 * mm
ALTURA_PAGINA = 130 * mm
MARGEM = 2 * mm
LARGURA_UTIL = LARGURA_PAGINA - 2 * MARGEM
ALTURA_UTIL = ALTURA_PAGINA - 2 * MARGEM

_VERDE = colors.HexColor('#1a7a3c')
_AZUL = colors.HexColor('#2563eb')

_FATOR_MINIMO = 0.55
_PASSO_REDUCAO = 0.92

_PISO_FONTE_VALOR = 5.5
_PISO_FONTE_TITULO = 6.5


def _fonte_para_caber(texto, fonte, tamanho_base, largura_disponivel, piso):
    """Reduz o tamanho da fonte em passos de 0.2pt até `texto` caber em uma única
    linha dentro de `largura_disponivel` (pt), sem passar do piso — abaixo do piso,
    o texto volta ao tamanho mínimo e deixa o Paragraph quebrar linha normalmente."""
    tamanho = tamanho_base
    if not texto:
        return tamanho_base
    while tamanho > piso and stringWidth(str(texto), fonte, tamanho) > largura_disponivel:
        tamanho -= 0.2
    return round(max(tamanho, piso), 2)


def _styles(fator):
    return {
        'titulo': ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=12.6 * fator, alignment=TA_CENTER, leading=14.3 * fator),
        'empresa': ParagraphStyle('empresa', fontName='Helvetica-Bold', fontSize=9.9 * fator, leading=11.3 * fator),
        'importador': ParagraphStyle('importador', fontName='Helvetica-Bold', fontSize=9.1 * fator, leading=10.8 * fator),
        'produto_tag': ParagraphStyle('produto_tag', fontName='Helvetica-Bold', fontSize=9.9 * fator, leading=11.3 * fator),
        'cell': ParagraphStyle('cell', fontName='Helvetica', fontSize=9.1 * fator, leading=10.6 * fator),
        'footer': ParagraphStyle(
            'footer', fontName='Helvetica-Bold', fontSize=6.4 * fator, alignment=TA_CENTER, leading=7.4 * fator,
        ),
        'bc_codigo': ParagraphStyle(
            'bc_codigo', fontName='Courier-Bold', fontSize=7.7 * fator, alignment=TA_CENTER, leading=8.8 * fator,
        ),
        'qr_legenda': ParagraphStyle('qr_legenda', fontName='Helvetica', fontSize=5.9 * fator, alignment=TA_CENTER, leading=7.1 * fator),
    }


# ──────────────────────────── ícones vetoriais ────────────────────────────

def _icone_bandeira_brasil(tam):
    d = Drawing(tam * 1.4, tam)
    w, h = tam * 1.4, tam
    d.add(Rect(0, 0, w, h, fillColor=_VERDE, strokeColor=None))
    d.add(Polygon([w * 0.5, h * 0.9, w * 0.1, h * 0.5, w * 0.5, h * 0.1, w * 0.9, h * 0.5],
                  fillColor=colors.HexColor('#f6c500'), strokeColor=None))
    d.add(Circle(w * 0.5, h * 0.5, h * 0.22, fillColor=_AZUL, strokeColor=None))
    return d


def _icone_tag(tam):
    d = Drawing(tam, tam)
    d.add(Polygon([0, tam * 0.6, tam * 0.4, tam, tam, tam * 0.4, tam * 0.6, 0],
                  fillColor=None, strokeColor=colors.black, strokeWidth=0.9))
    d.add(Circle(tam * 0.28, tam * 0.72, tam * 0.08, fillColor=colors.black, strokeColor=None))
    return d


def _icone_termometro(tam):
    d = Drawing(tam, tam * 1.6)
    cx = tam * 0.5
    d.add(Rect(cx - tam * 0.12, tam * 0.35, tam * 0.24, tam * 1.1, strokeColor=colors.black,
               fillColor=None, strokeWidth=0.9))
    d.add(Circle(cx, tam * 0.28, tam * 0.28, fillColor=colors.black, strokeColor=None))
    d.add(Rect(cx - tam * 0.06, tam * 0.45, tam * 0.12, tam * 0.75, fillColor=colors.black, strokeColor=None))
    return d


def _icone_navio(tam):
    d = Drawing(tam * 1.3, tam)
    w, h = tam * 1.3, tam
    d.add(Polygon([w * 0.1, h * 0.35, w * 0.9, h * 0.35, w * 0.75, h * 0.05, w * 0.25, h * 0.05],
                  fillColor=colors.black, strokeColor=None))
    d.add(Rect(w * 0.35, h * 0.4, w * 0.3, h * 0.35, fillColor=colors.black, strokeColor=None))
    d.add(Line(0, h * 0.02, w, h * 0.02, strokeColor=colors.black, strokeWidth=0.9))
    return d


def _icone_pin(tam):
    d = Drawing(tam, tam * 1.3)
    cx = tam * 0.5
    d.add(Circle(cx, tam * 0.85, tam * 0.42, fillColor=None, strokeColor=colors.black, strokeWidth=0.9))
    d.add(Circle(cx, tam * 0.85, tam * 0.14, fillColor=colors.black, strokeColor=None))
    d.add(Polygon([cx - tam * 0.18, tam * 0.55, cx + tam * 0.18, tam * 0.55, cx, 0],
                  fillColor=colors.black, strokeColor=None))
    return d


# ──────────────────────────── helpers de célula ────────────────────────────

def _cell(styles, fator, label, valor, largura_col, icone=None):
    """largura_col: largura total da coluna (pt) — usada para calcular o maior
    tamanho de fonte do valor que ainda cabe em uma única linha, sem quebrar."""
    icone_espaco = (icone.width + 1.4 * mm) if icone else 0
    largura_texto = largura_col - 2 * 2.2 * mm - icone_espaco
    tam_valor = _fonte_para_caber(valor, 'Helvetica-Bold', 9 * fator, largura_texto, _PISO_FONTE_VALOR * fator)
    p = Paragraph(
        f'<font size="{6.2 * fator:.2f}" color="#333333">{escape(str(label))}</font><br/>'
        f'<font size="{tam_valor:.2f}"><b>{escape(str(valor))}</b></font>',
        styles['cell'],
    )
    if icone is None:
        return p
    t = Table([[icone, p]], colWidths=[icone.width + 1.4 * mm, None])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 1.4 * mm), ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return t


def _grid_row(cells, col_widths, fator):
    t = Table([cells], colWidths=col_widths)
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 2.2 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 2.2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 0.6 * mm * fator), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.6 * mm * fator),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEAFTER', (0, 0), (-2, 0), 0.8, colors.black),
    ]))
    return t


def _linha_unica(flowable, fator, padding=0.6):
    t = Table([[flowable]], colWidths=[LARGURA_UTIL])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 2.2 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 2.2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), padding * fator * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), padding * fator * mm),
    ]))
    return t


def _logo_empresa(empresa, altura):
    if not empresa.logo:
        return None
    try:
        data = empresa.logo.open('rb').read()
        img = Image(io.BytesIO(data))
        proporcao = img.imageWidth / img.imageHeight
        img.drawHeight = altura
        img.drawWidth = altura * proporcao
        return img
    except Exception:
        return None


def _montar_linhas(etiqueta, lote, barcode_data, qr_url, fator):
    """Monta a lista de flowables (uma por linha/seção) da etiqueta, com todos os
    tamanhos (fonte, ícones, imagens, padding) escalados por `fator`."""
    styles = _styles(fator)
    fazenda = lote.fazenda
    ggn = fazenda.ggn_numero if (fazenda and fazenda.ggn_numero) else '—'
    produto_nome = etiqueta.produto_nome or '—'
    if etiqueta.variedade:
        produto_nome = f'{produto_nome} / {etiqueta.variedade}'
    cultivar = etiqueta.cultivares or '—'
    peso = f'{float(etiqueta.peso_liquido_cx):.1f}'.replace('.', ',') + ' kg' if etiqueta.peso_liquido_cx else '—'
    tamanho = etiqueta.tipo_size or '—'
    temperatura = f'{etiqueta.temperatura}°C' if etiqueta.temperatura else '—'
    navio = lote.navio_nome or '—'
    porto_origem = lote.porto_origem_nome or '—'
    porto_destino = lote.porto_destino_nome or None
    lote_num = lote.numero_lote or '—'
    importador = lote.cliente_nome or None
    marca = etiqueta.marca_nome or '—'
    carimbo = etiqueta.carimbo or '—'
    data_etiqueta = timezone.localtime(etiqueta.criado_em)

    linhas = []
    linhas.append(_linha_unica(Paragraph('ETIQUETA PARA PALLET', styles['titulo']), fator, padding=1.6))

    logo = _logo_empresa(etiqueta.empresa, altura=9.35 * mm * fator)
    largura_logo = 10.7 * mm * fator if logo else 0
    col_empresa = LARGURA_UTIL * 0.46 if importador else LARGURA_UTIL
    largura_texto_empresa = col_empresa - 2 * 2.2 * mm - largura_logo - 1.4 * mm
    tam_empresa = _fonte_para_caber(etiqueta.empresa.nome, 'Helvetica-Bold', 9.9 * fator, largura_texto_empresa, _PISO_FONTE_TITULO * fator)
    estilo_empresa = ParagraphStyle('empresa_dyn', parent=styles['empresa'], fontSize=tam_empresa, leading=tam_empresa * 1.14)
    empresa_cell = Table(
        [[logo, Paragraph(escape(etiqueta.empresa.nome), estilo_empresa)]] if logo else [[Paragraph(escape(etiqueta.empresa.nome), estilo_empresa)]],
        colWidths=([largura_logo, None] if logo else [None]),
    )
    empresa_cell.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 1.4 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    if importador:
        largura_importador = LARGURA_UTIL * 0.54 - 2 * 2.2 * mm
        tam_importador = _fonte_para_caber(importador, 'Helvetica-Bold', 9.1 * fator, largura_importador, _PISO_FONTE_TITULO * fator)
        imp_txt = f'<font size="{tam_importador:.2f}"><b>{escape(importador)}</b></font>'
        if porto_destino:
            tam_porto = _fonte_para_caber(porto_destino, 'Helvetica-Bold', 8.7 * fator, largura_importador, _PISO_FONTE_TITULO * fator)
            imp_txt += (
                f'<br/><font size="{6.6 * fator:.2f}" color="#333333">Port of Destination:</font>'
                f'<br/><font size="{tam_porto:.2f}"><b>{escape(porto_destino)}</b></font>'
            )
        importador_cell = Paragraph(imp_txt, styles['importador'])
        linhas.append(_grid_row([empresa_cell, importador_cell], [LARGURA_UTIL * 0.46, LARGURA_UTIL * 0.54], fator))
    else:
        linhas.append(_grid_row([empresa_cell], [LARGURA_UTIL], fator))

    largura_produto = LARGURA_UTIL - 2 * 2.2 * mm - 5.1 * mm * fator - 2.2 * mm
    tam_produto = _fonte_para_caber(produto_nome, 'Helvetica-Bold', 9.9 * fator, largura_produto, _PISO_FONTE_TITULO * fator)
    estilo_produto = ParagraphStyle('produto_dyn', parent=styles['produto_tag'], fontSize=tam_produto, leading=tam_produto * 1.14)
    tag_cell = Table(
        [[_icone_tag(4.4 * mm * fator), Paragraph(escape(produto_nome), estilo_produto)]],
        colWidths=[5.1 * mm * fator, None],
    )
    tag_cell.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 2.2 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    linhas.append(_linha_unica(tag_cell, fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'Country of Origin', 'Brazil', LARGURA_UTIL * 0.55, icone=_icone_bandeira_brasil(5.1 * mm * fator)),
        _cell(styles, fator, 'Cultivar', cultivar, LARGURA_UTIL * 0.45),
    ], [LARGURA_UTIL * 0.55, LARGURA_UTIL * 0.45], fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'GGN', ggn, LARGURA_UTIL / 2),
        _cell(styles, fator, 'Packhouse', etiqueta.empresa.nome, LARGURA_UTIL / 2),
    ], [LARGURA_UTIL / 2, LARGURA_UTIL / 2], fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'Packaging', peso, LARGURA_UTIL / 3),
        _cell(styles, fator, 'Size', tamanho, LARGURA_UTIL / 3),
        _cell(styles, fator, 'Count', f'{etiqueta.caixas} boxes', LARGURA_UTIL / 3),
    ], [LARGURA_UTIL / 3] * 3, fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'Brand', marca, LARGURA_UTIL / 2),
        _cell(styles, fator, 'Trace Code', carimbo, LARGURA_UTIL / 2),
    ], [LARGURA_UTIL / 2, LARGURA_UTIL / 2], fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'Temperature', temperatura, LARGURA_UTIL * 0.30, icone=_icone_termometro(3.7 * mm * fator)),
        _cell(styles, fator, 'Vessel', navio, LARGURA_UTIL * 0.38, icone=_icone_navio(4.7 * mm * fator)),
        _cell(styles, fator, 'Port of Origin', porto_origem, LARGURA_UTIL * 0.32, icone=_icone_pin(3.7 * mm * fator)),
    ], [LARGURA_UTIL * 0.30, LARGURA_UTIL * 0.38, LARGURA_UTIL * 0.32], fator))

    linhas.append(_grid_row([
        _cell(styles, fator, 'Lot', lote_num, LARGURA_UTIL * 0.68),
        _cell(styles, fator, 'Date', data_etiqueta.strftime('%d/%m/%Y'), LARGURA_UTIL * 0.32),
    ], [LARGURA_UTIL * 0.68, LARGURA_UTIL * 0.32], fator))

    qr_cell_conteudo = [Paragraph(f'<font size="{6.6 * fator:.2f}"><b>ROUTE (ORIGIN / DESTINATION)</b></font>', styles['qr_legenda'])]
    if qr_url:
        qr_png = qrcode_b64(qr_url)
        if qr_png:
            qr_img = Image(io.BytesIO(base64.b64decode(qr_png)))
            qr_img.drawWidth = 16 * mm * fator
            qr_img.drawHeight = 16 * mm * fator
            qr_cell_conteudo.append(qr_img)
            qr_cell_conteudo.append(Paragraph('Scan to view route on maps', styles['qr_legenda']))
    else:
        qr_cell_conteudo.append(Paragraph('—', styles['qr_legenda']))

    bc_cell_conteudo = [Paragraph(f'<font size="{6.6 * fator:.2f}"><b>BARCODE</b></font>', styles['qr_legenda'])]
    bc_png = barcode_b64(barcode_data)
    if bc_png:
        bc_img = Image(io.BytesIO(base64.b64decode(bc_png)))
        bc_img.drawWidth = LARGURA_UTIL * 0.42
        bc_img.drawHeight = 7.9 * mm * fator
        bc_cell_conteudo.append(bc_img)
    bc_cell_conteudo.append(Paragraph(escape(barcode_data), styles['bc_codigo']))

    qr_table = Table([[qr_cell_conteudo, bc_cell_conteudo]], colWidths=[LARGURA_UTIL / 2, LARGURA_UTIL / 2])
    qr_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 1.4 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 1.4 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 0.7 * mm * fator), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.7 * mm * fator),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LINEAFTER', (0, 0), (0, 0), 0.8, colors.black),
    ]))
    linhas.append(qr_table)

    linhas.append(_linha_unica(
        Paragraph('MANTENHA ESTA ETIQUETA LEGÍVEL DURANTE TODO O TRANSPORTE', styles['footer']), fator, padding=0.6,
    ))
    return linhas


def _bloco_etiqueta(etiqueta, lote, barcode_data, qr_url):
    """Monta a etiqueta de um pallet avulso garantindo que SEMPRE cabe em uma
    única página: tenta fator de fonte 1.0; se o conteúdo natural for maior que
    a área disponível, reduz o fator em passos até caber (nunca corta/sobrepõe
    texto). Depois, se sobrar espaço, estica só a ALTURA das linhas (não a
    fonte) para preencher a página."""
    fator = 1.0
    linhas = _montar_linhas(etiqueta, lote, barcode_data, qr_url, fator)
    alturas_naturais = [f.wrap(LARGURA_UTIL, ALTURA_UTIL)[1] for f in linhas]
    soma_natural = sum(alturas_naturais)

    while soma_natural > ALTURA_UTIL and fator > _FATOR_MINIMO:
        fator = max(fator * _PASSO_REDUCAO, _FATOR_MINIMO)
        linhas = _montar_linhas(etiqueta, lote, barcode_data, qr_url, fator)
        alturas_naturais = [f.wrap(LARGURA_UTIL, ALTURA_UTIL)[1] for f in linhas]
        soma_natural = sum(alturas_naturais)

    alvo = ALTURA_UTIL * 0.985  # pequena margem de segurança
    escala_altura = alvo / soma_natural if soma_natural else 1
    escala_altura = max(escala_altura, 1.0)
    alturas_finais = [h * escala_altura for h in alturas_naturais]

    outer = Table([[l] for l in linhas], colWidths=[LARGURA_UTIL], rowHeights=alturas_finais)
    outer.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.3, colors.black),
        ('LINEBELOW', (0, 0), (-1, -2), 0.8, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return outer


def _rota_maps_url(porto_origem, porto_destino):
    if not porto_origem or not porto_destino:
        return None
    from urllib.parse import quote
    origem = f'{porto_origem.cidade}, {porto_origem.pais}'
    destino = f'{porto_destino.cidade}, {porto_destino.pais}'
    return f'https://www.google.com/maps/dir/?api=1&origin={quote(origem)}&destination={quote(destino)}'


def render_etiqueta_avulsa_pdf(etiquetas):
    """Gera PDF com uma etiqueta por página para cada EtiquetaAvulsa informada."""
    from .models import EtiquetaAvulsa

    ids_ordenados = [e.pk for e in etiquetas]
    etiquetas_por_pk = {
        e.pk: e for e in EtiquetaAvulsa.objects.filter(pk__in=ids_ordenados).select_related(
            'empresa', 'produto', 'marca', 'cultura',
            'lote__fazenda', 'lote__cliente', 'lote__porto_origem', 'lote__porto_destino', 'lote__navio',
        )
    }
    etiquetas = [etiquetas_por_pk[pk] for pk in ids_ordenados if pk in etiquetas_por_pk]

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=(LARGURA_PAGINA, ALTURA_PAGINA),
        leftMargin=MARGEM, rightMargin=MARGEM, topMargin=MARGEM, bottomMargin=MARGEM,
    )
    # Frame customizado sem padding interno (o padrão do reportlab é 6pt por lado,
    # o que reduzia a área útil real e fazia o conteúdo — já dimensionado para
    # preencher exatamente a página — estourar para uma segunda página.
    frame = Frame(
        MARGEM, MARGEM, LARGURA_UTIL, ALTURA_UTIL,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id='etiqueta', frames=[frame])])
    story = []
    for i, etiqueta in enumerate(etiquetas):
        lote = etiqueta.lote
        qr_url = _rota_maps_url(lote.porto_origem, lote.porto_destino)
        story.append(_bloco_etiqueta(etiqueta, lote, etiqueta.codigo_pallet, qr_url))
        if i < len(etiquetas) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
