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
from reportlab.graphics.shapes import Drawing, Path, Polygon, String
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Table, TableStyle

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


def _size_span_count(peso_liquido_cx, tipo_calibre, cultura_id, faixas_por_cultura):
    """Texto "Count {N} / {min} - {max}" impresso na etiqueta sob o rótulo
    "Size-span & count" — faixa de peso do fruto individual pro calibre, cadastrada
    em FaixaPesoCalibre (por cultura + peso do carton + Count) e passada aqui já
    indexada em `faixas_por_cultura`: {cultura_id: {(carton_kg, calibre_n): (min, max)}}."""
    if not tipo_calibre:
        return '—'
    try:
        calibre_n = int(str(tipo_calibre).strip())
        carton_kg = int(round(float(peso_liquido_cx)))
    except (TypeError, ValueError):
        return f'Count {escape(str(tipo_calibre))}'
    faixa = faixas_por_cultura.get(cultura_id, {}).get((carton_kg, calibre_n))
    if not faixa:
        return f'Count {calibre_n}'
    minimo, maximo = faixa
    fmt = lambda v: f'{v:.2f}'.replace('.', ',')
    return f'Count {calibre_n} / {fmt(minimo)} - {fmt(maximo)}kg'


def _styles():
    _registrar_fonte_dejavu()
    return {
        'multilingue_nome': ParagraphStyle(
            'multilingue_nome', fontName=_DEJAVU_FONT_NAME, fontSize=4.2, leading=4.8, textColor=colors.black,
        ),
        'ian': ParagraphStyle(
            'ian', fontName='Helvetica-Bold', fontSize=26, leading=26, alignment=TA_CENTER,
        ),
        'origem': ParagraphStyle(
            'origem', fontName=_DEJAVU_FONT_NAME, fontSize=3.6, leading=4.1, textColor=colors.HexColor('#333333'),
        ),
        'ppwr_responsavel': ParagraphStyle(
            'ppwr_responsavel', fontName=_DEJAVU_FONT_NAME, fontSize=4.4, leading=5.1, textColor=colors.black,
        ),
        'packing_valor': ParagraphStyle('packing_valor', fontName='Helvetica-Bold', fontSize=18, leading=19, alignment=TA_CENTER),
        'reciclagem': ParagraphStyle('reciclagem', fontName='Helvetica-Bold', fontSize=4.2, leading=5, alignment=TA_CENTER),
        'traceability': ParagraphStyle(
            'traceability', fontName='Helvetica', fontSize=5, leading=5.8, textColor=colors.HexColor('#8B0000'),
        ),
        # rótulo estreito à esquerda (Grower/Packhouse/Supplier/Key) — mesma posição
        # do template real: coluna A, vertical-centralizado ao lado do bloco de valor.
        'rotulo': ParagraphStyle('rotulo', fontName='Helvetica', fontSize=4.6, leading=5.2, textColor=colors.HexColor('#333333')),
        'rotulo_bold': ParagraphStyle('rotulo_bold', fontName='Helvetica-Bold', fontSize=4.6, leading=5.2, textColor=colors.HexColor('#333333')),
        # valor em linha única (Klasse/Class/Cat. I, GGN, Variety, Size) — label e
        # valor juntos na mesma linha, não empilhados.
        'valor_inline': ParagraphStyle('valor_inline', fontName='Helvetica-Bold', fontSize=6.2, leading=7.2, alignment=TA_CENTER),
        'nome_bloco': ParagraphStyle('nome_bloco', fontName='Helvetica-Bold', fontSize=6, leading=6.8, alignment=TA_CENTER),
        'endereco_bloco': ParagraphStyle('endereco_bloco', fontName='Helvetica', fontSize=4.8, leading=5.6, alignment=TA_CENTER),
        'key_valor': ParagraphStyle('key_valor', fontName='Helvetica-Bold', fontSize=5.4, leading=6.2, alignment=TA_CENTER),
    }


def _icone_reciclagem_drawing(numero, tam_pt):
    """Triângulo de reciclagem "thin line" desenhado como 3 segmentos retos (um por
    lado de um triângulo equilátero, sentido horário) com uma seta (chevron) na
    ponta de cada um — em vez do glifo Unicode ♻, cujos traços são grossos demais
    (substituído a pedido do usuário: "deixa o ícone mas fino as setas")."""
    cx = cy = tam_pt / 2
    raio = tam_pt * 0.42
    espessura = tam_pt * 0.055
    gap_inicio, gap_fim = 0.16, 0.80
    angulos = (90, 330, 210)  # sentido horário: topo, inferior-direita, inferior-esquerda
    vertices = [
        (cx + raio * math.cos(math.radians(a)), cy + raio * math.sin(math.radians(a)))
        for a in angulos
    ]
    d = Drawing(tam_pt, tam_pt)
    for i in range(3):
        x0, y0 = vertices[i]
        x1, y1 = vertices[(i + 1) % 3]
        sx, sy = x0 + (x1 - x0) * gap_inicio, y0 + (y1 - y0) * gap_inicio
        ex, ey = x0 + (x1 - x0) * gap_fim, y0 + (y1 - y0) * gap_fim
        segmento = Path(strokeColor=colors.black, strokeWidth=espessura, strokeLineCap=1, fillColor=None)
        segmento.moveTo(sx, sy)
        segmento.lineTo(ex, ey)
        d.add(segmento)

        dx, dy = ex - sx, ey - sy
        comprimento = math.hypot(dx, dy)
        ux, uy = dx / comprimento, dy / comprimento
        px, py = -uy, ux
        cabeca_comp = espessura * 2.4
        cabeca_larg = espessura * 1.7
        ponta = (ex + ux * cabeca_comp * 0.4, ey + uy * cabeca_comp * 0.4)
        esquerda = (ex - ux * cabeca_comp * 0.6 + px * cabeca_larg, ey - uy * cabeca_comp * 0.6 + py * cabeca_larg)
        direita = (ex - ux * cabeca_comp * 0.6 - px * cabeca_larg, ey - uy * cabeca_comp * 0.6 - py * cabeca_larg)
        d.add(Polygon(
            points=[ponta[0], ponta[1], esquerda[0], esquerda[1], direita[0], direita[1]],
            fillColor=colors.black, strokeColor=None,
        ))
    if numero:
        num_size = raio * 0.5
        d.add(String(
            cx, cy - num_size * 0.35, numero, fontName='Helvetica-Bold',
            fontSize=num_size, textAnchor='middle', fillColor=colors.black,
        ))
    return d


def _icone_reciclagem_cell(styles, codigo, tam_pt=14):
    """Ícone de reciclagem com o número do material dentro do triângulo (ver
    _icone_reciclagem_drawing) empilhado com a sigla do material embaixo (ex:
    ♻ com "20" dentro, "PAP" na linha de baixo)."""
    partes = codigo.split(None, 1)
    numero = partes[0] if partes else ''
    material = partes[1] if len(partes) > 1 else ''
    icone = _icone_reciclagem_drawing(numero, tam_pt)
    linhas = [[icone]]
    if material:
        linhas.append([Paragraph(escape(material), styles['reciclagem'])])
    t = Table(linhas)
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


def _bloco_pallet(
    pallet, romaneio, largura, altura, supplier_fazenda, material_transporte, lote_producao,
    endereco_packhouse, codigo_ian, codigo_key, codigo_referencia, faixas_por_cultura,
):
    styles = _styles()
    te = pallet.tipo_embalagem
    lp = lote_producao
    parceiro = pallet.ordem_embalagem.produtor_parceiro
    if parceiro:
        ggn_growing = parceiro.grower_ggn or '—'
    else:
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
    size_span = (
        _size_span_count(te.peso_liquido_cx, te.tipo_calibre, te.cultura_id, faixas_por_cultura)
        if te else '—'
    )
    chave_semana = pallet.codigo_chave_semana
    responsavel = romaneio.cliente.ppwr_responsavel if (romaneio and romaneio.cliente.ppwr_responsavel) else '—'

    armazem = pallet.armazem
    if parceiro:
        packhouse_nome = parceiro.packhouse_nome or armazem.nome
        packhouse_endereco = parceiro.packhouse_endereco or endereco_packhouse or armazem.localizacao or '—'
        packhouse_ggn = parceiro.packhouse_ggn or '—'
    else:
        packhouse_nome = armazem.nome
        packhouse_endereco = endereco_packhouse or armazem.localizacao or '—'
        packhouse_ggn = armazem.ggn_numero or '—'

    supplier_nome = supplier_fazenda.nome if supplier_fazenda else '—'
    supplier_ggn = (supplier_fazenda.ggn_numero or '—') if supplier_fazenda else '—'

    # Etiqueta em formato horizontal, mesmo tamanho físico da etiqueta de pallet
    # (95x130mm) só que deitada (130x95mm). Grade de 6 colunas x 13 linhas que
    # replica exatamente as mesclagens/proporções do template real do cliente
    # ("GLOBAL STICKER_melão.xlsx"): colunas A-F com larguras proporcionais às
    # do Excel, e cada mesclagem (Grower/GGN lado a lado, rótulos Packhouse/
    # Supplier/Key numa coluna estreita ao lado do bloco de valor, etc.) traduzida
    # 1:1 para SPANs do reportlab.
    fracoes_col = [12.42578125, 20.28515625, 12.0, 26.42578125, 2.0, 75.0]
    soma_fracoes = sum(fracoes_col)
    col_w = [largura * f / soma_fracoes for f in fracoes_col]

    origem_html = f'<b>Country of origin: Brazil</b><br/>{escape(_ORIGEM_TEXTO)}'
    key_col_b = f'{escape(codigo_producao)}'
    if codigo_key:
        key_col_b = f'{escape(codigo_key)} | ' + key_col_b
    ppwr_html = (
        f'<font size="4.4">{escape(_PPWR_TEXTO)}</font><br/>'
        f'<font size="5.2" color="#000000">{escape(responsavel)}</font>'
    )
    reciclagem_codigo = material_transporte.codigo_reciclagem if (material_transporte and material_transporte.codigo_reciclagem) else None
    icone_reciclagem = _icone_reciclagem_cell(styles, reciclagem_codigo, tam_pt=40) if reciclagem_codigo else ''
    ppwr_bloco = Table(
        [[Paragraph(ppwr_html, styles['ppwr_responsavel'])], [icone_reciclagem]],
        colWidths=[col_w[3] + col_w[4] + col_w[5] - 4],
    )
    ppwr_bloco.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('ALIGN', (0, 1), (0, 1), 'RIGHT'),
    ]))
    traceability_html = (
        f'Production: <b>{escape(codigo_producao)}</b> &#183; '
        f'Transport package: <b>{escape(tp or "—")}</b> &#183; Sales package: <b>{escape(sp or "—")}</b>'
    )

    vazio = ''
    grade = [
        # linha 1 (Excel row1): nome (A:E, span rows1-2) | IAN (F)
        [Paragraph(escape(nome_multilingue), styles['multilingue_nome']), vazio, vazio, vazio, vazio,
         Paragraph(escape(codigo_multilingue), styles['ian'])],
        # linha 2 (row2): nome continua | Country of origin (F)
        [vazio, vazio, vazio, vazio, vazio, Paragraph(origem_html, styles['origem'])],
        # linha 3 (row3): Grower | GGN (B:E) | Klasse/Class/Cat. + valor (F)
        [Paragraph('Grower', styles['rotulo']), Paragraph(f'GGN {escape(ggn_growing)}', styles['valor_inline']), vazio, vazio, vazio,
         Paragraph(f'Klasse/Class/Cat. {escape(classe)}', styles['valor_inline'])],
        # linha 4 (row4): Packhouse (A, span rows4-7) | nome (B:E) | peso (F, span rows4-5)
        [Paragraph('Packhouse', styles['rotulo']), Paragraph(escape(packhouse_nome), styles['nome_bloco']), vazio, vazio, vazio,
         Paragraph(escape(peso), styles['packing_valor'])],
        # linha 5 (row5): Packhouse continua | endereço (B:E, span rows5-6) | peso continua
        [vazio, Paragraph(escape(packhouse_endereco), styles['endereco_bloco']), vazio, vazio, vazio, vazio],
        # linha 6 (row6): Packhouse continua | endereço continua | Variety (F, span rows6-7)
        [vazio, vazio, vazio, vazio, vazio, Paragraph(escape(variedade), styles['valor_inline'])],
        # linha 7 (row7): Packhouse continua | GGN (B:E) | Variety continua
        [vazio, Paragraph(f'GGN {escape(packhouse_ggn)}', styles['valor_inline']), vazio, vazio, vazio, vazio],
        # linha 8 (row8): Supplier (A, span rows8-9) | nome (B:E) | Count/faixa de peso (F — ocupa a
        # célula onde o template tinha o rótulo "Size-span & count", que não é impresso)
        [Paragraph('Supplier', styles['rotulo']), Paragraph(escape(supplier_nome), styles['nome_bloco']), vazio, vazio, vazio,
         Paragraph(escape(size_span), styles['key_valor'])],
        # linha 9 (row9): Supplier continua | GGN (B:E) | código de referência do cliente (F)
        [vazio, Paragraph(f'GGN {escape(supplier_ggn)}', styles['valor_inline']), vazio, vazio, vazio,
         Paragraph(escape(codigo_referencia) if codigo_referencia else '—', styles['key_valor'])],
        # linha 10 (row10): Key (A, span rows10-12) | código produção (B, span) | farm code (C, span) | PPWR+ícone (D:F, span)
        [Paragraph('Key', styles['rotulo_bold']), Paragraph(key_col_b, styles['key_valor']), Paragraph(escape(chave_semana), styles['key_valor']),
         ppwr_bloco, vazio, vazio],
        [vazio, vazio, vazio, vazio, vazio, vazio],
        [vazio, vazio, vazio, vazio, vazio, vazio],
        # linha 13 (row13): Traceability (A:B) | Production/TP/SP (C:F)
        [Paragraph('Traceability', styles['rotulo_bold']), vazio,
         Paragraph(traceability_html, styles['traceability']), vazio, vazio, vazio],
    ]

    estilo_tabela = TableStyle([
        ('SPAN', (0, 0), (4, 1)),    # nome
        ('SPAN', (1, 2), (4, 2)),    # Grower: GGN
        ('SPAN', (0, 3), (0, 6)),    # Packhouse (rótulo)
        ('SPAN', (1, 3), (4, 3)),    # Packhouse: nome
        ('SPAN', (5, 3), (5, 4)),    # peso
        ('SPAN', (1, 4), (4, 5)),    # endereço packhouse
        ('SPAN', (5, 5), (5, 6)),    # Variety
        ('SPAN', (1, 6), (4, 6)),    # Packhouse: GGN
        ('SPAN', (0, 7), (0, 8)),    # Supplier (rótulo)
        ('SPAN', (1, 7), (4, 7)),    # Supplier: nome
        ('SPAN', (1, 8), (4, 8)),    # Supplier: GGN
        ('SPAN', (0, 9), (0, 11)),   # Key (rótulo)
        ('SPAN', (1, 9), (1, 11)),   # código de produção
        ('SPAN', (2, 9), (2, 11)),   # farm code
        ('SPAN', (3, 9), (5, 11)),   # PPWR + ícone
        ('SPAN', (0, 12), (1, 12)),  # "Traceability"
        ('SPAN', (2, 12), (5, 12)),  # Production/TP/SP
        ('BOX', (0, 0), (-1, -1), 1.3, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('VALIGN', (3, 9), (5, 11), 'TOP'),
        ('ALIGN', (1, 2), (1, 2), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1.4),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
    ])

    outer = Table(grade, colWidths=col_w)
    outer.setStyle(estilo_tabela)

    # Mede a altura natural e estica só as ALTURAS das linhas (não a fonte) pra
    # ocupar a página inteira, igual à etiqueta de pallet (pdf_pallet.py) — sem
    # sobra de espaço em branco no rodapé.
    outer.wrap(largura, altura * 10)
    linhas_naturais = list(outer._rowHeights)
    soma_natural = sum(linhas_naturais)
    if soma_natural and soma_natural < altura:
        fator_altura = altura / soma_natural
        linhas_finais = [h * fator_altura for h in linhas_naturais]
        outer = Table(grade, colWidths=col_w, rowHeights=linhas_finais)
        outer.setStyle(estilo_tabela)

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

    # Código IAN / Key / Referência: atribuídos por cliente à família do produto
    # (cultura/produto + variedade + marca) — não mudam por calibre/peso de caixa
    # (confirmado com a fazenda), por isso não são campos diretos do TipoEmbalagem
    # nem chaveados por ele. Ver TipoEmbalagemCliente.
    from .models import TipoEmbalagemCliente
    pares_cliente = {
        ctx['pallet'].tipo_embalagem.identidade_ian + (ctx['romaneio'].cliente_id,)
        for ctx in pallets_ctx if ctx['pallet'].tipo_embalagem_id and ctx.get('romaneio')
    }
    codigos_por_par = {}
    if pares_cliente:
        cliente_ids = {p[-1] for p in pares_cliente}
        for tec in TipoEmbalagemCliente.objects.filter(cliente_id__in=cliente_ids, ativo=True):
            codigos_por_par[tec.identidade_ian + (tec.cliente_id,)] = tec

    # Faixas de peso por calibre ("Count"), por cultura + peso do carton — ver
    # FaixaPesoCalibre. Cadastrado por empresa, não por cliente (a faixa de peso do
    # fruto é uma característica do produto, não do retailer).
    from .models import FaixaPesoCalibre
    cultura_ids = {
        ctx['pallet'].tipo_embalagem.cultura_id
        for ctx in pallets_ctx if ctx['pallet'].tipo_embalagem_id and ctx['pallet'].tipo_embalagem.cultura_id
    }
    faixas_por_cultura = {}
    if cultura_ids:
        for f in FaixaPesoCalibre.objects.filter(
            empresa_id__in=empresa_ids, cultura_id__in=cultura_ids, ativo=True,
        ):
            carton_kg = int(round(float(f.peso_carton)))
            faixas_por_cultura.setdefault(f.cultura_id, {})[(carton_kg, f.calibre)] = (
                float(f.peso_minimo), float(f.peso_maximo),
            )

    largura_pagina = 130 * mm
    altura_pagina = 95 * mm
    margem = 2 * mm
    largura_util = largura_pagina - 2 * margem
    altura_util = altura_pagina - 2 * margem

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=(largura_pagina, altura_pagina),
        leftMargin=margem, rightMargin=margem, topMargin=margem, bottomMargin=margem,
    )
    # Frame sem padding interno (o padrão do reportlab é 6pt por lado, o que
    # reduziria a área útil real e faria a etiqueta — já dimensionada pra
    # preencher exatamente a página — estourar pra uma segunda página.
    frame = Frame(
        margem, margem, largura_util, altura_util,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id='etiqueta', frames=[frame])])
    story = []
    for i, ctx in enumerate(pallets_ctx):
        pallet = ctx['pallet']
        romaneio = ctx.get('romaneio')
        supplier_fazenda = supplier_por_empresa.get(pallet.empresa_id)
        material_transporte = material_por_romaneio.get(romaneio.pk) if romaneio else None
        lote_producao = lote_producao_por_ordem.get(pallet.ordem_embalagem_id)
        endereco_packhouse = endereco_por_fazenda.get(pallet.armazem.fazenda_id) if pallet.armazem.fazenda_id else None
        tec = (
            codigos_por_par.get(pallet.tipo_embalagem.identidade_ian + (romaneio.cliente_id,))
            if (pallet.tipo_embalagem_id and romaneio) else None
        )
        story.append(_bloco_pallet(
            pallet, romaneio, largura_util, altura_util, supplier_fazenda, material_transporte,
            lote_producao, endereco_packhouse,
            tec.codigo_ian if tec else None, tec.codigo_key if tec else None,
            tec.codigo_referencia if tec else None, faixas_por_cultura,
        ))
        if i < len(pallets_ctx) - 1:
            story.append(PageBreak())
    doc.build(story)
    buffer.seek(0)
    return buffer.read()
