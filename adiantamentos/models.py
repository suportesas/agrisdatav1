from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum


class AdiantamentoInternacional(models.Model):
    MOEDA = [
        ('USD', 'USD - Dólar Americano'),
        ('EUR', 'EUR - Euro'),
        ('GBP', 'GBP - Libra Esterlina'),
        ('BRL', 'BRL - Real Brasileiro'),
    ]

    STATUS = [
        ('PENDENTE_EMBARQUE', 'Pendente de Embarque'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('PARCIALMENTE_QUITADO', 'Parcialmente Quitado'),
        ('QUITADO', 'Quitado'),
        ('MIGRADO', 'Migrado para Próxima Safra'),
        ('CANCELADO', 'Cancelado'),
    ]

    TIPO_REGRA = [
        ('VALOR_FIXO', 'Valor Fixo por Embarque'),
        ('PERCENTUAL', 'Percentual do Valor da Invoice'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='adiantamentos_internacionais',
        verbose_name='Empresa',
    )
    cliente = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.CASCADE,
        related_name='adiantamentos_internacionais',
        verbose_name='Cliente Internacional',
    )
    safra_referencia = models.CharField(
        'Safra (Referência)',
        max_length=20,
        help_text='Ex: 2025/2026',
    )
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adiantamentos_internacionais',
        verbose_name='Safra (Vínculo)',
    )
    numero_referencia = models.CharField('Nº de Referência / Contrato', max_length=30)
    data_adiantamento = models.DateField('Data do Adiantamento')
    invoice_origem = models.ForeignKey(
        'faturamento.InvoiceExportacao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adiantamentos_origem',
        verbose_name='Invoice de Exportação (Opcional)',
    )
    moeda = models.CharField('Moeda', max_length=3, choices=MOEDA, default='USD')
    valor_estrangeiro = models.DecimalField('Valor Estrangeiro', max_digits=15, decimal_places=2)
    taxa_cambio = models.DecimalField('Taxa de Câmbio Acordada (BRL)', max_digits=10, decimal_places=4, default=1)
    valor_brl = models.DecimalField('Valor Convertido (BRL)', max_digits=15, decimal_places=2, default=0)

    tipo_regra_desconto = models.CharField(
        'Tipo de Regra de Desconto',
        max_length=20,
        choices=TIPO_REGRA,
        default='VALOR_FIXO',
    )
    valor_desconto_padrao = models.DecimalField(
        'Valor de Desconto por Embarque',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor fixo em moeda estrangeira a descontar a cada embarque',
    )
    percentual_desconto = models.DecimalField(
        'Percentual de Desconto (%)',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Percentual do valor da invoice a descontar',
    )

    data_prevista_reembolso = models.DateField('Data Prevista para Reembolso (Embarque)', null=True, blank=True)
    status = models.CharField('Status', max_length=25, choices=STATUS, default='PENDENTE_EMBARQUE')
    observacoes = models.TextField('Observações', blank=True)

    adiantamento_origem = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='migracoes_destino',
        verbose_name='Originado da Migração',
    )

    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='adiantamentos_criados',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Adiantamento Internacional'
        verbose_name_plural = 'Adiantamentos Internacionais'
        ordering = ['-data_adiantamento']
        unique_together = [['empresa', 'numero_referencia']]

    def __str__(self):
        return f'{self.numero_referencia} — {self.cliente} ({self.safra_referencia})'

    def save(self, *args, **kwargs):
        self.valor_brl = self.valor_estrangeiro * self.taxa_cambio
        super().save(*args, **kwargs)

    @property
    def total_descontado(self):
        resultado = self.descontos.filter(status='APLICADO').aggregate(
            total=Sum('valor_desconto_estrangeiro')
        )['total']
        return resultado or Decimal('0.00')

    @property
    def saldo_estrangeiro(self):
        return self.valor_estrangeiro - self.total_descontado

    @property
    def percentual_quitado(self):
        if self.valor_estrangeiro:
            return (self.total_descontado / self.valor_estrangeiro) * 100
        return Decimal('0')

    @property
    def tem_saldo(self):
        return self.saldo_estrangeiro > 0

    def desconto_sugerido(self, valor_invoice=None):
        """Retorna o valor de desconto sugerido com base na regra configurada."""
        if self.tipo_regra_desconto == 'VALOR_FIXO' and self.valor_desconto_padrao:
            return min(self.valor_desconto_padrao, self.saldo_estrangeiro)
        if self.tipo_regra_desconto == 'PERCENTUAL' and self.percentual_desconto and valor_invoice:
            sugerido = (valor_invoice * self.percentual_desconto / 100).quantize(Decimal('0.01'))
            return min(sugerido, self.saldo_estrangeiro)
        return self.saldo_estrangeiro


class DescontoAdiantamento(models.Model):
    STATUS = [
        ('APLICADO', 'Aplicado'),
        ('PULADO', 'Pulado (próximo embarque)'),
        ('CANCELADO', 'Cancelado'),
    ]

    adiantamento = models.ForeignKey(
        AdiantamentoInternacional,
        on_delete=models.CASCADE,
        related_name='descontos',
        verbose_name='Adiantamento',
    )
    invoice = models.ForeignKey(
        'faturamento.InvoiceExportacao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='descontos_adiantamento',
        verbose_name='Invoice',
    )
    data_desconto = models.DateField('Data do Desconto')
    valor_desconto_estrangeiro = models.DecimalField(
        'Valor do Desconto (Moeda Estrangeira)',
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    taxa_cambio_aplicada = models.DecimalField('Taxa de Câmbio Aplicada', max_digits=10, decimal_places=4, default=1)
    valor_desconto_brl = models.DecimalField('Valor do Desconto (BRL)', max_digits=15, decimal_places=2, default=0)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='APLICADO')
    motivo_pulo = models.TextField('Motivo do Pulo', blank=True)
    observacoes = models.TextField('Observações', blank=True)
    aplicado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='descontos_aplicados',
        verbose_name='Aplicado por',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Desconto de Adiantamento'
        verbose_name_plural = 'Descontos de Adiantamento'
        ordering = ['-data_desconto']

    def __str__(self):
        return f'Desconto {self.adiantamento.numero_referencia} — {self.data_desconto} ({self.get_status_display()})'

    def save(self, *args, **kwargs):
        self.valor_desconto_brl = self.valor_desconto_estrangeiro * self.taxa_cambio_aplicada
        super().save(*args, **kwargs)


class MigracaoAdiantamento(models.Model):
    adiantamento_origem = models.ForeignKey(
        AdiantamentoInternacional,
        on_delete=models.CASCADE,
        related_name='migracoes_geradas',
        verbose_name='Adiantamento de Origem',
    )
    adiantamento_destino = models.OneToOneField(
        AdiantamentoInternacional,
        on_delete=models.CASCADE,
        related_name='migracao_origem',
        verbose_name='Adiantamento de Destino',
    )
    saldo_migrado_estrangeiro = models.DecimalField(
        'Saldo Migrado (Moeda Estrangeira)',
        max_digits=15,
        decimal_places=2,
    )
    data_migracao = models.DateField('Data da Migração')
    motivo = models.TextField('Motivo da Migração')
    migrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='migracoes_realizadas',
        verbose_name='Migrado por',
    )

    class Meta:
        verbose_name = 'Migração de Adiantamento'
        verbose_name_plural = 'Migrações de Adiantamento'
        ordering = ['-data_migracao']

    def __str__(self):
        return f'Migração {self.adiantamento_origem.numero_referencia} → {self.adiantamento_destino.numero_referencia}'
