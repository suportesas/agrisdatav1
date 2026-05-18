from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


# ──────────────────────────── TipoEmbalagem ────────────────────────────────

class TipoEmbalagem(models.Model):
    """
    Configuração de embalagem padrão: define caixa e pallet para um produto/cultura.
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='tipos_embalagem',
        verbose_name='Empresa',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='tipos_embalagem',
        verbose_name='Produto',
        blank=True,
        null=True,
    )
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        related_name='tipos_embalagem',
        verbose_name='Cultura',
        blank=True,
        null=True,
    )
    nome = models.CharField('Nome da Embalagem', max_length=100,
                            help_text='Ex: Caixa 5kg Manga Tommy')
    variedade = models.CharField('Variedade', max_length=100, blank=True)
    marca = models.CharField('Marca', max_length=100, blank=True)
    tipo_calibre = models.CharField('Tipo / Calibre', max_length=20, blank=True,
                                    help_text='Ex: 2, 3, 14')
    peso_liquido_cx = models.DecimalField(
        'Peso Líquido por Caixa (kg)', max_digits=10, decimal_places=3)
    peso_bruto_cx = models.DecimalField(
        'Peso Bruto por Caixa (kg)', max_digits=10, decimal_places=3,
        help_text='Inclui tara da embalagem')
    caixas_por_pallet = models.PositiveIntegerField('Caixas por Pallet')
    peso_pallet_vazio = models.DecimalField(
        'Tara do Pallet (kg)', max_digits=10, decimal_places=3, default=0)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Embalagem'
        verbose_name_plural = 'Tipos de Embalagem'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def peso_liquido_pallet(self):
        return self.peso_liquido_cx * self.caixas_por_pallet

    @property
    def peso_bruto_pallet(self):
        return (self.peso_bruto_cx * self.caixas_por_pallet) + self.peso_pallet_vazio


# ──────────────────────────── OrdemEmbalagem ───────────────────────────────

class OrdemEmbalagem(models.Model):
    STATUS = [
        ('ABERTA', 'Aberta'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='ordens_embalagem',
        verbose_name='Empresa',
    )
    numero = models.CharField('Número', max_length=20, unique=True, blank=True)
    data = models.DateField('Data', default=timezone.now)
    tipo_embalagem = models.ForeignKey(
        TipoEmbalagem,
        on_delete=models.PROTECT,
        related_name='ordens',
        verbose_name='Tipo de Embalagem',
    )
    lote_origem = models.ForeignKey(
        'estoque.Lote',
        on_delete=models.PROTECT,
        related_name='ordens_embalagem',
        verbose_name='Lote de Origem (Produto a Granel)',
    )
    quantidade_entrada_kg = models.DecimalField(
        'Qtd Entrada (kg)', max_digits=14, decimal_places=3,
        help_text='Kg de produto bruto que entrou no packing')
    armazem_destino = models.ForeignKey(
        'estoque.Armazem',
        on_delete=models.PROTECT,
        related_name='ordens_embalagem_destino',
        verbose_name='Armazém de Destino',
    )
    local_destino = models.ForeignKey(
        'estoque.LocalEstocagem',
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem',
        verbose_name='Local de Estocagem',
        blank=True,
        null=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='ABERTA')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem_responsavel',
        verbose_name='Responsável',
        blank=True,
        null=True,
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ordens_embalagem_criadas',
        verbose_name='Criado por',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Ordem de Embalagem'
        verbose_name_plural = 'Ordens de Embalagem'
        ordering = ['-criado_em']

    def __str__(self):
        return self.numero or f'OE-{self.pk}'

    @classmethod
    def _gerar_numero(cls, empresa):
        ano = timezone.now().year
        ultimo = (cls.objects
                  .filter(empresa=empresa, numero__startswith=f'OE-{ano}-')
                  .order_by('numero')
                  .last())
        if ultimo and ultimo.numero:
            try:
                seq = int(ultimo.numero.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'OE-{ano}-{seq:04d}'

    @property
    def n_pallets(self):
        return self.pallets.count()

    @property
    def n_pallets_esperados(self):
        lp = self.tipo_embalagem.peso_liquido_pallet
        if lp:
            return int(self.quantidade_entrada_kg / lp)
        return 0


# ──────────────────────────── PalletEmbalado ───────────────────────────────

class PalletEmbalado(models.Model):
    STATUS = [
        ('DISPONIVEL', 'Disponível'),
        ('RESERVADO', 'Reservado'),
        ('CARREGADO', 'Carregado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='pallets_embalados',
        verbose_name='Empresa',
    )
    codigo_pallet = models.CharField('Código do Pallet', max_length=30, unique=True)
    ordem_embalagem = models.ForeignKey(
        OrdemEmbalagem,
        on_delete=models.CASCADE,
        related_name='pallets',
        verbose_name='Ordem de Embalagem',
    )
    tipo_embalagem = models.ForeignKey(
        TipoEmbalagem,
        on_delete=models.PROTECT,
        related_name='pallets',
        verbose_name='Tipo de Embalagem',
    )
    numero_sequencial = models.PositiveIntegerField('Nº Sequencial na Ordem')
    quantidade_caixas = models.PositiveIntegerField('Qtd de Caixas')
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=3)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=3)
    data_embalagem = models.DateField('Data de Embalagem', default=timezone.now)
    armazem = models.ForeignKey(
        'estoque.Armazem',
        on_delete=models.PROTECT,
        related_name='pallets_embalados',
        verbose_name='Armazém',
    )
    local_estocagem = models.ForeignKey(
        'estoque.LocalEstocagem',
        on_delete=models.SET_NULL,
        related_name='pallets_embalados',
        verbose_name='Local de Estocagem',
        blank=True,
        null=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='DISPONIVEL')
    etiqueta_gerada = models.BooleanField('Etiqueta Gerada', default=False)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Pallet Embalado'
        verbose_name_plural = 'Pallets Embalados'
        ordering = ['codigo_pallet']
        unique_together = [('ordem_embalagem', 'numero_sequencial')]

    def __str__(self):
        return self.codigo_pallet

    @classmethod
    def _gerar_codigo(cls, empresa, data=None):
        from django.utils.timezone import now as tz_now
        d = data or tz_now().date()
        prefixo = f'PLT-{d.strftime("%Y%m%d")}-'
        ultimo = (cls.objects
                  .filter(empresa=empresa, codigo_pallet__startswith=prefixo)
                  .order_by('codigo_pallet')
                  .last())
        if ultimo:
            try:
                seq = int(ultimo.codigo_pallet.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'{prefixo}{seq:04d}'


# ──────────────────────────── RomaneioVenda ────────────────────────────────

class RomaneioVenda(models.Model):
    TIPO = [
        ('EXPORTACAO', 'Exportação'),
        ('MERCADO_INTERNO', 'Mercado Interno'),
    ]
    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('CONFIRMADO', 'Confirmado'),
        ('CARREGANDO', 'Carregando'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='romaneios_venda',
        verbose_name='Empresa',
    )
    numero = models.CharField('Número', max_length=20, unique=True, blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO, default='EXPORTACAO')
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        related_name='romaneios_venda',
        verbose_name='Cliente',
    )
    data = models.DateField('Data', default=timezone.now)
    pedido_venda = models.OneToOneField(
        'vendas.PedidoVenda',
        on_delete=models.SET_NULL,
        related_name='romaneio_venda',
        verbose_name='Pedido de Venda',
        blank=True,
        null=True,
    )
    # Exportação
    booking = models.ForeignKey(
        'exportacao.Booking',
        on_delete=models.SET_NULL,
        related_name='romaneios_venda',
        verbose_name='Booking',
        blank=True,
        null=True,
    )
    container = models.ForeignKey(
        'exportacao.BookingContainer',
        on_delete=models.SET_NULL,
        related_name='romaneios_venda',
        verbose_name='Container',
        blank=True,
        null=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='romaneios_venda_criados',
        verbose_name='Criado por',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Romaneio de Venda'
        verbose_name_plural = 'Romaneios de Venda'
        ordering = ['-criado_em']

    def __str__(self):
        return self.numero or f'RV-{self.pk}'

    @classmethod
    def _gerar_numero(cls, empresa):
        ano = timezone.now().year
        ultimo = (cls.objects
                  .filter(empresa=empresa, numero__startswith=f'RV-{ano}-')
                  .order_by('numero')
                  .last())
        if ultimo and ultimo.numero:
            try:
                seq = int(ultimo.numero.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'RV-{ano}-{seq:04d}'

    @property
    def total_pallets(self):
        return self.itens.count()

    @property
    def total_caixas(self):
        return sum(i.quantidade_caixas for i in self.itens.all())

    @property
    def peso_bruto_total(self):
        return sum(i.peso_bruto_kg for i in self.itens.all()) or Decimal('0')

    @property
    def peso_liquido_total(self):
        return sum(i.peso_liquido_kg for i in self.itens.all()) or Decimal('0')

    @property
    def pallets_conferidos(self):
        return self.itens.filter(status_conferencia='CONFERIDO').count()


# ──────────────────────────── ItemRomaneioVenda ────────────────────────────

class ItemRomaneioVenda(models.Model):
    STATUS_CONFERENCIA = [
        ('PENDENTE', 'Pendente'),
        ('CONFERIDO', 'Conferido'),
        ('DIVERGENTE', 'Divergente'),
    ]

    romaneio = models.ForeignKey(
        RomaneioVenda,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Romaneio',
    )
    pallet = models.ForeignKey(
        PalletEmbalado,
        on_delete=models.PROTECT,
        related_name='itens_romaneio',
        verbose_name='Pallet',
    )
    quantidade_caixas = models.PositiveIntegerField('Qtd de Caixas')
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=10, decimal_places=3)
    peso_liquido_kg = models.DecimalField('Peso Líquido (kg)', max_digits=10, decimal_places=3)
    marks_numbers = models.CharField('Marks & Numbers', max_length=100, blank=True)
    status_conferencia = models.CharField(
        'Status Conferência', max_length=20,
        choices=STATUS_CONFERENCIA, default='PENDENTE',
    )
    data_conferencia = models.DateTimeField('Data da Conferência', blank=True, null=True)
    conferido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='itens_romaneio_conferidos',
        verbose_name='Conferido por',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'Item do Romaneio'
        verbose_name_plural = 'Itens do Romaneio'
        ordering = ['pallet__codigo_pallet']
        unique_together = [('romaneio', 'pallet')]

    def __str__(self):
        return f'{self.romaneio} / {self.pallet}'
