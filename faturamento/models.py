from django.conf import settings
from django.db import models
from django.utils import timezone


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
    regime_tributario = models.CharField('Regime Tributário', max_length=20, choices=REGIME, default='SIMPLES_NACIONAL')
    serie_nfe = models.IntegerField('Série NF-e', default=1)
    cfop_venda_interna = models.CharField('CFOP Venda Interna', max_length=10, default='5102')
    cfop_venda_exportacao = models.CharField('CFOP Venda Exportação', max_length=10, default='7101')
    natureza_operacao_padrao = models.CharField('Natureza da Operação Padrão', max_length=100, default='VENDA DE MERCADORIA')
    observacoes_padrao_nfe = models.TextField('Obs. Padrão NF-e', blank=True)
    observacoes_padrao_invoice = models.TextField('Obs. Padrão Invoice', blank=True)

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

    numero = models.PositiveIntegerField('Número NF', null=True, blank=True)
    serie = models.IntegerField('Série', default=1)
    natureza_operacao = models.CharField('Natureza da Operação', max_length=100, default='VENDA DE MERCADORIA')
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
    valor_ipi = models.DecimalField('Valor IPI', max_digits=14, decimal_places=2, default=0)
    valor_pis = models.DecimalField('Valor PIS', max_digits=14, decimal_places=2, default=0)
    valor_cofins = models.DecimalField('Valor COFINS', max_digits=14, decimal_places=2, default=0)
    valor_total = models.DecimalField('Valor Total', max_digits=14, decimal_places=2, default=0)
    informacoes_complementares = models.TextField('Informações Complementares', blank=True)
    chave_acesso = models.CharField('Chave de Acesso', max_length=44, blank=True)

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
        self.valor_ipi = sum(i.valor_ipi for i in items)
        self.valor_pis = sum(i.valor_pis for i in items)
        self.valor_cofins = sum(i.valor_cofins for i in items)
        self.valor_total = (
            self.valor_produtos
            + self.valor_frete
            + self.valor_seguro
            + self.valor_ipi
            - self.valor_desconto
        )
        self.save(update_fields=[
            'valor_produtos', 'valor_icms', 'valor_ipi',
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
    aliquota_icms = models.DecimalField('Alíq. ICMS (%)', max_digits=5, decimal_places=2, default=0)
    valor_icms = models.DecimalField('Valor ICMS', max_digits=14, decimal_places=2, default=0)
    aliquota_ipi = models.DecimalField('Alíq. IPI (%)', max_digits=5, decimal_places=2, default=0)
    valor_ipi = models.DecimalField('Valor IPI', max_digits=14, decimal_places=2, default=0)
    aliquota_pis = models.DecimalField('Alíq. PIS (%)', max_digits=5, decimal_places=2, default=0)
    valor_pis = models.DecimalField('Valor PIS', max_digits=14, decimal_places=2, default=0)
    aliquota_cofins = models.DecimalField('Alíq. COFINS (%)', max_digits=5, decimal_places=2, default=0)
    valor_cofins = models.DecimalField('Valor COFINS', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Item da Nota Fiscal'
        verbose_name_plural = 'Itens da Nota Fiscal'
        ordering = ['numero_item']
        unique_together = [('nota_fiscal', 'numero_item')]

    def __str__(self):
        return f'{self.numero_item} - {self.descricao}'

    def save(self, *args, **kwargs):
        self.valor_total = (self.quantidade * self.valor_unitario) - self.valor_desconto
        self.valor_icms = self.valor_total * self.aliquota_icms / 100
        self.valor_ipi = self.valor_total * self.aliquota_ipi / 100
        self.valor_pis = self.valor_total * self.aliquota_pis / 100
        self.valor_cofins = self.valor_total * self.aliquota_cofins / 100
        super().save(*args, **kwargs)


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
        self.valor_total = self.valor_mercadoria + self.valor_frete + self.valor_seguro
        self.save(update_fields=['valor_mercadoria', 'valor_total'])

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
