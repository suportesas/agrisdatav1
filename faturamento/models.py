from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from faturamento.encryption import decrypt_field, encrypt_field
from frota.models import TIPO_CARROCERIA_CHOICES, TIPO_RODADO_CHOICES


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
        """True apenas se o token decriptografado for não-vazio."""
        return bool(self.get_token())

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
    quantidade_volumes = models.PositiveIntegerField(
        'Quantidade de Volumes', blank=True, null=True,
        help_text='Quantidade de volumes transportados (grupo de volumes da NF-e)',
    )
    especie_volumes = models.CharField(
        'Espécie', max_length=60, blank=True,
        help_text='Espécie dos volumes transportados (sacos, caixas, pallets etc.)',
    )
    marca_volumes = models.CharField('Marca', max_length=100, blank=True)
    numeracao_volumes = models.CharField('Numeração', max_length=100, blank=True)
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=14, decimal_places=3, blank=True, null=True)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=14, decimal_places=3, blank=True, null=True)
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
    xml_autorizacao_url = models.URLField('URL XML Autorizado (Storage)', blank=True)
    pdf_danfe = models.TextField('DANFE PDF (base64)', blank=True)
    pdf_danfe_url = models.URLField('URL DANFE PDF (Storage)', blank=True)
    presenca_comprador = models.CharField('Presença do Comprador', max_length=1, choices=PRESENCA_COMPRADOR, default='9')

    # ── Intermediador (indIntermed / infIntermed — obrigatório para indPres 2/3/4/9) ──
    IND_INTERMEDIADOR_CHOICES = [
        ('', 'Não se aplica (presencial)'),
        ('0', '0 – Operação sem intermediador (site/plataforma própria)'),
        ('1', '1 – Operação em site ou plataforma de terceiros (marketplace)'),
    ]
    ind_intermediador = models.CharField(
        'Indicador de Intermediador (indIntermed)',
        max_length=1,
        choices=IND_INTERMEDIADOR_CHOICES,
        blank=True,
        default='',
        help_text='Obrigatório quando indPres = 2, 3, 4 ou 9 (não presencial).',
    )
    intermediador_cnpj = models.CharField(
        'CNPJ do Intermediador', max_length=14, blank=True,
        help_text='CNPJ da plataforma intermediadora (somente dígitos). Obrigatório quando indIntermed = 1.',
    )
    intermediador_id_cadastro = models.CharField(
        'ID Cad. no Intermediador (idCadIntTran)', max_length=60, blank=True,
        help_text='Identificador do vendedor na plataforma intermediadora (ex: login, CPF, código). Obrigatório quando indIntermed = 1.',
    )

    tipo_emissao = models.IntegerField('Tipo de Emissão', default=1, help_text='1=Normal')
    data_hora_emissao = models.DateTimeField('Data/Hora de Emissão SEFAZ', null=True, blank=True)
    motivo_cancelamento = models.CharField('Motivo do Cancelamento', max_length=255, blank=True)
    data_cancelamento = models.DateTimeField('Data/Hora do Cancelamento', null=True, blank=True)

    # ── Manifestação do Destinatário (MD-e) ─────────────────────────────────────
    manifestacao_tipo = models.CharField('Tipo de Manifestação', max_length=40, blank=True)
    manifestacao_protocolo = models.CharField('Protocolo da Manifestação', max_length=50, blank=True)
    manifestacao_data = models.DateTimeField('Data/Hora da Manifestação', null=True, blank=True)

    # ── Exportação (grupo ZA da NF-e — <exporta>) ──────────────────────────────
    embarque_uf = models.CharField(
        'UF do Embarque', max_length=2, blank=True,
        help_text='UF de saída do país (ex: CE, SP). Obrigatório para NF-e de exportação (CFOP 7xxx).',
    )
    embarque_local = models.CharField(
        'Local do Embarque', max_length=60, blank=True,
        help_text='Descrição do local de embarque/exportação (ex: Porto Mucuripe).',
    )
    embarque_local_despacho = models.CharField(
        'Local do Despacho', max_length=60, blank=True,
        help_text='Local de despacho aduaneiro, quando diferente do embarque (ex: Recinto Alfandegado).',
    )

    # ── Endereço de Entrega (grupo G da NF-e — local diferente do destinatário) ──
    entrega_ativo = models.BooleanField(
        'Usar endereço de entrega diferente',
        default=False,
        help_text='Marque quando a mercadoria for entregue em endereço diferente do destinatário (ex: porto, obra, filial).',
    )
    entrega_cnpj_cpf = models.CharField('CNPJ/CPF do Local de Entrega', max_length=14, blank=True,
        help_text='Somente dígitos. CNPJ (14) ou CPF (11) do local de entrega.')
    entrega_logradouro = models.CharField('Logradouro', max_length=60, blank=True)
    entrega_numero = models.CharField('Número', max_length=10, blank=True)
    entrega_complemento = models.CharField('Complemento', max_length=60, blank=True)
    entrega_bairro = models.CharField('Bairro', max_length=60, blank=True)
    entrega_codigo_municipio = models.CharField('Código IBGE do Município', max_length=7, blank=True,
        help_text='7 dígitos — código IBGE do município de entrega.')
    entrega_nome_municipio = models.CharField('Município', max_length=60, blank=True)
    entrega_uf = models.CharField('UF', max_length=2, blank=True)

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
    natureza_receita_pis = models.CharField('Natureza da Receita PIS', max_length=3, blank=True,
        help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99.')
    # COFINS
    aliquota_cofins = models.DecimalField('Alíq. COFINS (%)', max_digits=5, decimal_places=2, default=0)
    valor_cofins = models.DecimalField('Valor COFINS', max_digits=14, decimal_places=2, default=0)
    cofins_base_calculo = models.DecimalField('Base de Cálculo COFINS', max_digits=14, decimal_places=2, default=0)
    natureza_receita_cofins = models.CharField('Natureza da Receita COFINS', max_length=3, blank=True,
        help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99.')
    origem_mercadoria = models.CharField('Origem da Mercadoria', max_length=1, default='0', help_text='0=Nacional, 1-8=Estrangeira')
    cest = models.CharField('CEST', max_length=7, blank=True, help_text='Código Especificador da Substituição Tributária')
    ean = models.CharField('EAN/Código de Barras', max_length=14, blank=True, help_text='Deixe em branco para usar SEM GTIN')

    # ── DI — Declaração de Importação (Grupo I da NF-e) ──────────────────────
    # Obrigatório quando origem_mercadoria for 1, 2, 6 ou 7 (produto estrangeiro)
    VIA_TRANSPORTE_CHOICES = [
        ('1',  '1 - Marítima'), ('2',  '2 - Fluvial'), ('3',  '3 - Lacustre'),
        ('4',  '4 - Aérea'),    ('5',  '5 - Postal'),   ('6',  '6 - Ferroviária'),
        ('7',  '7 - Rodoviária'),('8',  '8 - Conduto/Rede'),('9',  '9 - Meios Próprios'),
        ('10', '10 - Entrada/Saída Ficta'),('11', '11 - Courier'),
        ('12', '12 - Em mãos'), ('13', '13 - Por reboque'),
    ]
    TIPO_INTERMEDIARIO_CHOICES = [
        ('1', '1 - Importação por conta própria'),
        ('2', '2 - Importação por conta e ordem'),
        ('3', '3 - Importação por encomenda'),
    ]

    # ── Unidade Tributável (exportação — CFOP 7xxx) ──────────────────────────
    # Mapeia para qTrib / uTrib / vUnTrib no XML da NF-e.
    # Quando CFOP 7xxx: unidade comercial = CX, unidade tributável = KG.
    quantidade_tributavel     = models.DecimalField('Qtd. Tributável', max_digits=14, decimal_places=4, default=0)
    unidade_tributavel        = models.CharField('Unid. Tributável', max_length=20, blank=True, default='KG')
    valor_unitario_tributavel = models.DecimalField('Vl. Unit. Tributável', max_digits=14, decimal_places=4, default=0)

    di_numero           = models.CharField('Nº da DI', max_length=12, blank=True,
                              help_text='Número da Declaração de Importação (ex: 24/1234567-8)')
    di_data_registro    = models.DateField('Data Registro DI', null=True, blank=True)
    di_local_desembaraco = models.CharField('Local do Desembaraço', max_length=60, blank=True,
                               help_text='Nome do porto/aeroporto/local de desembaraço aduaneiro')
    di_uf_desembaraco   = models.CharField('UF Desembaraço', max_length=2, blank=True)
    di_data_desembaraco = models.DateField('Data Desembaraço', null=True, blank=True)
    di_via_transporte   = models.CharField('Via de Transporte', max_length=2, blank=True,
                              choices=VIA_TRANSPORTE_CHOICES)
    di_valor_afrmm      = models.DecimalField('Valor AFRMM (R$)', max_digits=14, decimal_places=2,
                              default=0, help_text='Adicional ao Frete — apenas via Marítima')
    di_tipo_intermediario = models.CharField('Tipo Intermediário', max_length=1, blank=True,
                               choices=TIPO_INTERMEDIARIO_CHOICES)
    di_cnpj_adquirente  = models.CharField('CNPJ Adquirente/Encomendante', max_length=14, blank=True,
                              help_text='Obrigatório quando tipo intermediário = 2 ou 3')
    di_codigo_exportador = models.CharField('Código do Exportador', max_length=60, blank=True)
    # Adição da DI (adi) — suporte a 1 adição inline (caso mais comum)
    di_numero_adicao    = models.CharField('Nº Adição', max_length=3, blank=True)
    di_codigo_fabricante = models.CharField('Código do Fabricante', max_length=60, blank=True)
    di_desconto_adicao  = models.DecimalField('Desconto da Adição (R$)', max_digits=14, decimal_places=2, default=0)
    di_numero_drawback  = models.CharField('Nº Ato Concessório Drawback', max_length=20, blank=True,
                              help_text='Suspensão ou Isenção — deixe em branco se não se aplica')

    class Meta:
        verbose_name = 'Item da Nota Fiscal'
        verbose_name_plural = 'Itens da Nota Fiscal'
        ordering = ['numero_item']
        unique_together = [('nota_fiscal', 'numero_item')]

    def __str__(self):
        return f'{self.numero_item} - {self.descricao}'

    def save(self, *args, **kwargs):
        _0   = Decimal('0')
        _100 = Decimal('100')

        def d(val):
            """Garante Decimal — evita Decimal * float."""
            if val is None:
                return _0
            if isinstance(val, Decimal):
                return val
            return Decimal(str(val))

        self.valor_total = (self.quantidade * self.valor_unitario) - self.valor_desconto

        # ICMS com redução de BC
        reducao = d(self.icms_reducao_base)
        self.icms_base_calculo = self.valor_total * (_100 - reducao) / _100
        self.valor_icms = self.icms_base_calculo * d(self.aliquota_icms) / _100

        # ICMS ST
        if self.icms_st_aliquota and self.icms_st_aliquota > _0:
            mva    = d(self.icms_st_mva)
            red_st = d(self.icms_st_reducao_base)
            bc_st  = self.valor_total * (_100 + mva) / _100 * (_100 - red_st) / _100
            self.icms_st_base_calculo = bc_st
            self.valor_icms_st = max(bc_st * d(self.icms_st_aliquota) / _100 - self.valor_icms, _0)
        else:
            self.icms_st_base_calculo = _0
            self.valor_icms_st = _0

        # IPI
        self.valor_ipi = self.valor_total * d(self.aliquota_ipi) / _100

        # PIS
        self.pis_base_calculo = self.valor_total
        self.valor_pis = self.pis_base_calculo * d(self.aliquota_pis) / _100

        # COFINS
        self.cofins_base_calculo = self.valor_total
        self.valor_cofins = self.cofins_base_calculo * d(self.aliquota_cofins) / _100

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


class CartaCorrecaoNFe(models.Model):
    nota_fiscal = models.ForeignKey(
        NotaFiscal,
        on_delete=models.CASCADE,
        related_name='cartas_correcao',
        verbose_name='Nota Fiscal',
    )
    sequencia = models.PositiveIntegerField('Sequência', default=1)
    correcao = models.TextField('Texto da Correção')
    protocolo = models.CharField('Protocolo SEFAZ', max_length=50, blank=True)
    xml_retorno = models.TextField('XML de Retorno (base64)', blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cartas_correcao_nfe',
    )

    class Meta:
        verbose_name = 'Carta de Correção NF-e'
        verbose_name_plural = 'Cartas de Correção NF-e'
        ordering = ['sequencia']
        unique_together = [('nota_fiscal', 'sequencia')]

    def __str__(self):
        return f'CC-e {self.sequencia} — NF {self.nota_fiscal}'


class InutilizacaoNFe(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='inutilizacoes_nfe',
        verbose_name='Empresa',
    )
    serie = models.IntegerField('Série', default=1)
    numero_ini = models.PositiveIntegerField('Número Inicial')
    numero_fim = models.PositiveIntegerField('Número Final')
    ano = models.IntegerField('Ano')
    justificativa = models.CharField('Justificativa', max_length=255)
    protocolo = models.CharField('Protocolo SEFAZ', max_length=50, blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inutilizacoes_nfe',
    )

    class Meta:
        verbose_name = 'Inutilização NF-e'
        verbose_name_plural = 'Inutilizações NF-e'
        ordering = ['-criado_em']

    def __str__(self):
        return f'Inut. {self.serie}/{self.numero_ini}-{self.numero_fim} ({self.ano})'


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
    globalizado     = models.BooleanField(
        'CT-e Globalizado', default=False,
        help_text='Cobre múltiplas NF-e de uma mesma coleta ou entrega dentro do mesmo Estado',
    )
    referencia_despacho = models.CharField(
        'Referência ao Despacho', max_length=20, blank=True,
        help_text='Número do manifesto/despacho que agrupa as NF-e (obrigatório no modo globalizado)',
    )

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
        'frota.Motorista', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conhecimentos_transporte', verbose_name='Motorista',
    )
    veiculo         = models.ForeignKey(
        'frota.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conhecimentos_transporte', verbose_name='Veículo',
    )

    # Percurso
    uf_inicio             = models.CharField('UF de Início', max_length=2)
    municipio_inicio      = models.CharField('Município de Início', max_length=100)
    codigo_municipio_inicio = models.CharField('Cód. IBGE Início', max_length=7, blank=True, default='',
        help_text='7 dígitos IBGE do município de início do transporte')
    uf_fim                = models.CharField('UF de Fim', max_length=2)
    municipio_fim         = models.CharField('Município de Fim', max_length=100)
    codigo_municipio_fim  = models.CharField('Cód. IBGE Fim', max_length=7, blank=True, default='',
        help_text='7 dígitos IBGE do município de fim do transporte')

    # Valores
    valor_servico              = models.DecimalField('Valor Total da Prestação', max_digits=14, decimal_places=2, default=0)
    valor_receber              = models.DecimalField('Valor a Receber', max_digits=14, decimal_places=2, default=0)
    valor_aproximado_tributos  = models.DecimalField('Valor Aproximado dos Tributos', max_digits=14, decimal_places=2, default=0)
    produto_predominante       = models.CharField('Produto Predominante', max_length=60, blank=True)
    valor_carga                = models.DecimalField('Valor da Carga', max_digits=14, decimal_places=2, default=0)
    peso_bruto_kg              = models.DecimalField('Peso Bruto (kg)', max_digits=12, decimal_places=3, default=0)
    modalidade_frete           = models.CharField('Modalidade de Frete', max_length=3, choices=MODALIDADE_FRETE, default='CIF')

    # ICMS
    CST_ICMS = [
        ('00', '00 - Tributação normal ICMS'),
        ('20', '20 - Com redução de BC'),
        ('40', '40 - Isenta'),
        ('41', '41 - Não tributada'),
        ('51', '51 - Diferimento'),
        ('60', '60 - ICMS cobrado por ST'),
        ('90', '90 - Outros'),
    ]
    cst_icms           = models.CharField('CST/COSN ICMS', max_length=3, choices=CST_ICMS, default='00')
    base_calculo_icms  = models.DecimalField('Base de Cálculo ICMS', max_digits=14, decimal_places=2, default=0)
    reducao_base_icms  = models.DecimalField('% Redução BC ICMS', max_digits=5, decimal_places=2, default=0)
    aliquota_icms      = models.DecimalField('Alíquota ICMS (%)', max_digits=5, decimal_places=2, default=0)
    valor_icms         = models.DecimalField('Valor ICMS', max_digits=14, decimal_places=2, default=0)

    # Modal Rodoviário
    rntrc_override = models.CharField(
        'RNTRC (override)',
        max_length=20, blank=True,
        help_text='Preencha apenas para sobrescrever o RNTRC da transportadora neste CT-e',
    )

    # Reforma Tributária (IBS/CBS — NT 2024)
    REFORMA_CST = [
        ('',   '--- Não informado ---'),
        ('01', '01 - Tributada integralmente'),
        ('02', '02 - Isenta'),
        ('03', '03 - Não tributada'),
        ('04', '04 - Imune'),
        ('05', '05 - Suspensa'),
        ('06', '06 - Diferimento parcial'),
        ('07', '07 - Diferimento integral'),
    ]
    REFORMA_CLASSIFICACAO = [
        ('',  '--- Não informado ---'),
        ('01', '01 - Serviço de transporte'),
        ('02', '02 - Serviço sujeito a alíquota zero'),
        ('03', '03 - Serviço isento'),
        ('04', '04 - Serviço imune'),
        ('05', '05 - Serviço não sujeito à tributação'),
    ]
    reforma_cst             = models.CharField('CST Situação Tributária (Reforma)', max_length=2, choices=REFORMA_CST, blank=True, default='')
    reforma_classificacao   = models.CharField('Classificação Tributária (Reforma)', max_length=2, choices=REFORMA_CLASSIFICACAO, blank=True, default='')

    # Partilha do ICMS (operações interestaduais)
    partilha_bc_icms              = models.DecimalField('BC Partilha ICMS', max_digits=14, decimal_places=2, default=0)
    partilha_aliq_interna_uf_fim  = models.DecimalField('Alíquota Interna UF de Fim (%)', max_digits=5, decimal_places=2, default=0)
    partilha_aliq_interestadual   = models.DecimalField('Alíquota Interestadual (%)', max_digits=5, decimal_places=2, default=0)
    partilha_percentual_uf_fim    = models.DecimalField('% Partilha UF de Fim', max_digits=5, decimal_places=2, default=0)
    partilha_valor_icms_uf_inicio = models.DecimalField('Valor ICMS Partilha UF de Início', max_digits=14, decimal_places=2, default=0)
    partilha_valor_icms_uf_fim    = models.DecimalField('Valor ICMS Partilha UF de Fim', max_digits=14, decimal_places=2, default=0)
    partilha_percentual_fcp_uf_fim = models.DecimalField('% FCP UF de Fim', max_digits=5, decimal_places=2, default=0)
    partilha_valor_fcp_uf_fim     = models.DecimalField('Valor FCP UF de Fim', max_digits=14, decimal_places=2, default=0)

    # Informações adicionais
    observacoes     = models.TextField('Observações', blank=True)

    # SEFAZ
    chave_acesso    = models.CharField('Chave de Acesso', max_length=44, blank=True)
    protocolo       = models.CharField('Protocolo de Autorização', max_length=60, blank=True)
    xml_autorizacao      = models.TextField('XML Autorizado (base64)', blank=True)
    xml_autorizacao_url  = models.URLField('URL XML Autorizado (Storage)', blank=True)
    xml_cancelamento     = models.TextField('XML Cancelamento (base64)', blank=True)
    xml_cancelamento_url = models.URLField('URL XML Cancelamento (Storage)', blank=True)
    pdf_dacte            = models.TextField('DACTE PDF (base64)', blank=True)
    pdf_dacte_url        = models.URLField('URL DACTE PDF (Storage)', blank=True)
    status               = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    motivo_cancelamento = models.CharField('Motivo do Cancelamento', max_length=255, blank=True)
    data_cancelamento   = models.DateTimeField('Data do Cancelamento', null=True, blank=True)
    data_hora_emissao   = models.DateTimeField('Data/Hora SEFAZ', null=True, blank=True)

    # Fatura (cobrança — <cobr><fat>)
    fatura_numero          = models.CharField('Número da Fatura', max_length=60, blank=True)
    fatura_valor_original  = models.DecimalField('Valor Original da Fatura', max_digits=14, decimal_places=2, default=0)
    fatura_valor_desconto  = models.DecimalField('Valor do Desconto', max_digits=14, decimal_places=2, default=0)

    # Manifesta Desacordo
    desacordo_descricao = models.CharField('Descrição do Desacordo', max_length=255, blank=True)
    desacordo_protocolo = models.CharField('Protocolo do Desacordo', max_length=50, blank=True)
    desacordo_data      = models.DateTimeField('Data/Hora do Desacordo', null=True, blank=True)

    class Meta:
        verbose_name = 'Conhecimento de Transporte (CT-e)'
        verbose_name_plural = 'Conhecimentos de Transporte (CT-e)'
        ordering = ['-data_emissao', '-numero']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'CT-e {self.numero or "S/N"}/{self.serie} — {self.remetente} → {self.destinatario}'


class ComponenteValorCTe(models.Model):
    """Componentes do valor da prestação de serviço do CT-e (<vPrest><Comp>)."""
    cte   = models.ForeignKey(ConhecimentoTransporte, on_delete=models.CASCADE, related_name='componentes_valor')
    nome  = models.CharField('Nome do Componente', max_length=60,
                              help_text='Ex: FRETE PESO, FRETE VALOR, SEC/CAT, ADEME, AGENDAMENTO')
    valor = models.DecimalField('Valor (R$)', max_digits=14, decimal_places=2, default=0)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)

    class Meta:
        verbose_name = 'Componente de Valor do CT-e'
        verbose_name_plural = 'Componentes de Valor do CT-e'
        ordering = ['ordem', 'id']

    def __str__(self):
        return f'{self.nome}: {self.valor}'


class DocumentoVinculadoCTe(models.Model):
    """NF-e ou outros documentos transportados no CT-e."""
    cte             = models.ForeignKey(ConhecimentoTransporte, on_delete=models.CASCADE, related_name='documentos_vinculados')
    chave_nfe       = models.CharField('Chave NF-e (44 dígitos)', max_length=44)
    descricao       = models.CharField('Descrição / Produto', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Documento Vinculado ao CT-e'

    def __str__(self):
        return self.chave_nfe


class CartaCorrecaoCTe(models.Model):
    cte = models.ForeignKey(
        ConhecimentoTransporte,
        on_delete=models.CASCADE,
        related_name='cartas_correcao',
        verbose_name='CT-e',
    )
    sequencia   = models.PositiveIntegerField('Sequência', default=1)
    correcao    = models.TextField('Texto da Correção')
    protocolo   = models.CharField('Protocolo SEFAZ', max_length=50, blank=True)
    xml_retorno = models.TextField('XML de Retorno (base64)', blank=True)
    criado_em   = models.DateTimeField('Criado em', auto_now_add=True)
    criado_por  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cartas_correcao_cte',
    )

    class Meta:
        verbose_name = 'Carta de Correção CT-e'
        verbose_name_plural = 'Cartas de Correção CT-e'
        ordering = ['sequencia']
        unique_together = [('cte', 'sequencia')]

    def __str__(self):
        return f'CC-e CT-e {self.sequencia} — {self.cte}'


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
    PROP_TIPO_CHOICES = [
        ('TAC',       'TAC — Transportador Autônomo de Cargas'),
        ('TAC-Agr',   'TAC Agregado'),
        ('EMP',       'Empresa'),
    ]
    PROP_TRANSP_CHOICES = [
        ('ETC',     'ETC — Empresa de Transporte de Cargas'),
        ('CTC',     'CTC — Cooperativa de Transporte de Cargas'),
        ('TAC-Ind', 'TAC Independente'),
        ('TAC-Agr', 'TAC Agregado'),
    ]

    numero          = models.PositiveIntegerField('Número MDF-e', null=True, blank=True)
    serie           = models.CharField('Série', max_length=3, default='1')
    data_emissao    = models.DateField('Data de Emissão', default=timezone.now)

    # Modal
    motorista       = models.ForeignKey(
        'frota.Motorista', on_delete=models.PROTECT,
        related_name='manifestos', verbose_name='Motorista',
    )
    veiculo         = models.ForeignKey(
        'frota.Vehicle', on_delete=models.PROTECT,
        related_name='manifestos', verbose_name='Veículo (Tração)',
    )

    # Percurso
    uf_inicio                   = models.CharField('UF de Início', max_length=2, help_text='Ex: SP')
    municipio_carregamento      = models.CharField('Município de Carregamento', max_length=100)
    codigo_municipio_carregamento = models.CharField('Código IBGE Município de Carregamento', max_length=7, blank=True, help_text='7 dígitos IBGE')
    uf_fim          = models.CharField('UF de Destino Final', max_length=2, help_text='Ex: MG')

    # Carga
    tipo_transporte = models.CharField('Tipo de Transporte', max_length=1, choices=TIPO_TRANSPORTE, default='1')
    valor_carga     = models.DecimalField('Valor Total da Carga', max_digits=14, decimal_places=2, default=0)
    peso_bruto_kg   = models.DecimalField('Peso Bruto (kg)', max_digits=12, decimal_places=3, default=0)

    # Modal Rodoviário — infANTT / Veículo de Tração extras
    rntrc_veiculo   = models.CharField('RNTRC', max_length=8, blank=True, help_text='Reg. Nac. de Transportadores Rodoviários de Carga')
    cod_ag_porto    = models.CharField('Código de Agendamento de Porto', max_length=8, blank=True)
    tipo_carroceria = models.CharField('Tipo de Carroceria', max_length=2, blank=True, choices=TIPO_CARROCERIA_CHOICES)
    tipo_rodado     = models.CharField('Tipo de Rodado',     max_length=2, blank=True, choices=TIPO_RODADO_CHOICES)
    # Dados do veículo de tração editáveis no MDF-e (sobrescrevem o cadastro do veículo)
    placa_tracao    = models.CharField('Placa (tração)', max_length=7, blank=True, default='')
    uf_tracao       = models.CharField('UF (tração)',    max_length=2, blank=True, default='')
    tara_tracao_kg  = models.IntegerField('Tara (kg) tração', null=True, blank=True)

    # Proprietário/Possuidor do Veículo (quando diferente do emitente)
    proprietario_diferente      = models.BooleanField('Proprietário/Possuidor diferente do emitente', default=False)
    prop_tipo                   = models.CharField('Tipo de Proprietário/Possuidor', max_length=10, blank=True, choices=PROP_TIPO_CHOICES)
    prop_cpf_cnpj               = models.CharField('CPF/CNPJ do Proprietário', max_length=14, blank=True)
    prop_nome                   = models.CharField('Nome do Proprietário', max_length=60, blank=True)
    prop_ie                     = models.CharField('Inscrição Estadual do Proprietário', max_length=14, blank=True)
    prop_uf                     = models.CharField('UF do Proprietário', max_length=2, blank=True)
    prop_rntrc                  = models.CharField('RNTRC do Proprietário', max_length=8, blank=True)
    prop_tipo_transportador     = models.CharField('Tipo de Transportador', max_length=10, blank=True, choices=PROP_TRANSP_CHOICES)

    # Informações adicionais
    informacoes_fisco       = models.TextField('Informações para o Fisco', blank=True)
    informacoes_contribuinte = models.TextField('Informações do Contribuinte', blank=True)

    # SEFAZ
    chave_acesso    = models.CharField('Chave de Acesso', max_length=44, blank=True)
    protocolo       = models.CharField('Protocolo de Autorização', max_length=60, blank=True)
    xml_autorizacao     = models.TextField('XML Autorizado (base64)', blank=True)
    xml_autorizacao_url = models.URLField('URL XML Autorizado (Storage)', blank=True)
    pdf_damdfe          = models.TextField('DAMDFE PDF (base64)', blank=True)
    pdf_damdfe_url      = models.URLField('URL DAMDFE PDF (Storage)', blank=True)
    status              = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
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
    municipio_descarregamento        = models.CharField('Município de Descarregamento', max_length=100)
    codigo_municipio_descarregamento = models.CharField('Código IBGE', max_length=7, blank=True, help_text='7 dígitos IBGE')
    cep_descarregamento              = models.CharField('CEP de Entrega', max_length=8, blank=True, help_text='8 dígitos sem hífen')

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


class CondutorAdicionalMDFe(models.Model):
    """Condutor incluído no MDF-e após emissão via API IntegraNota."""
    mdfe            = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='condutores_adicionais')
    cpf             = models.CharField('CPF', max_length=14)
    nome            = models.CharField('Nome', max_length=100)
    protocolo       = models.CharField('Protocolo SEFAZ', max_length=50, blank=True)
    adicionado_em   = models.DateTimeField(auto_now_add=True)
    adicionado_por  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'Condutor Adicional MDF-e'
        ordering = ['adicionado_em']

    def __str__(self):
        return f'{self.nome} — {self.cpf}'


class CondutorMDFe(models.Model):
    """Condutores incluídos no MDF-e antes da emissão (veicTracao.condutor)."""
    mdfe    = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='condutores')
    cpf     = models.CharField('CPF', max_length=14)
    nome    = models.CharField('Nome', max_length=60)
    ordem   = models.PositiveSmallIntegerField('Ordem', default=1)

    class Meta:
        verbose_name = 'Condutor MDF-e'
        ordering = ['ordem']

    def __str__(self):
        return f'{self.nome} ({self.cpf})'


class ReboqueMDFe(models.Model):
    """Veículos de reboque (veicReboque) vinculados ao MDF-e."""
    PROP_TIPO_CHOICES = ManifestoDocumentoFiscal.PROP_TIPO_CHOICES
    PROP_TRANSP_CHOICES = ManifestoDocumentoFiscal.PROP_TRANSP_CHOICES
    TIPO_CARROCERIA_CHOICES = [
        ('00', '00 - Não Aplicável'), ('01', '01 - Aberta'), ('02', '02 - Fechada/Baú'),
        ('03', '03 - Graneleira'), ('04', '04 - Porta Container'), ('05', '05 - Sider'),
    ]

    mdfe                = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='reboques')
    placa               = models.CharField('Placa', max_length=7)
    uf                  = models.CharField('UF', max_length=2)
    rntrc               = models.CharField('RNTRC', max_length=8, blank=True)
    tipo_carroceria     = models.CharField('Tipo de Carroceria', max_length=2, blank=True, choices=TIPO_CARROCERIA_CHOICES)
    tara_kg             = models.IntegerField('Tara (kg)', null=True, blank=True)
    renavam             = models.CharField('RENAVAM', max_length=9, blank=True)
    capacidade_kg       = models.IntegerField('Capacidade (kg)', null=True, blank=True)
    capacidade_m3       = models.IntegerField('Capacidade (m³)', null=True, blank=True)
    # Proprietário (quando diferente do emitente)
    prop_tipo           = models.CharField('Tipo de Proprietário', max_length=10, blank=True, choices=PROP_TIPO_CHOICES)
    prop_cpf_cnpj       = models.CharField('CPF/CNPJ do Proprietário', max_length=14, blank=True)
    prop_nome           = models.CharField('Nome do Proprietário', max_length=60, blank=True)
    prop_ie             = models.CharField('IE do Proprietário', max_length=14, blank=True)
    prop_uf             = models.CharField('UF do Proprietário', max_length=2, blank=True)
    prop_rntrc          = models.CharField('RNTRC do Proprietário', max_length=8, blank=True)
    prop_tipo_transportador = models.CharField('Tipo de Transportador', max_length=10, blank=True, choices=PROP_TRANSP_CHOICES)

    class Meta:
        verbose_name = 'Reboque MDF-e'
        ordering = ['id']

    def __str__(self):
        return f'Reboque {self.placa}/{self.uf}'


class CiotMDFe(models.Model):
    """CIOT — Código Identificador da Operação de Transporte (infCIOT)."""
    mdfe        = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='ciots')
    ciot        = models.CharField('Código CIOT', max_length=20)
    cpf_cnpj    = models.CharField('CPF/CNPJ Responsável', max_length=14)

    class Meta:
        verbose_name = 'CIOT MDF-e'

    def __str__(self):
        return f'CIOT {self.ciot}'


class ContratanteMDFe(models.Model):
    """Contratante do serviço de transporte (infContratante)."""
    mdfe        = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='contratantes')
    cpf_cnpj    = models.CharField('CPF/CNPJ', max_length=14)
    ie          = models.CharField('Inscrição Estadual', max_length=14, blank=True)
    n_contrato  = models.CharField('Número do Contrato', max_length=20, blank=True)
    v_contrato  = models.DecimalField('Valor do Contrato (R$)', max_digits=15, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Contratante MDF-e'

    def __str__(self):
        return f'Contratante {self.cpf_cnpj}'


class ValePedagioMDFe(models.Model):
    """Vale Pedágio (valePed) vinculado ao MDF-e."""
    TP_VALE = [
        ('01', '01 - Tarjeta'),
        ('02', '02 - Vale Pedágio Eletrônico'),
        ('03', '03 - Vale Pedágio Pré-pago'),
    ]
    mdfe            = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='vales_pedagio')
    cnpj_fornecedor = models.CharField('CNPJ do Fornecedor', max_length=14)
    n_compra        = models.CharField('Número da Compra', max_length=20)
    valor           = models.DecimalField('Valor do Vale (R$)', max_digits=15, decimal_places=2)
    tp_vale         = models.CharField('Tipo de Vale Pedágio', max_length=2, blank=True, choices=TP_VALE)

    class Meta:
        verbose_name = 'Vale Pedágio MDF-e'

    def __str__(self):
        return f'Vale Pedágio {self.n_compra} — R$ {self.valor}'


class PagamentoFreteMDFe(models.Model):
    """Informações de pagamento do frete (infPag)."""
    RESPONSAVEL = [
        ('1', '1 - Emitente do MDF-e'),
        ('2', '2 - Expedidor'),
        ('3', '3 - Recebedor'),
        ('4', '4 - Tomador do Serviço'),
        ('5', '5 - Outros'),
    ]
    TP_COMP = [
        ('01', '01 - Vale Pedágio'),
        ('02', '02 - Alimentação'),
        ('03', '03 - Combustível'),
        ('04', '04 - Ajudante'),
        ('05', '05 - Comissão'),
        ('06', '06 - Outros'),
    ]
    mdfe            = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='pagamentos_frete')
    x_nome          = models.CharField('Nome', max_length=60, blank=True)
    cpf_cnpj        = models.CharField('CPF/CNPJ', max_length=14)
    responsavel     = models.CharField('Responsável', max_length=1, choices=RESPONSAVEL, default='1')
    ind_pag         = models.CharField('Indicador (0=À Vista/1=A Prazo)', max_length=1, blank=True)
    vr_total        = models.DecimalField('Valor Total (R$)', max_digits=15, decimal_places=2, null=True, blank=True)
    tp_antecip      = models.CharField('Tipo de Antecipação', max_length=1, blank=True)
    # Componentes de pagamento (armazenados como JSON ou serializado)
    componentes_json = models.TextField('Componentes (JSON)', blank=True,
                                        help_text='Lista de componentes: [{"tp_comp":"01","v_comp":100.00}, ...]')

    class Meta:
        verbose_name = 'Pagamento de Frete MDF-e'

    def __str__(self):
        return f'Pagamento {self.get_responsavel_display()} — {self.cpf_cnpj}'


class SeguroMDFe(models.Model):
    """Informações de seguro da carga (seg)."""
    RESPONSAVEL = [
        ('1', '1 - Emitente do MDF-e'),
        ('2', '2 - Contratante do Seguro'),
    ]
    mdfe        = models.ForeignKey(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='seguros')
    responsavel = models.CharField('Responsável pelo Seguro', max_length=1, choices=RESPONSAVEL, default='1')
    seguradora  = models.CharField('Nome da Seguradora', max_length=30, blank=True)
    n_apolice   = models.CharField('Número da Apólice', max_length=20)
    n_averbacao = models.CharField('Número de Averbação', max_length=40, blank=True)

    class Meta:
        verbose_name = 'Seguro MDF-e'

    def __str__(self):
        return f'Seguro {self.n_apolice} — {self.seguradora}'


class ProdutoPredominanteMDFe(models.Model):
    """Produto predominante da carga (prodPred) — 0 ou 1 por MDF-e."""
    TIPO_CARGA = [
        ('01', '01 - Granel sólido'),
        ('02', '02 - Granel líquido'),
        ('03', '03 - Frigorificada'),
        ('04', '04 - Conteinerizada'),
        ('05', '05 - Carga Geral'),
        ('06', '06 - Neogranel'),
        ('07', '07 - Perigosa (granel sólido)'),
        ('08', '08 - Perigosa (granel líquido)'),
        ('09', '09 - Perigosa (carga frigorificada)'),
        ('10', '10 - Perigosa (conteinerizada)'),
        ('11', '11 - Perigosa (carga geral)'),
        ('12', '12 - Granel pressurizada'),
    ]
    TIPO_MEDIDA = [
        ('01', '01 - M3'),
        ('02', '02 - KG'),
        ('03', '03 - Tonelada'),
        ('04', '04 - Unidade'),
        ('05', '05 - Litros'),
        ('06', '06 - Mmbtu'),
    ]
    mdfe        = models.OneToOneField(ManifestoDocumentoFiscal, on_delete=models.CASCADE, related_name='produto_predominante')
    c_prod      = models.CharField('Código do Produto (NCM ou interno)', max_length=20, blank=True)
    x_prod      = models.CharField('Descrição do Produto', max_length=120, blank=True)
    tipo_carga  = models.CharField('Tipo de Carga', max_length=2, blank=True, choices=TIPO_CARGA)
    tipo_medida = models.CharField('Tipo de Medida', max_length=2, blank=True, choices=TIPO_MEDIDA)
    q_carga     = models.DecimalField('Quantidade', max_digits=11, decimal_places=4, null=True, blank=True)

    class Meta:
        verbose_name = 'Produto Predominante MDF-e'

    def __str__(self):
        return f'{self.x_prod} ({self.c_prod})'


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


class CotacaoBCB(models.Model):
    MOEDAS = [
        ('USD', 'Dólar EUA (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'Libra Esterlina (GBP)'),
    ]

    data = models.DateField('Data de Referência', db_index=True)
    moeda = models.CharField('Moeda', max_length=3, choices=MOEDAS)
    compra = models.DecimalField('Taxa Compra', max_digits=10, decimal_places=4)
    venda = models.DecimalField('Taxa Venda', max_digits=10, decimal_places=4)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        unique_together = [('data', 'moeda')]
        ordering = ['-data', 'moeda']
        verbose_name = 'Cotação BCB'
        verbose_name_plural = 'Cotações BCB'

    def __str__(self):
        return f'{self.moeda} {self.data} — Compra: {self.compra} / Venda: {self.venda}'
