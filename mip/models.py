from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class EstagioDesenvolvimento(models.Model):
    """
    Estágios do ciclo de vida de uma praga.
    Ex: Lagarta-do-cartucho tem: Ovo → Larva → Pupa → Adulto
    """

    TIPO_ESTAGIO_CHOICES = [
        ('OVO', 'Ovo'),
        ('NINFA', 'Ninfa'),
        ('LARVA', 'Larva'),
        ('PUPA', 'Pupa'),
        ('ADULTO', 'Adulto'),
        ('ESPORO', 'Esporo (Fungo)'),
        ('LESAO', 'Lesão (Doença)'),
        ('OUTRO', 'Outro'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='estagios_desenvolvimento',
        verbose_name='Empresa',
        null=True,
        blank=True,
        help_text='Deixar em branco para criar um template padrão'
    )

    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.CASCADE,
        related_name='estagios',
        verbose_name='Praga'
    )

    tipo_estagio = models.CharField(
        'Tipo de Estágio',
        max_length=20,
        choices=TIPO_ESTAGIO_CHOICES,
        help_text='Ex: Ovo, Larva, Adulto, etc'
    )

    descricao = models.CharField(
        'Descrição',
        max_length=200,
        blank=True,
        help_text='Ex: "Larva de 3º ínstar" ou "Ninfa 4 (pseudopupa)"'
    )

    duracao_minima_dias = models.IntegerField(
        'Duração Mínima (dias)',
        null=True,
        blank=True,
    )

    duracao_maxima_dias = models.IntegerField(
        'Duração Máxima (dias)',
        null=True,
        blank=True,
    )

    ordem_ciclo = models.IntegerField(
        'Ordem no Ciclo',
        default=1,
        help_text='1=Ovo, 2=Larva1, 3=Larva2, etc'
    )

    eh_fase_critica = models.BooleanField(
        'É Fase Crítica?',
        default=False,
        help_text='Marcar se é a fase mais sensível/danosa'
    )

    observacoes = models.TextField('Observações', blank=True)

    ativo = models.BooleanField('Ativo', default=True)

    eh_template = models.BooleanField(
        'É Estágio Template?',
        default=False,
        help_text='Marcar para estágios padrão copiados para novas empresas'
    )

    template_original = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='copias',
        verbose_name='Template Original',
    )

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_estagiodesenvolvimento'
        verbose_name = 'Estágio de Desenvolvimento'
        verbose_name_plural = 'Estágios de Desenvolvimento'
        ordering = ['praga', 'ordem_ciclo']
        indexes = [
            models.Index(fields=['empresa', 'praga']),
            models.Index(fields=['tipo_estagio']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'praga', 'tipo_estagio', 'ordem_ciclo'],
                name='unique_estagio_praga_empresa'
            )
        ]

    def __str__(self):
        return f"{self.praga.nome_comum} - {self.get_tipo_estagio_display()}"


class MonitoramentoMIP(models.Model):
    """
    Monitoramento MIP (Manejo Integrado de Pragas).
    Representa UMA VISITA ao talhão para avaliação de pragas.
    """

    TIPO_MONITORAMENTO_CHOICES = [
        ('REGULAR', 'Monitoramento Regular'),
        ('PREVENTIVO', 'Monitoramento Preventivo'),
        ('EMERGENCIAL', 'Monitoramento Emergencial'),
    ]

    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('COMPLETO', 'Monitoramento Completo'),
        ('ANALISADO', 'Analisado e Avaliado'),
        ('CANCELADO', 'Cancelado'),
    ]

    CONDICOES_TEMPO_CHOICES = [
        ('ENSOLARADO', 'Ensolarado'),
        ('PARCIALMENTE_NUBLADO', 'Parcialmente Nublado'),
        ('NUBLADO', 'Nublado'),
        ('CHUVA_LEVE', 'Chuva Leve'),
        ('CHUVA_MODERADA', 'Chuva Moderada'),
        ('CHUVA_FORTE', 'Chuva Forte'),
        ('GAROA', 'Garoa'),
        ('VENTO_FRACO', 'Vento Fraco'),
        ('VENTO_MODERADO', 'Vento Moderado'),
        ('VENTO_FORTE', 'Vento Forte'),
        ('NEBLINA', 'Neblina'),
        ('ORVALHO', 'Orvalho'),
        ('SECO', 'Seco'),
        ('UMIDO', 'Umido'),
        ('OUTRO', 'Outro'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='monitoramentos_mip',
        verbose_name='Empresa'
    )

    numero = models.CharField(
        'Número',
        max_length=20,
        unique=True,
        help_text='Auto-gerado: MIP-YYYY-NNNNN'
    )

    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='monitoramentos_mip',
        verbose_name='Talhão'
    )

    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='monitoramentos_mip',
        verbose_name='Safra',
    )

    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        related_name='monitoramentos_mip',
        verbose_name='Cultura',
        help_text='Auto-preenchida do talhão'
    )

    data_monitoramento = models.DateField('Data do Monitoramento')

    tipo_monitoramento = models.CharField(
        'Tipo de Monitoramento',
        max_length=20,
        choices=TIPO_MONITORAMENTO_CHOICES,
        default='REGULAR'
    )

    responsavel = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitoramentos_mip_realizados',
        verbose_name='Responsável (Pragueiro)'
    )

    quantidade_pontos = models.IntegerField(
        'Quantidade de Pontos',
        default=20,
        help_text='Padrão: 20 pontos por monitoramento'
    )

    condicoes_tempo = models.CharField(
        'Condições do Tempo',
        max_length=100,
        blank=True,
        choices=CONDICOES_TEMPO_CHOICES,
    )

    temperatura_media = models.DecimalField(
        'Temperatura Média (°C)',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )

    umidade_media = models.IntegerField(
        'Umidade Média (%)',
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    velocidade_vento_media = models.DecimalField(
        'Velocidade do Vento Média (km/h)',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    foto_area_geral = models.ImageField(
        'Foto da Área Geral',
        upload_to='monitoramento_mip/%Y/%m/',
        null=True,
        blank=True
    )

    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='RASCUNHO'
    )

    observacoes_gerais = models.TextField('Observações Gerais', blank=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitoramentos_mip_criados',
        verbose_name='Criado Por'
    )

    class Meta:
        db_table = 'cadastros_monitoramentomip'
        verbose_name = 'Monitoramento MIP'
        verbose_name_plural = 'Monitoramentos MIP'
        ordering = ['-data_monitoramento']
        indexes = [
            models.Index(fields=['empresa', 'data_monitoramento']),
            models.Index(fields=['talhao', 'data_monitoramento']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['talhao', 'data_monitoramento'],
                name='unique_monitoramento_talhao_data',
                condition=models.Q(status__in=['COMPLETO', 'ANALISADO'])
            )
        ]

    def __str__(self):
        return f"{self.numero} - {self.talhao.nome} ({self.data_monitoramento})"

    def save(self, *args, **kwargs):
        if not self.numero:
            from datetime import datetime
            from django.utils import timezone
            ano = timezone.now().year
            ultima = MonitoramentoMIP.objects.filter(
                numero__startswith=f'MIP-{ano}'
            ).order_by('numero').last()

            if ultima:
                numero_seq = int(ultima.numero.split('-')[-1]) + 1
            else:
                numero_seq = 1

            self.numero = f'MIP-{ano}-{numero_seq:05d}'

        if self.talhao and not self.cultura_id:
            self.cultura = self.talhao.cultura_atual

        super().save(*args, **kwargs)


class PragaNoMonitoramento(models.Model):
    """
    Liga Praga ao Monitoramento MIP.
    Um monitoramento pode ter N pragas; cada praga tem seus próprios dados.
    """

    RESULTADO_ACAO_CHOICES = [
        ('SEM_ACAO', 'Sem Ação Necessária'),
        ('MONITORAR', 'Continuar Monitorando'),
        ('RECOMENDA_DEFENSIVO', 'Recomenda Defensivo'),
    ]

    SEVERIDADE_CHOICES = [
        (1, 'Muito Baixa'),
        (2, 'Baixa'),
        (3, 'Média'),
        (4, 'Alta'),
        (5, 'Muito Alta'),
    ]

    monitoramento = models.ForeignKey(
        'mip.MonitoramentoMIP',
        on_delete=models.CASCADE,
        related_name='pragas_detectadas',
        verbose_name='Monitoramento MIP'
    )

    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.PROTECT,
        related_name='monitoramentos',
        verbose_name='Praga/Doença'
    )

    quantidade_pontos_com_praga = models.IntegerField(
        'Quantidade de Pontos com Praga',
        help_text='Quantos dos 20 pontos tinham esta praga'
    )

    incidencia_percentual = models.DecimalField(
        'Incidência (%)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        default=0,
    )

    estagio_principal = models.ForeignKey(
        'mip.EstagioDesenvolvimento',
        on_delete=models.PROTECT,
        related_name='praga_monitoramento_estagio_principal',
        verbose_name='Estágio Principal',
    )

    detalhes_estagios = models.JSONField(
        'Detalhes por Estágio',
        default=dict,
        blank=True,
    )

    severidade = models.IntegerField(
        'Severidade (1-5)',
        choices=SEVERIDADE_CHOICES,
        default=3,
    )

    quantidade_total_pragas = models.IntegerField(
        'Quantidade Total de Pragas Encontradas',
        null=True,
        blank=True,
    )

    ned_valor = models.DecimalField(
        'Nível Econômico de Dano (%)',
        max_digits=5,
        decimal_places=2,
        default=5.0,
    )

    ned_atingido = models.BooleanField('NED Atingido?')

    resultado_acao = models.CharField(
        'Resultado da Ação',
        max_length=20,
        choices=RESULTADO_ACAO_CHOICES,
        default='MONITORAR'
    )

    fotos = models.JSONField('Fotos da Praga', default=list, blank=True)

    observacoes = models.TextField('Observações', blank=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        db_table = 'cadastros_praganomonitoramento'
        verbose_name = 'Praga no Monitoramento'
        verbose_name_plural = 'Pragas no Monitoramento'
        ordering = ['monitoramento', 'resultado_acao', '-incidencia_percentual']
        indexes = [
            models.Index(fields=['monitoramento', 'ned_atingido']),
            models.Index(fields=['resultado_acao']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['monitoramento', 'praga'],
                name='unique_praga_por_monitoramento'
            )
        ]

    def __str__(self):
        return f"{self.monitoramento.numero} - {self.praga.nome_comum} ({self.incidencia_percentual}%)"

    def save(self, *args, **kwargs):
        if not self.incidencia_percentual:
            self.incidencia_percentual = (
                (self.quantidade_pontos_com_praga /
                 self.monitoramento.quantidade_pontos) * 100
            )

        if self.ned_valor is not None:
            self.ned_atingido = self.incidencia_percentual >= self.ned_valor

            if self.ned_atingido:
                self.resultado_acao = 'RECOMENDA_DEFENSIVO'
            elif self.incidencia_percentual > 0 and self.incidencia_percentual < self.ned_valor:
                self.resultado_acao = 'MONITORAR'
            else:
                self.resultado_acao = 'SEM_ACAO'

        super().save(*args, **kwargs)


class PontoMonitoramento(models.Model):
    """
    Detalhe de cada ponto no monitoramento de uma praga.
    """

    praga_monitoramento = models.ForeignKey(
        'mip.PragaNoMonitoramento',
        on_delete=models.CASCADE,
        related_name='pontos',
        verbose_name='Praga no Monitoramento'
    )

    numero_ponto = models.IntegerField(
        'Número do Ponto',
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text='Qual dos 20 pontos (1-20)'
    )

    latitude = models.DecimalField(
        'Latitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        'Longitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    praga_presente = models.BooleanField('Praga Presente?', default=False)

    quantidade = models.IntegerField(
        'Quantidade',
        default=0,
        validators=[MinValueValidator(0)],
    )

    estagio = models.ForeignKey(
        'mip.EstagioDesenvolvimento',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Estágio Encontrado'
    )

    severidade = models.IntegerField(
        'Severidade Neste Ponto',
        choices=[
            (0, 'Nenhuma'),
            (1, 'Muito Leve'),
            (2, 'Leve'),
            (3, 'Média'),
            (4, 'Severa'),
            (5, 'Muito Severa'),
        ],
        default=0
    )

    foto = models.ImageField(
        'Foto do Ponto',
        upload_to='monitoramento_pontos/%Y/%m/',
        null=True,
        blank=True
    )

    observacoes = models.TextField('Observações', blank=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_pontomonitoramento'
        verbose_name = 'Ponto de Monitoramento'
        verbose_name_plural = 'Pontos de Monitoramento'
        ordering = ['praga_monitoramento', 'numero_ponto']
        indexes = [
            models.Index(fields=['praga_monitoramento', 'numero_ponto']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['praga_monitoramento', 'numero_ponto'],
                name='unique_ponto_por_praga_monitoramento'
            )
        ]

    def __str__(self):
        return f"Ponto {self.numero_ponto} - {self.praga_monitoramento}"
