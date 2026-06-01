from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


TIPO_CONTA_CHOICES = [
    ('CORRENTE', 'Conta Corrente'),
    ('POUPANCA', 'Poupança'),
    ('GARANTIDA', 'Conta Garantida / Especial'),
]

TIPO_PIX_CHOICES = [
    ('CPF', 'CPF'),
    ('CNPJ', 'CNPJ'),
    ('EMAIL', 'E-mail'),
    ('TELEFONE', 'Telefone'),
    ('CHAVE_ALEATORIA', 'Chave Aleatória'),
]


class ContaBancaria(models.Model):
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='contas_bancarias_empresa',
        verbose_name='Empresa',
    )
    banco = models.CharField('Banco', max_length=100)
    codigo_banco = models.CharField('Código do Banco', max_length=4, blank=True,
                                    help_text='Ex: 001 (BB), 237 (Bradesco), 341 (Itaú)')
    agencia = models.CharField('Agência', max_length=10)
    agencia_digito = models.CharField('Dígito da Agência', max_length=2, blank=True)
    conta = models.CharField('Conta', max_length=20)
    conta_digito = models.CharField('Dígito da Conta', max_length=2, blank=True)
    tipo_conta = models.CharField('Tipo de Conta', max_length=20,
                                  choices=TIPO_CONTA_CHOICES, default='CORRENTE')
    pix_habilitado = models.BooleanField('PIX Habilitado', default=False)
    tipo_chave_pix = models.CharField('Tipo de Chave PIX', max_length=20,
                                      choices=TIPO_PIX_CHOICES, blank=True)
    chave_pix = models.CharField('Chave PIX', max_length=100, blank=True)
    saldo_inicial = models.DecimalField(
        'Saldo Inicial', max_digits=15, decimal_places=2, default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('-999999999.99'))],
        help_text='Saldo da conta na data de início do controle no sistema',
    )
    data_saldo_inicial = models.DateField('Data do Saldo Inicial', null=True, blank=True)
    ativa = models.BooleanField('Ativa', default=True)
    conta_principal = models.BooleanField(
        'Conta Principal', default=False,
        help_text='Apenas uma conta pode ser marcada como principal por empresa',
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        ordering = ['-conta_principal', 'banco']
        unique_together = [('empresa', 'banco', 'agencia', 'conta')]
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
        ]

    def __str__(self):
        digito = f'-{self.conta_digito}' if self.conta_digito else ''
        return f'{self.banco} — Ag: {self.agencia} / Cc: {self.conta}{digito}'

    def save(self, *args, **kwargs):
        if self.conta_principal:
            ContaBancaria.objects.filter(
                empresa=self.empresa, conta_principal=True,
            ).exclude(pk=self.pk).update(conta_principal=False)
        super().save(*args, **kwargs)

    @property
    def numero_formatado(self):
        ag = f'{self.agencia}-{self.agencia_digito}' if self.agencia_digito else self.agencia
        cc = f'{self.conta}-{self.conta_digito}' if self.conta_digito else self.conta
        return f'Ag {ag} / Cc {cc}'


class ImportacaoExtrato(models.Model):
    TIPO_ARQUIVO = [
        ('OFX', 'OFX (Open Financial Exchange)'),
        ('CNAB240', 'CNAB 240 (Retorno Bancário)'),
        ('CNAB150', 'CNAB 150'),
    ]
    STATUS = [
        ('PENDENTE', 'Pendente'),
        ('PROCESSANDO', 'Processando'),
        ('CONCLUIDA', 'Concluída'),
        ('ERRO', 'Erro no Processamento'),
    ]

    conta_bancaria = models.ForeignKey(
        ContaBancaria,
        on_delete=models.CASCADE,
        related_name='importacoes',
        verbose_name='Conta Bancária',
    )
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='importacoes_extrato',
        verbose_name='Empresa',
    )
    tipo_arquivo = models.CharField('Tipo de Arquivo', max_length=10, choices=TIPO_ARQUIVO)
    arquivo = models.FileField('Arquivo', upload_to='extratos_bancarios/%Y/%m/')
    data_inicio_extrato = models.DateField('Início do Extrato', null=True, blank=True)
    data_fim_extrato = models.DateField('Fim do Extrato', null=True, blank=True)
    total_lancamentos = models.IntegerField('Total de Lançamentos', default=0)
    total_debitos = models.DecimalField('Total Débitos', max_digits=15, decimal_places=2,
                                        default=Decimal('0.00'))
    total_creditos = models.DecimalField('Total Créditos', max_digits=15, decimal_places=2,
                                         default=Decimal('0.00'))
    status = models.CharField('Status', max_length=15, choices=STATUS, default='PENDENTE')
    erro_mensagem = models.TextField('Mensagem de Erro', blank=True)
    importado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='importacoes_extrato',
        verbose_name='Importado por',
    )
    importado_em = models.DateTimeField('Importado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Importação de Extrato'
        verbose_name_plural = 'Importações de Extrato'
        ordering = ['-importado_em']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['conta_bancaria', 'importado_em']),
        ]

    def __str__(self):
        return f'{self.get_tipo_arquivo_display()} — {self.conta_bancaria.banco} — {self.importado_em:%d/%m/%Y}'

    @property
    def saldo_extrato(self):
        return self.total_creditos - self.total_debitos

    @property
    def percentual_conciliado(self):
        total = self.lancamentos.count()
        if not total:
            return 0
        conciliados = self.lancamentos.filter(status_conciliacao='CONCILIADO').count()
        return round(conciliados / total * 100)


class ExtratoLancamento(models.Model):
    TIPO = [
        ('DEBITO', 'Débito'),
        ('CREDITO', 'Crédito'),
    ]
    STATUS_CONCILIACAO = [
        ('PENDENTE', 'Pendente'),
        ('CONCILIADO', 'Conciliado'),
        ('IGNORADO', 'Ignorado'),
    ]

    importacao = models.ForeignKey(
        ImportacaoExtrato,
        on_delete=models.CASCADE,
        related_name='lancamentos',
        verbose_name='Importação',
    )
    conta_bancaria = models.ForeignKey(
        ContaBancaria,
        on_delete=models.CASCADE,
        related_name='lancamentos',
        verbose_name='Conta Bancária',
    )
    data_lancamento = models.DateField('Data do Lançamento')
    data_compensacao = models.DateField('Data de Compensação', null=True, blank=True)
    tipo = models.CharField('Tipo', max_length=7, choices=TIPO)
    valor = models.DecimalField(
        'Valor', max_digits=15, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Sempre positivo — o tipo (DEBITO/CREDITO) indica a direção',
    )
    descricao = models.CharField('Descrição', max_length=500)
    numero_documento = models.CharField('Número do Documento', max_length=50, blank=True)
    fit_id = models.CharField('FIT ID (OFX)', max_length=80, blank=True,
                               help_text='Identificador único do lançamento no arquivo OFX')
    status_conciliacao = models.CharField(
        'Status de Conciliação', max_length=12,
        choices=STATUS_CONCILIACAO, default='PENDENTE',
    )
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Lançamento de Extrato'
        verbose_name_plural = 'Lançamentos de Extrato'
        ordering = ['-data_lancamento', 'tipo']
        indexes = [
            models.Index(fields=['conta_bancaria', 'status_conciliacao']),
            models.Index(fields=['fit_id']),
            models.Index(fields=['data_lancamento']),
            models.Index(fields=['conta_bancaria', 'data_lancamento']),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} R$ {self.valor} — {self.data_lancamento:%d/%m/%Y} — {self.descricao[:50]}'

    @property
    def valor_sinalizado(self):
        return -self.valor if self.tipo == 'DEBITO' else self.valor

    @property
    def badge_status(self):
        mapa = {'PENDENTE': 'warning', 'CONCILIADO': 'success', 'IGNORADO': 'secondary'}
        return mapa.get(self.status_conciliacao, 'light')

    @property
    def badge_tipo(self):
        return 'danger' if self.tipo == 'DEBITO' else 'success'


class ConciliacaoLancamento(models.Model):
    TIPO_OPERACAO = [
        ('CONTA_PAGAR', 'Conta a Pagar'),
        ('CONTA_RECEBER', 'Conta a Receber'),
        ('LANCAMENTO_MANUAL', 'Lançamento Manual'),
    ]

    lancamento_extrato = models.OneToOneField(
        ExtratoLancamento,
        on_delete=models.CASCADE,
        related_name='conciliacao',
        verbose_name='Lançamento do Extrato',
    )
    tipo_operacao = models.CharField('Tipo de Operação', max_length=20, choices=TIPO_OPERACAO)
    pagamento_conta_pagar = models.ForeignKey(
        'financeiro.PagamentoContaPagar',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conciliacoes',
        verbose_name='Pagamento (CP)',
    )
    recebimento_conta_receber = models.ForeignKey(
        'financeiro.RecebimentoContaReceber',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conciliacoes',
        verbose_name='Recebimento (CR)',
    )
    descricao_manual = models.CharField('Descrição Manual', max_length=300, blank=True)
    score_matching = models.IntegerField('Score de Matching', default=0,
                                         help_text='0-100: qualidade do match automático')
    conciliado_manualmente = models.BooleanField(
        'Conciliado Manualmente', default=False,
        help_text='True = usuário selecionou manualmente; False = aceite de sugestão automática',
    )
    conciliado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='conciliacoes_realizadas',
        verbose_name='Conciliado por',
    )
    conciliado_em = models.DateTimeField('Conciliado em', null=True, blank=True)

    class Meta:
        verbose_name = 'Conciliação de Lançamento'
        verbose_name_plural = 'Conciliações de Lançamentos'

    def __str__(self):
        return f'Conciliação: {self.lancamento_extrato} → {self.get_tipo_operacao_display()}'

    @property
    def operacao_descricao(self):
        if self.tipo_operacao == 'CONTA_PAGAR' and self.pagamento_conta_pagar:
            cp = self.pagamento_conta_pagar
            return f'CP {cp.conta_pagar.numero} — {cp.conta_pagar.fornecedor}'
        if self.tipo_operacao == 'CONTA_RECEBER' and self.recebimento_conta_receber:
            cr = self.recebimento_conta_receber
            return f'CR {cr.conta_receber.numero} — {cr.conta_receber.cliente}'
        return self.descricao_manual or '—'
