from django.conf import settings
from django.db import models
from django.utils import timezone


class ExportacaoBaseModel(models.Model):
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


class SolicitacaoBooking(ExportacaoBaseModel):
    STATUS = [
        ('ABERTO', 'Aberto'),
        ('APROVADO', 'Aprovado'),
        ('NEGADO', 'Negado'),
        ('CANCELADO', 'Cancelado'),
    ]

    FRETE_CHOICES = [
        ('FREIGHT_COLLECT', 'Freight Collect - Fob (a cobrar)'),
        ('FREIGHT_PREPAID', 'Freight Prepaid - CIF (pré-pago)'),
    ]

    GENSET_CHOICES = [
        ('COM_GENSET', 'Com Genset'),
        ('SEM_GENSET', 'Sem Genset'),
    ]

    TIPO_EXPORTACAO_CHOICES = [
        ('CONTEINER', 'Contêiner'),
        ('GRANELEIRA', 'Graneleira'),
        ('REEFER', 'Reefer'),
        ('OUTROS', 'Outros'),
    ]

    nome = models.CharField('Nome da Solicitação', max_length=200)
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='solicitacoes_booking',
        verbose_name='Cliente',
    )
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='solicitacoes_booking',
        verbose_name='Cultura',
    )
    data_solicitacao = models.DateTimeField('Data de Solicitação', auto_now_add=True)
    data_prevista_embarque = models.DateField('Previsão de Embarque', blank=True, null=True)
    quantidade = models.DecimalField('Quantidade de containers', max_digits=14, decimal_places=3, blank=True, null=True)
    porto_origem = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='solicitacoes_origem',
        verbose_name='Porto de Origem',
    )
    porto_destino = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='solicitacoes_destino',
        verbose_name='Porto de Destino',
    )
    armador = models.ForeignKey(
        'cadastros.Armador',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='solicitacoes_booking',
        verbose_name='Armador',
    )
    navio = models.ForeignKey(
        'cadastros.Navio',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='solicitacoes_booking',
        verbose_name='Navio',
    )
    frete = models.CharField(
        'Frete',
        max_length=20,
        choices=FRETE_CHOICES,
        default='FREIGHT_COLLECT',
        blank=True,
    )
    genset = models.CharField(
        'Genset',
        max_length=20,
        choices=GENSET_CHOICES,
        blank=True,
    )
    tipo_exportacao = models.CharField(
        'Tipo de Exportação',
        max_length=20,
        choices=TIPO_EXPORTACAO_CHOICES,
        blank=True,
    )
    tipo_exportacao_outros = models.CharField(
        'Especificação (Outros)',
        max_length=200,
        blank=True,
    )
    status = models.CharField('Status', max_length=20, choices=STATUS, default='ABERTO')
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Solicitação de Booking'
        verbose_name_plural = 'Solicitações de Booking'
        ordering = ['-data_solicitacao']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'{self.nome} ({self.status})'


class Booking(ExportacaoBaseModel):
    TIPO_EXPORTACAO = [
        ('CONTÊINER', 'Contêiner'),
        ('GRANELEIRA', 'Graneleira'),
        ('REEFER', 'Reefer'),
        ('OUTRO', 'Outro'),
    ]

    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('ABERTO', 'Aberto'),
        ('CONFIRMADO', 'Confirmado'),
        ('EMBARCADO', 'Embarcado'),
        ('CONCLUÍDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    solicitacao = models.ForeignKey(
        SolicitacaoBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='bookings',
        verbose_name='Solicitação',
    )
    codigo = models.CharField('Código do Booking', max_length=30, blank=True, null=True, db_index=True)
    tipo_exportacao = models.CharField('Tipo de Exportação', max_length=20, choices=TIPO_EXPORTACAO, default='CONTÊINER')
    transportadora = models.ForeignKey(
        'cadastros.Transportadora',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='bookings',
        verbose_name='Transportadora',
    )
    porto_origem = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='bookings_origem',
        verbose_name='Porto de Origem',
    )
    porto_destino = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='bookings_destino',
        verbose_name='Porto de Destino',
    )
    data_embarque_previsto = models.DateField('Previsão de Embarque', blank=True, null=True)
    data_embarque_realizado = models.DateField('Data de Embarque', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    valor_fob = models.DecimalField('Valor FOB', max_digits=14, decimal_places=2, blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True)
    rota_navio = models.CharField('Rota do Navio (VIAGEM)', max_length=100, blank=True)
    deadline_draft = models.DateTimeField('DEADLINE DRAFT', null=True, blank=True)
    deadline_carga = models.DateTimeField('DEADLINE CARGA', null=True, blank=True)
    etd = models.DateTimeField('ETD', null=True, blank=True)
    eta = models.DateTimeField('ETA', null=True, blank=True)

    class Meta:
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'
        ordering = ['-data_embarque_previsto', '-criado_em']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='unique_booking_codigo_por_empresa'),
        ]
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'{self.codigo or "Booking"} - {self.get_status_display()}'

    @property
    def containers_count(self):
        return self.containers.count()


class BookingContainer(ExportacaoBaseModel):
    TIPOS = [
        ('20GP', '20 GP'),
        ('40GP', '40 GP'),
        ('40HC', '40 HC'),
        ('REEFER', 'Reefer'),
        ('OUTRO', 'Outro'),
    ]

    STATUS = [
        ('PENDENTE', 'Pendente'),
        ('CONFIRMADO', 'Confirmado'),
        ('EMBARCADO', 'Embarcado'),
        ('DESLOCADO', 'Deslocado'),
        ('DEVOLVIDO', 'Devolvido'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='containers',
        verbose_name='Booking',
    )
    numero_container = models.CharField('Número do Contêiner', max_length=30)
    tipo_container = models.CharField('Tipo de Contêiner', max_length=20, choices=TIPOS, default='20GP')
    status = models.CharField('Status', max_length=20, choices=STATUS, default='PENDENTE')
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name='booking_containers',
        verbose_name='Cultura',
    )
    peso_bruto_kg = models.DecimalField('Peso Bruto (kg)', max_digits=14, decimal_places=2, blank=True, null=True)
    lacre_armador = models.CharField('Lacre do Armador', max_length=50, blank=True)
    lacre_fiscal = models.CharField('Lacre Fiscal', max_length=50, blank=True)
    lacre_terminal = models.CharField('Lacre do Terminal', max_length=50, blank=True)
    porto_origem = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='containers_origem',
        verbose_name='Porto de Origem',
    )
    porto_destino = models.ForeignKey(
        'cadastros.Porto',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='containers_destino',
        verbose_name='Porto de Destino',
    )
    data_coleta_prevista  = models.DateField('Previsão de Coleta', blank=True, null=True)
    data_coleta_realizada = models.DateField('Coleta Realizada', blank=True, null=True)
    hora_coleta_realizada = models.TimeField('Hora Coleta Realizada', null=True, blank=True)
    armador = models.ForeignKey(
        'cadastros.Armador', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Armador', related_name='containers',
    )
    transportadora = models.ForeignKey(
        'cadastros.Transportadora', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Transportadora', related_name='containers',
    )
    motorista = models.ForeignKey(
        'cadastros.Motorista', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='Motorista', related_name='containers',
    )
    placa_principal = models.CharField('Placa Principal', max_length=15, blank=True)
    placa_reboque   = models.CharField('Placa(s) Reboque', max_length=100, blank=True)
    numero_genset   = models.CharField('Nº Genset', max_length=30, blank=True)
    tara_container  = models.IntegerField('Tara do Container (kg)', null=True, blank=True)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Contêiner de Booking'
        verbose_name_plural = 'Contêineres de Booking'
        ordering = ['-booking__data_embarque_previsto', 'numero_container']
        constraints = [
            models.UniqueConstraint(fields=['booking', 'numero_container'], name='unique_container_por_booking'),
        ]
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'{self.numero_container} ({self.status})'


class BookingContainerHistory(ExportacaoBaseModel):
    container = models.ForeignKey(
        BookingContainer,
        on_delete=models.CASCADE,
        related_name='historico',
        verbose_name='Contêiner',
    )
    data = models.DateTimeField('Data', default=timezone.now)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='historico_booking_containers',
        verbose_name='Usuário',
    )
    status_from = models.CharField('Status anterior', max_length=50, blank=True)
    status_to = models.CharField('Status novo', max_length=50)
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Histórico de Contêiner'
        verbose_name_plural = 'Histórico de Contêineres'
        ordering = ['-data']
        indexes = [models.Index(fields=['empresa', 'data'])]

    def __str__(self):
        return f'{self.container.numero_container} {self.status_from or ""} → {self.status_to}'


class OrdemColeta(ExportacaoBaseModel):
    STATUS = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANDAMENTO', 'Em andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='ordens_coleta',
        verbose_name='Booking',
    )
    container = models.ForeignKey(
        BookingContainer,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordens_coleta',
        verbose_name='Contêiner',
    )
    numero = models.CharField('Número da Ordem de Coleta', max_length=30, blank=True, null=True, db_index=True)
    endereco_coleta = models.CharField('Endereço de Coleta', max_length=250, blank=True)
    responsavel_coleta = models.CharField('Responsável pela Coleta', max_length=150, blank=True)
    data_prevista = models.DateField('Data Prevista', blank=True, null=True)
    data_realizada = models.DateField('Data Realizada', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='PENDENTE')
    documento = models.FileField('Assinatura / Documento de Coleta', upload_to='exportacao/ordens_coleta/', blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True)
    segregado = models.BooleanField('Contêiner Segregado', default=False)
    lacre_armador = models.CharField('Lacre do Armador', max_length=50, blank=True)
    lacre_fiscal = models.CharField('Lacre Fiscal', max_length=50, blank=True)
    lacre_terminal = models.CharField('Lacre do Terminal', max_length=50, blank=True)
    transportadora = models.ForeignKey(
        'cadastros.Transportadora',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordens_coleta',
        verbose_name='Transportadora',
    )
    motorista = models.ForeignKey(
        'cadastros.Motorista',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='ordens_coleta',
        verbose_name='Motorista',
    )

    class Meta:
        verbose_name = 'Ordem de Coleta'
        verbose_name_plural = 'Ordens de Coleta'
        ordering = ['-data_prevista', '-criado_em']
        indexes = [models.Index(fields=['empresa', 'status'])]

    def __str__(self):
        return f'Ordem {self.numero or self.pk} - {self.get_status_display()}'

    @classmethod
    def generate_numero(cls, empresa):
        from django.utils import timezone
        year = timezone.now().year
        prefix = 'OC-'
        suffix = f'/{year}'
        last = cls.objects.filter(
            empresa=empresa,
            numero__startswith=prefix,
            numero__endswith=suffix,
        ).order_by('-numero').first()
        seq = 1
        if last and last.numero:
            try:
                seq = int(last.numero[len(prefix):-len(suffix)]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f'{prefix}{seq:04d}{suffix}'


class FotoOrdemColeta(models.Model):
    TIPO_CHOICES = [
        ('CONTAINER_VAZIO',  'Container Vazio'),
        ('NUMERO_CONTAINER', 'Número do Container'),
        ('GENSET',           'Genset'),
        ('OUTROS',           'Outros'),
    ]
    ordem = models.ForeignKey(
        OrdemColeta, on_delete=models.CASCADE,
        related_name='fotos', verbose_name='Ordem de Coleta',
    )
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='OUTROS')
    foto = models.ImageField('Foto', upload_to='exportacao/ordens_coleta/fotos/%Y/%m/')
    observacao = models.CharField('Observação', max_length=200, blank=True)
    enviada_por = models.ForeignKey(
        'cadastros.Motorista', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fotos_coleta',
        verbose_name='Enviada por',
    )
    data_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Foto da Coleta'
        verbose_name_plural = 'Fotos da Coleta'
        ordering = ['tipo', 'data_envio']

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.ordem}'
