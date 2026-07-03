from django.conf import settings
from django.db import models
from django.utils import timezone


# ──────────────────────────── LoteEtiquetaAvulsa ────────────────────────────

class LoteEtiquetaAvulsa(models.Model):
    """Cabeçalho de um lote de etiquetas de pallet avulso.
    Guarda os campos comuns preenchidos uma vez (equivalente ao diálogo de
    'Paletização'); cada pallet do lote vira um EtiquetaAvulsa individual.
    """
    ORIGEM = [
        ('UI', 'Interno'),
        ('API', 'API Externa'),
    ]
    STATUS = [
        ('ABERTA', 'Aberta'),
        ('CONCLUIDA', 'Concluída'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='lotes_etiqueta_avulsa',
        verbose_name='Empresa',
    )
    numero_lote = models.CharField('Número do Lote', max_length=20, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='ABERTA')
    origem = models.CharField('Origem', max_length=10, choices=ORIGEM, default='UI')
    api_key = models.ForeignKey(
        'empresas.APIKey',
        on_delete=models.SET_NULL,
        related_name='lotes_criados',
        verbose_name='Chave de API',
        null=True,
        blank=True,
    )

    # Safra — define o prefixo do código de barras dos pallets (reinicia a sequência a cada safra)
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa',
        verbose_name='Safra',
        null=True,
        blank=True,
    )
    safra_texto = models.CharField(
        'Safra (código)', max_length=10, blank=True,
        help_text='Código da safra (ex: 202526). Define o prefixo do código de barras.')

    # Fazenda
    fazenda = models.ForeignKey(
        'cadastros.Fazenda',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa',
        verbose_name='Fazenda',
        null=True,
        blank=True,
    )
    fazenda_texto = models.CharField('Fazenda', max_length=150, blank=True)

    # Importador / Cliente
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa',
        verbose_name='Importador / Cliente',
        null=True,
        blank=True,
    )
    cliente_texto = models.CharField('Importador / Cliente', max_length=150, blank=True)
    cliente_final_texto = models.CharField('Cliente Final', max_length=150, blank=True)

    # Portos
    porto_origem = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa_origem',
        verbose_name='Porto Origem',
        null=True,
        blank=True,
    )
    porto_origem_texto = models.CharField('Porto Origem', max_length=150, blank=True)
    porto_destino = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa_destino',
        verbose_name='Porto Destino',
        null=True,
        blank=True,
    )
    porto_destino_texto = models.CharField('Porto Destino', max_length=150, blank=True)

    # Navio
    navio = models.ForeignKey(
        'cadastros.Navio',
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa',
        verbose_name='Navio',
        null=True,
        blank=True,
    )
    navio_texto = models.CharField('Navio', max_length=150, blank=True)

    total_pallets = models.PositiveIntegerField('Total de Pallets', default=0)
    comentarios = models.TextField('Comentários', blank=True)

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='lotes_etiqueta_avulsa_criados',
        verbose_name='Criado por',
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Lote de Etiqueta Avulsa'
        verbose_name_plural = 'Lotes de Etiqueta Avulsa'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'criado_em']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'numero_lote'], name='unique_numero_lote_por_empresa'),
        ]

    def __str__(self):
        return self.numero_lote or f'LTA-{self.pk}'

    @classmethod
    def _gerar_numero(cls, empresa):
        ano = timezone.now().year
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, numero_lote__startswith=f'LTA-{ano}-')
                  .order_by('numero_lote')
                  .last())
        if ultimo and ultimo.numero_lote:
            try:
                seq = int(ultimo.numero_lote.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'LTA-{ano}-{seq:04d}'

    @property
    def safra_codigo(self):
        if self.safra and self.safra.codigo:
            return self.safra.codigo
        return self.safra_texto

    @property
    def fazenda_nome(self):
        return self.fazenda.nome if self.fazenda else self.fazenda_texto

    @property
    def cliente_nome(self):
        return self.cliente.razao_social if self.cliente else self.cliente_texto

    @property
    def porto_origem_nome(self):
        return self.porto_origem.nome if self.porto_origem else self.porto_origem_texto

    @property
    def porto_destino_nome(self):
        return self.porto_destino.nome if self.porto_destino else self.porto_destino_texto

    @property
    def navio_nome(self):
        return self.navio.nome if self.navio else self.navio_texto

    @property
    def produtos_resumo(self):
        """Lista (sem repetição) dos produtos das levas já adicionadas a este
        lote — uma carga pode misturar mais de um produto."""
        nomes = []
        for et in self.etiquetas.filter(ativo=True).select_related('produto'):
            nome = et.produto_nome
            if nome and nome not in nomes:
                nomes.append(nome)
        return ', '.join(nomes) if nomes else '—'


# ──────────────────────────── EtiquetaAvulsa ────────────────────────────────

class EtiquetaAvulsa(models.Model):
    """Uma linha por pallet físico — a unidade imprimível/escaneável do lote."""
    STATUS = [
        ('GERADA', 'Gerada'),
        ('IMPRESSA', 'Impressa'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='etiquetas_avulsas',
        verbose_name='Empresa',
    )
    lote = models.ForeignKey(
        LoteEtiquetaAvulsa,
        on_delete=models.CASCADE,
        related_name='etiquetas',
        verbose_name='Lote',
    )
    codigo_pallet = models.CharField('Código do Pallet', max_length=30)
    numero_sequencial = models.PositiveIntegerField('Nº na sequência do lote')

    # Produto — cada leva de pallets adicionada pode ter um produto diferente
    # (uma carga pode misturar mais de um tipo de produto).
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.SET_NULL,
        related_name='etiquetas_avulsas',
        verbose_name='Produto',
        null=True,
        blank=True,
    )
    produto_texto = models.CharField('Produto', max_length=150, blank=True)
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.SET_NULL,
        related_name='etiquetas_avulsas',
        verbose_name='Cultura',
        null=True,
        blank=True,
    )
    variedade = models.CharField('Variedade', max_length=100, blank=True)
    embalagem = models.CharField('Embalagem', max_length=100, blank=True)
    marca = models.ForeignKey(
        'produtos.Marca',
        on_delete=models.SET_NULL,
        related_name='etiquetas_avulsas',
        verbose_name='Marca',
        null=True,
        blank=True,
    )
    marca_texto = models.CharField('Marca', max_length=100, blank=True)
    cultivares = models.CharField('Cultivares', max_length=150, blank=True)
    tipo_size = models.CharField('Tipo / Size', max_length=30, blank=True)
    temperatura = models.CharField('Temperatura', max_length=20, blank=True)
    carimbo = models.CharField('Carimbo (Trace/Lote)', max_length=50, blank=True)
    peso_liquido_cx = models.DecimalField(
        'Peso Líquido/Caixa (kg)', max_digits=10, decimal_places=3, null=True, blank=True)
    peso_bruto_cx = models.DecimalField(
        'Peso Bruto/Caixa (kg)', max_digits=10, decimal_places=3, null=True, blank=True)

    caixas = models.PositiveIntegerField('Caixas')
    status = models.CharField('Status', max_length=20, choices=STATUS, default='GERADA')
    impressa_em = models.DateTimeField('Impressa em', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Etiqueta Avulsa'
        verbose_name_plural = 'Etiquetas Avulsas'
        ordering = ['numero_sequencial']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['codigo_pallet']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo_pallet'], name='unique_codigo_pallet_por_empresa'),
        ]

    def __str__(self):
        return self.codigo_pallet

    @property
    def produto_nome(self):
        return self.produto.nome if self.produto else self.produto_texto

    @property
    def marca_nome(self):
        return self.marca.nome if self.marca else self.marca_texto

    @classmethod
    def _gerar_codigo_base(cls, empresa):
        """Sem safra informada: gera um código-base genérico por lote (ex: 100000).
        Cada pallet do lote soma um sufixo sequencial: {base}-1, {base}-2, ..."""
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa)
                  .order_by('-id')
                  .first())
        if ultimo:
            try:
                base_num = int(ultimo.codigo_pallet.split('-')[0])
                return str(base_num + 1)
            except (ValueError, IndexError):
                pass
        return '100000'

    @classmethod
    def _gerar_codigo_por_safra(cls, empresa, prefixo):
        """Com safra informada: o código de cada pallet é {prefixo}-{seq}, com
        `seq` contínuo entre lotes da mesma safra — só reinicia quando o
        código da safra muda."""
        base_prefix = f'{prefixo}-'
        ultimo = (cls.objects
                  .select_for_update()
                  .filter(empresa=empresa, codigo_pallet__startswith=base_prefix)
                  .order_by('-id')
                  .first())
        if ultimo:
            try:
                seq = int(ultimo.codigo_pallet[len(base_prefix):]) + 1
            except (ValueError, IndexError):
                seq = 1
        else:
            seq = 1
        return f'{prefixo}-{seq}'
