"""
Utilitarios para geracao de relatorios de clientes em PDF e Excel
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side


def _create_logo_cell(logo_field, max_width, max_height):
    try:
        try:
            logo_source = logo_field.path
        except NotImplementedError:
            # Storage remoto (ex: Supabase) nao suporta path local: baixa via URL
            import urllib.request
            logo_source = io.BytesIO(urllib.request.urlopen(logo_field.url, timeout=5).read())
        reader = ImageReader(logo_source)
        img_width, img_height = reader.getSize()
        if not img_width or not img_height:
            return ''
        scale = min(max_width / img_width, max_height / img_height)
        if hasattr(logo_source, 'seek'):
            logo_source.seek(0)
        return Image(logo_source, width=img_width * scale, height=img_height * scale)
    except Exception:
        return ''


class RelatorioClientesPDF:
    def __init__(self, empresa, titulo='Relatorio de Clientes'):
        self.empresa = empresa
        self.titulo = titulo
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.5 * inch,
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER,
        ))

    def adicionar_cabecalho(self, filtros_desc=''):
        info_texto = f'<b>Empresa:</b> {self.empresa.nome}<br/>'
        info_texto += f'<b>Gerado em:</b> {datetime.now().strftime("%d/%m/%Y as %H:%M")}<br/>'
        if filtros_desc:
            info_texto += f'<b>Filtros:</b> {filtros_desc}'

        logo_cell = ''
        try:
            if getattr(self.empresa, 'logo', None) and self.empresa.logo.name:
                logo_cell = _create_logo_cell(self.empresa.logo, 1.6 * inch, 1.0 * inch)
        except Exception:
            logo_cell = ''

        header_table = Table(
            [[logo_cell, Paragraph(info_texto, self.styles['Subtitle'])]],
            colWidths=[1.8 * inch, 4.8 * inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(header_table)
        self.story.append(Spacer(1, 0.12 * inch))
        self.story.append(Paragraph(self.titulo, self.styles['CustomTitle']))
        self.story.append(Spacer(1, 0.3 * inch))

    def adicionar_tabela(self, clientes):
        if not clientes.exists():
            self.story.append(Paragraph('Nenhum cliente encontrado com os criterios especificados.', self.styles['Normal']))
            return

        dados = [['Razao Social', 'CNPJ/CPF', 'Mercado', 'Status']]

        for cliente in clientes:
            dados.append([
                (cliente.razao_social or '')[:50],
                cliente.cnpj_cpf or '',
                cliente.get_tipo_cliente_display(),
                cliente.get_status_display(),
            ])

        tabela = Table(dados, colWidths=[3.2 * inch, 1.5 * inch, 1.2 * inch, 0.9 * inch])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        self.story.append(tabela)

    def gerar(self):
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer.getvalue()


class RelatorioClientePDF:
    def __init__(self, empresa, cliente, titulo='Cadastro de Cliente'):
        self.empresa = empresa
        self.cliente = cliente
        self.titulo = titulo
        self.buffer = io.BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.5 * inch,
        )
        self.styles = getSampleStyleSheet()
        self.story = []
        self._setup_styles()

    def _setup_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER,
        ))

        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#1f4788'),
            spaceBefore=10,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

    def _fmt(self, value, default='—'):
        if value is None or value == '':
            return default
        return str(value)

    def adicionar_cabecalho(self):
        info_texto = f'<b>Empresa:</b> {self.empresa.nome}<br/>'
        info_texto += f'<b>Gerado em:</b> {datetime.now().strftime("%d/%m/%Y as %H:%M")}<br/>'
        info_texto += f'<b>Cliente:</b> {self.cliente.razao_social}'

        logo_cell = ''
        try:
            if getattr(self.empresa, 'logo', None) and self.empresa.logo.name:
                logo_cell = _create_logo_cell(self.empresa.logo, 1.6 * inch, 1.0 * inch)
        except Exception:
            logo_cell = ''

        header_table = Table(
            [[logo_cell, Paragraph(info_texto, self.styles['Subtitle'])]],
            colWidths=[1.8 * inch, 4.8 * inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        self.story.append(header_table)
        self.story.append(Spacer(1, 0.12 * inch))
        self.story.append(Paragraph(self.titulo, self.styles['CustomTitle']))
        self.story.append(Spacer(1, 0.2 * inch))

    def _add_kv_table(self, titulo, linhas):
        self.story.append(Paragraph(titulo, self.styles['SectionTitle']))

        dados = []
        for chave, valor in linhas:
            dados.append([
                Paragraph(f'<b>{chave}</b>', self.styles['Normal']),
                Paragraph(self._fmt(valor), self.styles['Normal'])
            ])

        tabela = Table(dados, colWidths=[2.2 * inch, 4.8 * inch])
        tabela.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c7c7c7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        self.story.append(tabela)

    def _add_list(self, titulo, itens, vazio_label='Nenhum registro'):
        self.story.append(Paragraph(titulo, self.styles['SectionTitle']))
        if not itens:
            self.story.append(Paragraph(vazio_label, self.styles['Normal']))
            return

        texto = '<br/>'.join(itens)
        self.story.append(Paragraph(texto, self.styles['Normal']))

    def _format_endereco_sem_cep(self, endereco):
        numero = endereco.numero or 'S/N'
        complemento = f", {endereco.complemento}" if endereco.complemento else ""
        uf_part = f"/{endereco.uf}" if endereco.uf and endereco.uf != 'EX' else ""
        pais_part = f", {endereco.pais}" if endereco.pais and endereco.pais.lower() != 'brasil' else ""
        cep_part = f" - CEP: {endereco.cep}" if endereco.uf != 'EX' and endereco.cep else ""
        return (
            f"{endereco.logradouro}, {numero}{complemento} - "
            f"{endereco.bairro}, {endereco.cidade}{uf_part}{pais_part}{cep_part}"
        )

    def adicionar_conteudo(self):
        cliente = self.cliente
        tipo_pessoa = getattr(cliente, 'get_tipo_pessoa_display', None)
        regime = getattr(cliente, 'get_regime_tributario_display', None)
        tipo_cliente = getattr(cliente, 'get_tipo_cliente_display', None)

        self._add_kv_table('Informacoes Gerais', [
            ('Tipo de Pessoa', tipo_pessoa() if callable(tipo_pessoa) else self._fmt(cliente.tipo_pessoa, '—')),
            ('CNPJ/CPF', getattr(cliente, 'get_cnpj_cpf_formatado', None)() if hasattr(cliente, 'get_cnpj_cpf_formatado') else self._fmt(cliente.cnpj_cpf)),
            ('Inscricao Estadual', self._fmt(cliente.inscricao_estadual)),
            ('Inscricao Municipal', self._fmt(cliente.inscricao_municipal)),
            ('Codigo EORI', self._fmt(cliente.eori)),
            ('Regime Tributario', regime() if callable(regime) else self._fmt(cliente.regime_tributario)),
            ('Contribuinte ICMS', 'Sim' if cliente.contribuinte_icms else 'Nao'),
            ('Indicador IE', self._fmt(cliente.indicador_ie)),
            ('Inscricao SUFRAMA', self._fmt(cliente.inscricao_suframa)),
            ('VAT / Registro Exterior', self._fmt(cliente.vat)),
            ('Mercado', tipo_cliente() if callable(tipo_cliente) else self._fmt(cliente.tipo_cliente)),
            ('Status', self._fmt(getattr(cliente, 'get_status_display', None)() if hasattr(cliente, 'get_status_display') else cliente.status)),
        ])

        self._add_kv_table('Comerciais', [
            ('Limite de Credito', self._fmt(cliente.limite_credito)),
            ('Prazo de Pagamento', f"{cliente.prazo_pagamento} dias" if cliente.prazo_pagamento else '—'),
            ('Vendedor Responsavel', self._fmt(cliente.vendedor_responsavel)),
            ('Porto Destino', self._fmt(cliente.porto_destino)),
            ('Pais', self._fmt(cliente.pais)),
        ])

        if cliente.observacoes_comerciais:
            self._add_list('Observacoes', [self._fmt(cliente.observacoes_comerciais)], vazio_label='—')

        enderecos_por_tipo = {}
        for endereco in cliente.enderecos.all():
            enderecos_por_tipo.setdefault(endereco.tipo, []).append(endereco)

        enderecos_linhas = []
        ordem_tipos = ['PRINCIPAL', 'FATURAMENTO', 'COBRANCA', 'ENTREGA', 'NOTIFY']
        for tipo in ordem_tipos:
            itens = enderecos_por_tipo.get(tipo, [])
            if not itens:
                continue

            label = itens[0].get_tipo_display()
            valores = []
            for item in itens:
                desc = self._format_endereco_sem_cep(item)
                if item.recebedor_notify:
                    valores.append(self._fmt(item.recebedor_notify))
                valores.append(desc)
            enderecos_linhas.append((label, '<br/>'.join(valores)))

        if enderecos_linhas:
            self._add_kv_table('Enderecos', enderecos_linhas)
        else:
            self._add_list('Enderecos', [], vazio_label='Nenhum endereco cadastrado')

        contatos_itens = []
        for contato in cliente.contatos.all():
            partes = [contato.nome]
            if contato.cargo:
                partes.append(contato.cargo)
            if contato.telefone:
                partes.append(contato.telefone)
            if contato.email:
                partes.append(contato.email)
            contatos_itens.append(' | '.join(partes))
        self._add_list('Contatos', contatos_itens, vazio_label='Nenhum contato cadastrado')

    def gerar(self):
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer.getvalue()


class RelatorioClientesExcel:
    def __init__(self, empresa, titulo='Relatorio de Clientes'):
        self.empresa = empresa
        self.titulo = titulo
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.title = 'Clientes'
        self._setup_styles()

    def _setup_styles(self):
        self.header_fill = PatternFill(start_color='1f4788', end_color='1f4788', fill_type='solid')
        self.header_font = Font(bold=True, color='FFFFFF', size=11)
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

    def adicionar_cabecalho(self, filtros_desc=''):
        self.ws['A1'] = self.titulo
        self.ws['A1'].font = Font(bold=True, size=14, color='1f4788')

        self.ws['A2'] = f'Empresa: {self.empresa.nome}'
        self.ws['A3'] = f'Gerado em: {datetime.now().strftime("%d/%m/%Y as %H:%M")}'

        if filtros_desc:
            self.ws['A4'] = f'Filtros: {filtros_desc}'

        return 5

    def adicionar_tabela(self, clientes, linha_inicio=5):
        colunas = ['Razao Social', 'CNPJ/CPF', 'Mercado', 'Status']

        for col, titulo in enumerate(colunas, 1):
            cell = self.ws.cell(row=linha_inicio, column=col)
            cell.value = titulo
            cell.fill = self.header_fill
            cell.font = self.header_font
            cell.border = self.border
            cell.alignment = Alignment(horizontal='center', vertical='center')

        linha = linha_inicio + 1
        for cliente in clientes:
            self.ws.cell(row=linha, column=1).value = cliente.razao_social
            self.ws.cell(row=linha, column=2).value = cliente.cnpj_cpf
            self.ws.cell(row=linha, column=3).value = cliente.get_tipo_cliente_display()
            self.ws.cell(row=linha, column=4).value = cliente.get_status_display()

            for col in range(1, 5):
                cell = self.ws.cell(row=linha, column=col)
                cell.border = self.border
                cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

            linha += 1

        self.ws.column_dimensions['A'].width = 40
        self.ws.column_dimensions['B'].width = 18
        self.ws.column_dimensions['C'].width = 15
        self.ws.column_dimensions['D'].width = 12

        return linha

    def gerar(self):
        buffer = io.BytesIO()
        self.wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()
