from django.conf import settings
from django.db import models
from django.utils import timezone

from faturamento.encryption import decrypt_field, encrypt_field


class FaturamentoBaseModel(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Empresa',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='%(class)s_criados',
        verbose_name='Criado por',
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='%(class)s_atualizados',
        verbose_name='Atualizado por',
    )

    class Meta:
        abstract = True


class ConfiguracaoFiscal(models.Model):
    REGIME = [
        ('SIMPLES_NACIONAL', 'Simples Nacional'),
        ('LUCRO_PRESUMIDO', 'Lucro Presumido'),
        ('LUCRO_REAL', 'Lucro Real'),
    ]

    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='configuracao_fiscal',
        verbose_name='Empresa',
    )
    AMBIENTE_NFE = [
        ('1', 'Produção'),
        ('2', 'Homologação'),
    ]

    regime_tributario = models.CharField('Regime Tributário', max_length=20, choices=REGIME, default='SIMPLES_NACIONAL')
    serie_nfe = models.IntegerField('Série NF-e', default=1)
    cfop_venda_interna = models.CharField('CFOP Venda Interna', max_length=10, default='5102')
    cfop_venda_exportacao = models.CharField('CFOP Venda Exportação', max_length=10, default='7101')
    natureza_operacao_padrao = models.CharField('Natureza da Operação Padrão', max_length=100, default='VENDA DE MERCADORIA')
    observacoes_padrao_nfe = models.TextField('Obs. Padrão NF-e', blank=True)
    observacoes_padrao_invoice = models.TextField('Obs. Padrão Invoice', blank=True)
    token_integranotas = models.CharField('Token IntegraNota', max_length=500, blank=True, help_text='Bearer token da API IntegraNota')
    ambiente_nfe = models.CharField('Ambiente NF-e', max_length=1, choices=AMBIENTE_NFE, default='2', help_text='2=Homologação (testes), 1=Produção')
    numero_nfe_inicial = models.PositiveIntegerField(
        'Número Inicial da NF-e',
        default=1,
        help_text='Usado somente quando não há notas emitidas neste sistema. '
                  'Para migrar de outro sistema, informe o próximo número (ex: última nota foi 3365 → informe 3366).',
    )

    # Certificado Digital A1
    certificado_pfx = models.BinaryField('Certificado Digital (.pfx)', blank=True, null=True)
    senha_certificado = models.CharField('Senha do Certificado', max_length=100, blank=True)
    certificado_validade = models.DateField('Validade do Certificado', null=True, blank=True)
    certificado_cnpj = models.CharField('CNPJ Titular', max_length=18, blank=True)
    certificado_arquivo_nome = models.CharField('Nome do Arquivo (.pfx)', max_length=255, blank=True)

    # ── Token encryption helpers ─────────────────────────────────────────────
    def set_token(self, raw_token: str) -> None:
        """Criptografa e armazena o token. Chamar .save() separadamente."""
        self.token_integranotas = encrypt_field(raw_token)

    def get_token(self) -> str:
        """Retorna o token decriptografado, ou '' se não configurado."""
        return decrypt_field(self.token_integranotas)

    @property
    def has_token(self) -> bool:
        return bool(self.token_integranotas)

    class Meta:
        verbose_name = 'Configuração Fiscal'
        verbose_name_plural = 'Configurações Fiscais'

    def __str__(self):
        return f'Config Fiscal - {self.empresa}'


class NotaFiscal(FaturamentoBaseModel):
    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('EMITIDA', 'Emitida'),
        ('CANCELADA', 'Cancelada'),
    ]

    MODALIDADE_FRETE = [
        ('SEM_FRETE', 'Sem Frete'),
        ('CIF', 'CIF - Por conta do Emitente'),
        ('FOB', 'FOB - Por conta do Destinatário'),
        ('EMITENTE', 'Por conta do Emitente'),
        ('DESTINATARIO', 'Por conta do Destinatário'),
    ]

    FINALIDADE_NFE = [
        ('1', '1 - NF-e Normal'),
        ('2', '2 - NF-e Complementar'),
        ('3', '3 - NF-e de Ajuste'),
        ('4', '4 - Devolução de Mercadoria'),
    ]

    PRESENCA_COMPRADOR = [
        ('0', '0 - Não se aplica'),
        ('1', '1 - Operação presencial'),
        ('2', '2 - Operação não presencial, Internet'),
        ('3', '3 - Operação não presencial, Teleatendimento'),
        ('4', '4 - NFC-e em operação com entrega em domicílio'),
        ('9', '9 - Operação não presencial, Outros'),
    ]

    numero = models.PositiveIntegerField('Número NF', null=True, blank=True)
    serie = models.IntegerField('Série', default=1)
    natureza_operacao = models.CharField('Natureza da Operação', max_length=100, default='VENDA DE MERCADORIA')
    finalidade_nfe = models.CharField('Finalidade NF-e', max_length=1, choices=FINALIDADE_NFE, default='1')
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        related_name='notas_fiscais',
        verbose_name='Cliente',
    )
    data_emissao = models.DateField('Data de Emissão', default=timezone.now)
    data_saida = models.DateField('Data de Saída', blank=True, null=True)
    cfop = models.CharField('CFOP', max_length=10, default='5102')
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    modalidade_frete = models.CharField('Modalidade de Frete', max_length=20, choices=MODALIDADE_FRETE, default='SEM_FRETE')
    transportadora = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='notas_fiscais_transporte',
        verbose_name='Transportadora',
    )
    valor_produtos = models.DecimalField('Valor dos Produtos', max_digits=14, decimal_places=2, default=0)
    valor_frete = models.DecimalField('Valor do Frete', max_digits=14, decimal_places=2, default=0)
    valor_seguro = models.DecimalField('Valor do Seguro', max_digits=14, decimal_places=2, default=0)
    valor_desconto = models.DecimalField('Valor de Desconto', max_digits=14, decimal_places=2, default=0)
    valor_icms = models.DecimalField('Valor ICMS', max_digits=14, decimal_places=2, default=0)
    valor_icms_st = models.DecimalField('Valor ICMS ST', max_digits=14, decimal_places=2, default=0)
    valor_ipi = models.DecimalField('Valor IPI', max_digits=14, decimal_places=2, default=0)
    valor_pis = models.DecimalField('Valor PIS', max_digits=14, decimal_places=2, default=0)
    valor_cofins = models.DecimalField('Valor COFINS', max_digits=14, decimal_places=2, default=0)
    valor_total = models.DecimalField('Valor Total', max_digits=14, decimal_places=2, default=0)
    informacoes_complementares = models.TextField('Informações Complementares', blank=True)
    informacoes_fisco = models.TextField('Informações para o Fisco (infAdFisco)', blank=True)
    chave_acesso = models.CharField('Chave de Acesso', max_length=44, blank=True)
    protocolo_autorizacao = models.CharField('Protocolo de Autorização', max_length=60, blank=True)
    xml_autorizacao = models.TextField('XML Autorizado (base64)', blank=True)
    pdf_danfe = models.TextField('DANFE PDF (base64)', blank=True)
    presenca_comprador = models.CharField('Presença do Comprador', max_length=1, choices=PRESENCA_COMPRADOR, default='9')
    tipo_emissao = models.IntegerField('Tipo de Emissão', default=1, help_text='1=Normal')
    data_hora_emissao = models.DateTimeField('Data/Hora de Emissão SEFAZ', null=True, blank=True)
    motivo_cancelamento = models.CharField('Motivo do Cancelamento', max_length=255, blank=True)
    data_cancelamento = models.DateTimeField('Data/Hora do Cancelamento', null=True, blank=True)

    class Meta:
        verbose_name = 'Nota Fiscal'
        verbose_name_plural = 'Notas Fiscais'
        ordering = ['-data_emissao', '-numero']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'NF {self.numero or "S/N"}/{self.serie} - {self.cliente}'

    def calcular_totais(self):
        items = self.itens.all()
        self.valor_produtos = sum(i.valor_total for i in items)
        self.valor_icms = sum(i.valor_icms for i in items)
        self.valor_icms_st = sum(i.valor_icms_st for i in items)
        self.valor_ipi = sum(i.valor_ipi for i in items)
        self.valor_pis = sum(i.valor_pis for i in items)
        self.valor_cofins = sum(i.valor_cofins for i in items)
        self.valor_total = (
            self.valor_produtos
            + self.valor_frete
            + self.valor_seguro
            + self.valor_ipi
            + self.valor_icms_st
            - self.valor_desconto
        )
        self.save(update_fields=[
            'valor_produtos', 'valor_icms', 'valor_icms_st', 'valor_ipi',
            'valor_pis', 'valor_cofins', 'valor_total',
        ])


class ItemNotaFiscal(models.Model):
    nota_fiscal = models.ForeignKey(
        NotaFiscal,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Nota Fiscal',
    )
    numero_item = models.PositiveIntegerField('Nº Item', default=1)
    descricao = models.CharField('Descrição', max_length=250)
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='itens_nota_fiscal',
        verbose_name='Produto',
    )
    ncm = models.CharField('NCM', max_length=8, blank=True)
    cfop = models.CharField('CFOP', max_length=10, blank=True)
    cst_icms = models.CharField('CST ICMS', max_length=3, blank=True)
    cst_pis = models.CharField('CST PIS', max_length=2, blank=True, default='07')
    cst_cofins = models.CharField('CST COFINS', max_length=2, blank=True, default='07')
    unidade = models.CharField('Unidade', max_length=10, default='UN')
    quantidade = models.DecimalField('Quantidade', max_digits=14, decimal_places=4, default=1)
    valor_unitario = models.DecimalField('Valor Unitário', max_digits=14, decimal_places=4, default=0)
    valor_total = models.DecimalField('Valor Total', max_digits=14, decimal_places=2, default=0)
    valor_desconto = models.DecimalField('Desconto', max_digits=14, decimal_places=2, default=0)
    # ICMS
    aliquota_icms = models.DecimalField('Alíq. ICMS (%)', max_digits=5, decimal_places=2, default=0)
    valor_icms = models.DecimalField('Valor ICMS', max_digits=14, decimal_places=2, default=0)
    icms_base_calculo = models.DecimalField('Base de Cálculo ICMS', max_digits=14, decimal_places=2, default=0)
    icms_modalidade_base = models.CharField('Modalidade BC ICMS', max_length=1, default='3',
        help_text='0=MVA, 1=Pauta, 2=Preço Tabelado, 3=Valor da Operação, 4=Margem Valor Agregado')
    icms_reducao_base = models.DecimalField('Redução BC ICMS (%)', max_digits=5, decimal_places=2, default=0)
    # ICMS ST
    icms_st_aliquota = models.DecimalField('Alíq. ICMS ST (%)', max_digits=5, decimal_places=2, default=0)
    icms_st_mva = models.DecimalField('MVA ST (%)', max_digits=5, decimal_places=2, default=0)
    icms_st_reducao_base = models.DecimalField('Redução BC ST (%)', max_digits=5, decimal_places=2, default=0)
    icms_st_base_calculo = models.DecimalField('BC ICMS ST', max_digits=14, decimal_places=2, default=0)
    valor_icms_st = models.DecimalField('Valor ICMS ST', max_digits=14, decimal_places=2, default=0)
    # IPI
    cst_ipi = models.CharField('CST IPI', max_length=2, blank=True, default='99')
    aliquota_ipi = models.DecimalField('Alíq. IPI (%)', max_digits=5, decimal_places=2, default=0)
    valor_ipi = models.DecimalField('Valor IPI', max_digits=14, decimal_places=2, default=0)
    ipi_codigo_enquadramento = models.CharField('Código Enquadramento IPI', max_length=3, default='999', blank=True)
    # PIS
    aliquota_pis = models.DecimalField('Alíq. PIS (%)', max_digits=5, decimal_places=2, default=0)
    valor_pis = models.DecimalField('Valor PIS', max_digits=14, decimal_places=2, default=0)
    pis_base_calculo = models.DecimalField('Base de Cálculo PIS', max_digits=14, decimal_places=2, default=0)
    # COFINS
    aliquota_cofins = models.DecimalField('Alíq. COFINS (%)', max_digits=5, decimal_places=2, default=0)
    valor_cofins = models.DecimalField('Valor COFINS', max_digits=14, decimal_places=2, default=0)
    cofins_base_calculo = models.DecimalField('Base de Cálculo COFINS', max_digits=14, decimal_places=2, default=0)
    origem_mercadoria = models.CharField('Origem da Mercadoria', max_length=1, default='0', help_text='0=Nacional, 1-8=Estrangeira')
    cest = models.CharField('CEST', max_length=7, blank=True, help_text='Código Especificador da Substituição Tributária')
    ean = models.CharField('EAN/Código de Barras', max_length=14, blank=True, help_text='Deixe em branco para usar SEM GTIN')

    class Meta:
        verbose_name = 'Item da Nota Fiscal'
        verbose_name_plural = 'Itens da Nota Fiscal'
        ordering = ['numero_item']
        unique_together = [('nota_fiscal', 'numero_item')]

    def __str__(self):
        return f'{self.numero_item} - {self.descricao}'

    def save(self, *args, **kwargs):
        self.valor_total = (self.quantidade * self.valor_unitario) - self.valor_desconto
        # ICMS com redução de BC
        reducao = self.icms_reducao_base or 0
        self.icms_base_calculo = self.valor_total * (1 - reducao / 100)
        self.valor_icms = self.icms_base_calculo * (self.aliquota_icms or 0) / 100
        # ICMS ST
        if self.icms_st_aliquota and self.icms_st_aliquota > 0:
            mva = self.icms_st_mva or 0
            red_st = self.icms_st_reducao_base or 0
            bc_st = self.valor_total * (1 + mva / 100) * (1 - red_st / 100)
            self.icms_st_base_calculo = bc_st
            self.valor_icms_st = max(bc_st * self.icms_st_aliquota / 100 - self.valor_icms, 0)
        else:
            self.icms_st_base_calculo = 0
            self.valor_icms_st = 0
        # IPI
        self.valor_ipi = self.valor_total * (self.aliquota_ipi or 0) / 100
        # PIS
        self.pis_base_calculo = self.valor_total
        self.valor_pis = self.pis_base_calculo * (self.aliquota_pis or 0) / 100
        # COFINS
        self.cofins_base_calculo = self.valor_total
        self.valor_cofins = self.cofins_base_calculo * (self.aliquota_cofins or 0) / 100
        super().save(*args, **kwargs)


MEIO_PAGAMENTO_CHOICES = [
    ('01', 'Dinheiro'),
    ('02', 'Cheque'),
    ('03', 'Cartão de Crédito'),
    ('04', 'Cartão de Débito'),
    ('05', 'Crédito Loja'),
    ('14', 'Duplicata Mercantil'),
    ('15', 'Boleto Bancário'),
    ('16', 'Depósito Bancário'),
    ('17', 'PIX'),
    ('18', 'Transferência Bancária / TED'),
    ('90', 'Sem Pagamento'),
    ('99', 'Outros'),
]


class PagamentoNF(models.Model):
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.CASCADE, related_name='pagamentos')
    meio_pagamento = models.CharField('Meio de Pagamento', max_length=2, choices=MEIO_PAGAMENTO_CHOICES, default='17')
    valor = models.DecimalField('Valor', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Pagamento NF'
        verbose_name_plural = 'Pagamentos NF'

    def __str__(self):
        return f'{self.get_meio_pagamento_display()} — R$ {self.valor}'


class DuplicataNF(models.Model):
    nota_fiscal = models.ForeignKey(NotaFiscal, on_delete=models.CASCADE, related_name='duplicatas')
    numero = models.CharField('Número', max_length=60, blank=True)
    vencimento = models.DateField('Vencimento')
    valor = models.DecimalField('Valor', max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = 'Duplicata NF'
        verbose_name_plural = 'Duplicatas NF'
        ordering = ['vencimento']

    def __str__(self):
        return f'Dup {self.numero} — {self.vencimento} — R$ {self.valor}'


class InvoiceExportacao(FaturamentoBaseModel):
    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('EMITIDA', 'Emitida'),
        ('CANCELADA', 'Cancelada'),
    ]

    INCOTERM = [
        ('FOB', 'FOB - Free On Board'),
        ('CIF', 'CIF - Cost, Insurance and Freight'),
        ('EXW', 'EXW - Ex Works'),
        ('DDP', 'DDP - Delivered Duty Paid'),
        ('CFR', 'CFR - Cost and Freight'),
    ]

    MOEDA = [
        ('USD', 'USD - Dólar Americano'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - Libra Esterlina'),
        ('BRL', 'BRL - Real Brasileiro'),
    ]

    numero = models.CharField('Número Invoice', max_length=30, blank=True)
    booking = models.ForeignKey(
        'exportacao.Booking',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='invoices',
        verbose_name='Booking',
    )
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        related_name='invoices_exportacao',
        verbose_name='Importador / Cliente',
    )
    data_emissao = models.DateField('Data de Emissão', default=timezone.now)
    data_embarque_previsto = models.DateField('Data de Embarque Previsto', blank=True, null=True)
    incoterm = models.CharField('Incoterm', max_length=5, choices=INCOTERM, default='FOB')
    moeda = models.CharField('Moeda', max_length=5, choices=MOEDA, default='USD')
    taxa_cambio = models.DecimalField('Taxa de Câmbio (para BRL)', max_digits=10, decimal_places=4, blank=True, null=True)
    porto_embarque = models.CharField('Porto de Embarque', max_length=100, blank=True)
    porto_destino = models.CharField('Porto de Destino', max_length=100, blank=True)
    condicao_pagamento = models.CharField('Condição de Pagamento', max_length=100, blank=True, default='30 days from BL date')
    banco_beneficiario = models.TextField('Dados Bancários do Beneficiário', blank=True)
    observacoes = models.TextField('Observações', blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    valor_mercadoria = models.DecimalField('Valor da Mercadoria', max_digits=14, decimal_places=2, default=0)
    valor_frete = models.DecimalField('Valor do Frete', max_digits=14, decimal_places=2, default=0)
    valor_seguro = models.DecimalField('Valor do Seguro', max_digits=14, decimal_places=2, default=0)
    valor_desconto_adiantamento = models.DecimalField(
        'Desconto Adiantamento Internacional',
        max_digits=14,
        decimal_places=2,
        default=0,
    )
    valor_total = models.DecimalField('Valor Total', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Invoice de Exportação'
        verbose_name_plural = 'Invoices de Exportação'
        ordering = ['-data_emissao', '-numero']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'{self.numero or "Invoice"} - {self.cliente}'

    def calcular_totais(self):
        self.valor_mercadoria = sum(i.valor_total_fob for i in self.itens.all())
        self.valor_total = (
            self.valor_mercadoria + self.valor_frete + self.valor_seguro
            - (self.valor_desconto_adiantamento or 0)
        )
        self.save(update_fields=['valor_mercadoria', 'valor_desconto_adiantamento', 'valor_total'])

    @property
    def peso_bruto_total(self):
        return sum(i.peso_bruto_kg for i in self.itens.all())

    @property
    def peso_liquido_total(self):
        return sum(i.peso_liquido_kg for i in self.itens.all())


class ItemInvoice(models.Model):
    invoice = models.ForeignKey(
        InvoiceExportacao,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Invoice',
    )
    container = models.ForeignKey(
        'exportacao.BookingContainer',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='itens_invoice',
        verbose_name='Container',
    )
    descricao = models.CharField('Descrição do Produto', max_length=250)
    quantidade = models.DecimalField('Quantidade', max_digits=14, decimal_places=4, default=1)
    unidade = models.CharField('Unidade', max_length=20, default='CTN')
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=14, decimal_places=3, default=0)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=14, decimal_places=3, default=0)
    valor_unitario_fob = models.DecimalField('Valor Unitário FOB', max_digits=14, decimal_places=4, default=0)
    valor_total_fob = models.DecimalField('Valor Total FOB', max_digits=14, decimal_places=2, default=0)
    marks_numbers = models.CharField('Marks & Numbers', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Item da Invoice'
        verbose_name_plural = 'Itens da Invoice'
        ordering = ['pk']

    def __str__(self):
        return f'{self.descricao} - {self.quantidade} {self.unidade}'

    def save(self, *args, **kwargs):
        self.valor_total_fob = self.quantidade * self.valor_unitario_fob
        super().save(*args, **kwargs)


class PackingList(FaturamentoBaseModel):
    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('EMITIDO', 'Emitido'),
        ('CANCELADO', 'Cancelado'),
    ]

    invoice = models.ForeignKey(
        InvoiceExportacao,
        on_delete=models.PROTECT,
        related_name='packing_lists',
        verbose_name='Invoice',
    )
    numero = models.CharField('Número Packing List', max_length=30, blank=True)
    data_emissao = models.DateField('Data de Emissão', default=timezone.now)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Packing List'
        verbose_name_plural = 'Packing Lists'
        ordering = ['-data_emissao']

    def __str__(self):
        return f'{self.numero or "PL"} - {self.invoice}'

    @property
    def peso_bruto_total(self):
        return sum(i.peso_bruto_kg for i in self.itens.all())

    @property
    def peso_liquido_total(self):
        return sum(i.peso_liquido_kg for i in self.itens.all())

    @property
    def total_caixas(self):
        return sum(i.quantidade_caixas for i in self.itens.all())


# ═══════════════════════════════════════════════════════════════════
#  CT-e — Conhecimento de Transporte Eletrônico
# ═══════════════════════════════════════════════════════════════════

class ConhecimentoTransporte(FaturamentoBaseModel):
    STATUS = [
        ('RASCUNHO',  'Rascunho'),
        ('EMITIDO',   'Emitido'),
        ('CANCELADO', 'Cancelado'),
    ]
    MODALIDADE_FRETE = [
        ('CIF', 'CIF — Por conta do Remetente'),
        ('FOB', 'FOB — Por conta do Destinatário/Tomador'),
    ]
    TIPO_SERVICO = [
        ('NORMAL',       'Normal'),
        ('SUBCONTRATADO','Subcontratação'),
        ('REDESPACHO',   'Redespacho'),
        ('INTERMEDIARIO','Intermediário'),
    ]

    numero          = models.PositiveIntegerField('Número CT-e', null=True, blank=True)
    serie           = models.CharField('Série', max_length=3, default='1')
    data_emissao    = models.DateField('Data de Emissão', default=timezone.now)
    cfop            = models.CharField('CFOP', max_length=4, default='6351', help_text='6351=Prestação de serviço de transporte')
    natureza_operacao = models.CharField('Natureza da Operação', max_length=60, default='PRESTAÇÃO DE SERVIÇO DE TRANSPORTE')
    tipo_servico    = models.CharField('Tipo de Serviço', max_length=20, choices=TIPO_SERVICO, default='NORMAL')

    # Partes envolvidas
    remetente       = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='cte_remetente', verbose_name='Remetente',
        help_text='Quem envia a mercadoria',
    )
    destinatario    = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='cte_destinatario', verbose_name='Destinatário',
        help_text='Quem recebe a mercadoria',
    )
    tomador         = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='cte_tomador', verbose_name='Tomador do Serviço',
        help_text='Responsável pelo pagamento do frete',
    )
    transportadora  = models.ForeignKey(
        'cadastros.Transportadora', on_delete=models.PROTECT,
        related_name='conhecimentos_transporte', verbose_name='Transportadora',
    )
    motorista       = models.ForeignKey(
        'cadastros.Motorista', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conhecimentos_transporte', verbose_name='Motorista',
    )
    veiculo         = models.ForeignKey(
        'cadastros.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conhecimentos_transporte', verbose_name='Veículo',
    )

    # Percurso
    uf_inicio       = models.CharField('UF de Início', max_length=2)
    municipio_inicio = models.CharField('Município de Início', max_length=100)
    uf_fim          = models.CharField('UF de Fim', max_length=2)
    municipio_fim   = models.CharField('Município de Fim', max_length=100)

    # Valores
    valor_servico   = models.DecimalField('Valor do Serviço (Frete)', max_digits=14, decimal_places=2, default=0)
    valor_carga     = models.DecimalField('Valor da Carga', max_digits=14, decimal_places=2, default=0)
    peso_bruto_kg   = models.DecimalField('Peso Bruto (kg)', max_digits=12, decimal_places=3, default=0)
    modalidade_frete = models.CharField('Modalidade de Frete', max_length=3, choices=MODALIDADE_FRETE, default='CIF')

    # Informações adicionais
    observacoes     = models.TextField('Observações', blank=True)

    # SEFAZ
    chave_acesso    = models.CharField('Chave de Acesso', max_length=44, blank=True)
    protocolo       = models.CharField('Protocolo de Autorização', max_length=60, blank=True)
    xml_autorizacao = models.TextField('XML Autorizado (base64)', blank=True)
    pdf_dacte       = models.TextField('DACTE PDF (base64)', blank=True)
    status          = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    motivo_cancelamento = models.CharField('Motivo do Cancelamento', max_length=255, blank=True)
    data_cancelamento   = models.DateTimeField('Data do Cancelamento', null=True, blank=True)
    data_hora_emissao   = models.DateTimeField('Data/Hora SEFAZ', null=True, blank=True)

    class Meta:
        verbose_name = 'Conhecimento de Transporte (CT-e)'
        verbose_name_plural = 'Conhecimentos de Transporte (CT-e)'
        ordering = ['-data_emissao', '-numero']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'CT-e {self.numero or "S/N"}/{self.serie} — {self.remetente} → {self.destinatario}'


class DocumentoVinculadoCTe(models.Model):
    """NF-e ou outros documentos transportados no CT-e."""
    cte             = models.ForeignKey(ConhecimentoTransporte, on_delete=models.CASCADE, related_name='documentos_vinculados')
    chave_nfe       = models.CharField('Chave NF-e (44 dígitos)', max_length=44)
    descricao       = models.CharField('Descrição / Produto', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Documento Vinculado ao CT-e'

    def __str__(self):
        return self.chave_nfe


# ═══════════════════════════════════════════════════════════════════
#  MDF-e — Manifesto de Documentos Fiscais Eletrônico
# ═══════════════════════════════════════════════════════════════════

class ManifestoDocumentoFiscal(FaturamentoBaseModel):
    STATUS = [
        ('RASCUNHO',   'Rascunho'),
        ('EMITIDO',    'Emitido'),
        ('ENCERRADO',  'Encerrado'),
        ('CANCELADO',  'Cancelado'),
    ]
    TIPO_EMITENTE = [
        ('TAC',   'TAC — Transportador Autônomo de Carga'),
        ('ETC',   'ETC — Empresa de Transporte de Cargas'),
        ('CTC',   'CTC — Cooperativa de Transporte de Cargas'),
    ]
    TIPO_TRANSPORTE = [
        ('1', 'Carga Geral'),
        ('2', 'Frigorificada/Aquecida'),
        ('3', 'Granel Líquido'),
        ('4', 'Granel Sólido'),
        ('5', 'Carga Fracionada'),
    ]

    numero          = models.PositiveIntegerField('Número MDF-e', null=True, blank=True)
    serie           = models.CharField('Série', max_length=3, default='1')
    data_emissao    = models.DateField('Data de Emissão', default=timezone.now)

    # Modal
    motorista       = models.ForeignKey(
        'cadastros.Motorista', on_delete=models.PROTECT,
        related_name='manifestos', verbose_name='Motorista',
    )
    veiculo         = models.ForeignKey(
        'cadastros.Vehicle', on_delete=models.PROTECT,
        related_name='manifestos', verbose_name='Veículo (Tração)',
    )

    # Percurso
    uf_inicio       = models.CharField('UF de Início', max_length=2, help_text='Ex: SP')
    municipio_carregamento = models.CharField('Município de Carregamento', max_length=100)
    uf_fim          = models.CharField('UF de Destino Final', max_length=2, help_text='Ex: MG')

    # Carga
    tipo_transporte = models.CharField('Tipo de Transporte', max_length=1, choices=TIPO_TRANSPORTE, default='1')
    valor_carga     = models.DecimalField('Valor Total da Carga', max_digits=14, decimal_places=2, default=0)
    peso_bruto_kg   = models.DecimalField('Peso Bruto (kg)', max_digits=12, decimal_places=3, default=0)

    # Informações adicionais
    informacoes_fisco       = models.TextField('Informações para o Fisco', blank=True)
    informacoes_contribuinte = models.TextField('Informações do Contribuinte', blank=True)

    # SEFAZ
    chave_acesso    = models.CharField('Chave de Acesso', max_length=44, blank=True)
    protocolo       = models.CharField('Protocolo de Autorização', max_length=60, blank=True)
    xml_autorizacao = models.TextField('XML Autorizado (base64)', blank=True)
    pdf_damdfe      = models.TextField('DAMDFE PDF (base64)', blank=True)
    status          = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    motivo_cancelamento     = models.CharField('Motivo do Cancelamento', max_length=255, blank=True)
    data_cancelamento       = models.DateTimeField('Data do Cancelamento', null=True, blank=True)
    data_hora_emissao       = models.DateTimeField('Data/Hora SEFAZ', null=True, blank=True)
    data_encerramento       = models.DateTimeField('Data do Encerramento', null=True, blank=True)
    municipio_encerramento  = models.CharField('Município de Encerramento', max_length=100, blank=True)

    class Meta:
        verbose_name = 'Manifesto de Documentos Fiscais (MDF-e)'
        verbose_name_plural = 'Manifestos de Documentos Fiscais (MDF-e)'
        ordering = ['-data_emissao', '-numero']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'MDF-e {self.numero or "S/N"}/{self.serie} — {self.motorista} ({self.uf_inicio}→{self.uf_fim})'


class DocumentoVinculadoMDFe(models.Model):
    """NF-e ou CT-e vinculados ao MDF-e por município de descarregamento."""
    TIPO = [('nfe', 'NF-e'), ('cte', 'CT-e')]

    mdfe            = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='documentos_vinculados')
    tipo            = models.CharField('Tipo de Documento', max_length=3, choices=TIPO, default='nfe')
    chave           = models.CharField('Chave de Acesso (44 dígitos)', max_length=44)
    municipio_descarregamento = models.CharField('Município de Descarregamento', max_length=100)

    class Meta:
        verbose_name = 'Documento Vinculado ao MDF-e'

    def __str__(self):
        return f'{self.get_tipo_display()} {self.chave[:10]}… → {self.municipio_descarregamento}'


class PercursoMDFe(models.Model):
    """Estados percorridos no trajeto do MDF-e."""
    mdfe            = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='percursos')
    uf              = models.CharField('UF Percorrida', max_length=2)
    ordem           = models.PositiveSmallIntegerField('Ordem', default=1)

    class Meta:
        verbose_name = 'Percurso MDF-e'
        ordering = ['ordem']

    def __str__(self):
        return self.uf


class ItemPackingList(models.Model):
    packing_list = models.ForeignKey(
        PackingList,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Packing List',
    )
    container = models.ForeignKey(
        'exportacao.BookingContainer',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='itens_packing_list',
        verbose_name='Container',
    )
    numero_container = models.CharField('Número do Container', max_length=20, blank=True)
    tipo_container = models.CharField('Tipo', max_length=10, blank=True)
    lacre_armador = models.CharField('Lacre Armador', max_length=30, blank=True)
    lacre_fiscal = models.CharField('Lacre Fiscal', max_length=30, blank=True)
    descricao_produto = models.CharField('Descrição do Produto', max_length=250)
    quantidade_caixas = models.DecimalField('Qtd. Caixas', max_digits=14, decimal_places=2, default=0)
    quantidade_pallets = models.DecimalField('Qtd. Pallets', max_digits=14, decimal_places=2, blank=True, null=True)
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=14, decimal_places=3, default=0)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=14, decimal_places=3, default=0)
    volume_m3 = models.DecimalField('Volume (m³)', max_digits=10, decimal_places=3, blank=True, null=True)
    marks_numbers = models.CharField('Marks & Numbers', max_length=200, blank=True)
    ordem = models.PositiveIntegerField('Ordem', default=1)

    class Meta:
        verbose_name = 'Item do Packing List'
        verbose_name_plural = 'Itens do Packing List'
        ordering = ['ordem']

    def __str__(self):
        return f'{self.numero_container or self.descricao_produto}'
