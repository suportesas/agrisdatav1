"""
Módulo Financeiro - Contas a Pagar
Gestão completa de pagamentos, parcelas, juros e multas
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


# ============================================
# 0. FORMA DE PAGAMENTO
# ============================================

class FormaPagemento(models.Model):
    """Formas de pagamento disponíveis (Boleto, PIX, Transferência, etc)"""
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='formas_pagamento',
        verbose_name='Empresa'
    )

    nome = models.CharField(
        'Nome da Forma de Pagamento',
        max_length=100,
        unique=True,
        help_text='Ex: Boleto, PIX, Transferência Bancária, Dinheiro, Cheque'
    )
    
    descricao = models.TextField(
        'Descrição',
        blank=True,
        help_text='Instruções ou observações sobre esta forma de pagamento'
    )
    
    ativo = models.BooleanField(
        'Ativo',
        default=True,
        help_text='Se marcado, esta forma será disponível nas parcelas'
    )
    
    dias_processamento = models.IntegerField(
        'Dias de Processamento',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Dias úteis que leva para o pagamento ser processado'
    )
    
    taxa_administrativa = models.DecimalField(
        'Taxa Administrativa (%)',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Percentual de taxa cobrada sobre o valor (ex: 1.5% para boleto)'
    )
    
    ordem_exibicao = models.IntegerField(
        'Ordem de Exibição',
        default=0,
        help_text='Ordem em que aparece na lista de formas de pagamento'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Forma de Pagamento'
        verbose_name_plural = 'Formas de Pagamento'
        ordering = ['ordem_exibicao', 'nome']
    
    def __str__(self):
        return self.nome


# ============================================
# 1. CONFIGURAÇÃO DE JUROS E MULTA (Empresa)
# ============================================

class ConfiguracaoJurosMulta(models.Model):
    """Configuração de taxa de juros e multa por empresa"""
    
    TIPO_MULTA_CHOICES = [
        ('PERCENTUAL', 'Percentual (%)'),
        ('FIXO', 'Valor Fixo (R$)'),
    ]
    
    empresa = models.OneToOneField(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='configuracao_juros_multa',
        verbose_name='Empresa'
    )
    
    taxa_juros_mensal = models.DecimalField(
        'Taxa de Juros Mensal (%)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='Taxa mensal de juros sobre valores em atraso'
    )
    
    multa_atraso = models.DecimalField(
        'Multa por Atraso',
        max_digits=8,
        decimal_places=2,
        default=Decimal('50.00'),
        help_text='Multa por atraso (valor percentual ou fixo)'
    )
    
    tipo_multa = models.CharField(
        'Tipo de Multa',
        max_length=20,
        choices=TIPO_MULTA_CHOICES,
        default='PERCENTUAL'
    )
    
    dias_tolerancia = models.IntegerField(
        'Dias de Tolerância',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Dias sem cobrança de juros/multa após vencimento'
    )
    
    ativo = models.BooleanField(
        'Ativo',
        default=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Configuração de Juros e Multa'
        verbose_name_plural = 'Configurações de Juros e Multa'
    
    def __str__(self):
        return f"Config {self.empresa.nome}"


# ============================================
# 2. CONTA A PAGAR (Principal)
# ============================================

class ContaPagar(models.Model):
    """Conta a pagar - gerada automaticamente de recebimentos ou manualmente"""
    
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('APROVADA', 'Aprovada'),
        ('PAGA', 'Paga'),
        ('CANCELADA', 'Cancelada'),
        ('RENEGOCIADA', 'Renegociada'),
    ]
    
    # Referências
    recebimento = models.OneToOneField(
        'compras.RecebimentoCompra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conta_pagar',
        verbose_name='Recebimento de Compra'
    )
    
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='contas_pagar',
        verbose_name='Fornecedor'
    )
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='contas_pagar',
        verbose_name='Empresa'
    )
    
    # Identificação
    numero = models.CharField(
        'Número',
        max_length=50,
        unique=True,
        help_text='Número da conta (gerado automaticamente ou manual)'
    )
    
    # Valores
    valor_total = models.DecimalField(
        'Valor Total',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    valor_ajustado = models.DecimalField(
        'Valor Ajustado',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        default=Decimal('0.00'),
        help_text='Valor após descontos/acréscimos'
    )
    
    desconto_negociado = models.DecimalField(
        'Desconto Negociado',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    juros_acumulados = models.DecimalField(
        'Juros Acumulados',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        editable=False
    )
    
    multa_acumulada = models.DecimalField(
        'Multa Acumulada',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        editable=False
    )
    
    # Status e Aprovação
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='ABERTA'
    )
    
    requer_aprovacao = models.BooleanField(
        'Requer Aprovação',
        default=False,
        help_text='Se True, aguarda aprovação antes de permitir pagamento'
    )
    
    aprovado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contas_aprovadas',
        verbose_name='Aprovado por'
    )
    
    data_aprovacao = models.DateTimeField(
        'Data de Aprovação',
        null=True,
        blank=True
    )
    
    # Datas
    data_emissao = models.DateField(
        'Data de Emissão',
        default=timezone.now
    )
    
    # Auditoria
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contas_criadas',
        verbose_name='Criado por'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Conta a Pagar'
        verbose_name_plural = 'Contas a Pagar'
        ordering = ['-data_emissao', '-numero']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['fornecedor', 'status']),
            models.Index(fields=['numero']),
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.fornecedor.nome}"
    
    def calcular_valor_ajustado(self):
        """Recalcula o valor ajustado"""
        self.valor_ajustado = self.valor_total - self.desconto_negociado
        return self.valor_ajustado
    
    def aprovar(self, usuario):
        """Aprova conta se requer_aprovacao=True"""
        if self.status != 'ABERTA':
            raise ValidationError('Apenas contas ABERTA podem ser aprovadas')
        self.status = 'APROVADA'
        self.aprovado_por = usuario
        self.data_aprovacao = timezone.now()
        self.save()
    
    def pode_pagar(self):
        """Verifica se pode ser paga"""
        if self.status == 'PAGA':
            return False, 'Conta já foi paga'
        if self.status == 'CANCELADA':
            return False, 'Conta foi cancelada'
        if self.requer_aprovacao and self.status == 'ABERTA':
            return False, 'Conta aguarda aprovação'
        return True, 'OK'


# ============================================
# 3. PARCELA DA CONTA A PAGAR
# ============================================

class ParcelaContaPagar(models.Model):
    """Parcelas da conta a pagar"""
    
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('PAGA', 'Paga'),
        ('VENCIDA', 'Vencida'),
        ('RENEGOCIADA', 'Renegociada'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    conta_pagar = models.ForeignKey(
        ContaPagar,
        on_delete=models.CASCADE,
        related_name='parcelas',
        verbose_name='Conta a Pagar'
    )
    
    numero_parcela = models.IntegerField(
        'Número da Parcela',
        validators=[MinValueValidator(1)]
    )
    
    forma_pagamento = models.ForeignKey(
        FormaPagemento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parcelas',
        verbose_name='Forma de Pagamento',
        help_text='Boleto, PIX, Transferência, etc'
    )
    
    valor_parcela = models.DecimalField(
        'Valor da Parcela',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    data_vencimento = models.DateField(
        'Data de Vencimento'
    )
    
    data_pagamento = models.DateField(
        'Data de Pagamento',
        null=True,
        blank=True
    )
    
    dias_atraso = models.IntegerField(
        'Dias em Atraso',
        default=0,
        editable=False
    )
    
    juros_parcela = models.DecimalField(
        'Juros da Parcela',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        editable=False
    )
    
    multa_parcela = models.DecimalField(
        'Multa da Parcela',
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        editable=False
    )
    
    valor_total_parcela = models.DecimalField(
        'Valor Total (Parcela + Juros + Multa)',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        editable=False
    )
    
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='ABERTA'
    )
    
    observacao = models.TextField(
        'Observação',
        blank=True
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Parcela de Conta a Pagar'
        verbose_name_plural = 'Parcelas de Contas a Pagar'
        ordering = ['conta_pagar', 'numero_parcela']
        unique_together = ['conta_pagar', 'numero_parcela']
    
    def __str__(self):
        return f"{self.conta_pagar.numero} - Parcela {self.numero_parcela}"
    
    def calcular_dias_atraso(self):
        """Calcula dias em atraso"""
        if self.status == 'PAGA':
            return 0
        atraso = (timezone.now().date() - self.data_vencimento).days
        return max(0, atraso)
    
    def recalcular_total(self):
        """Recalcula valor total com juros e multa"""
        self.dias_atraso = self.calcular_dias_atraso()
        self.valor_total_parcela = self.valor_parcela + self.juros_parcela + self.multa_parcela
        return self.valor_total_parcela


# ============================================
# 4. PAGAMENTO DE CONTA A PAGAR
# ============================================

class PagamentoContaPagar(models.Model):
    """Registro de pagamentos realizados"""
    
    FORMA_PAGAMENTO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('BOLETO', 'Boleto'),
        ('TED', 'Transferência Eletrônica'),
        ('CARTAO', 'Cartão de Crédito'),
        ('CHEQUE', 'Cheque'),
        ('PIX', 'Pix'),
        ('OUTRO', 'Outro'),
    ]
    
    STATUS_PAGAMENTO_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PROCESSANDO', 'Processando'),
        ('COMPENSADO', 'Compensado'),
        ('FALHA', 'Falha'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    parcela = models.ForeignKey(
        ParcelaContaPagar,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        verbose_name='Parcela'
    )
    
    conta_pagar = models.ForeignKey(
        ContaPagar,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        verbose_name='Conta a Pagar'
    )
    
    valor_pago = models.DecimalField(
        'Valor Pago',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    forma_pagamento = models.CharField(
        'Forma de Pagamento',
        max_length=20,
        choices=FORMA_PAGAMENTO_CHOICES
    )
    
    numero_documento = models.CharField(
        'Número do Documento',
        max_length=50,
        blank=True,
        help_text='Número do cheque, boleto, etc'
    )
    
    banco = models.CharField(
        'Banco',
        max_length=100,
        blank=True
    )
    
    data_pagamento = models.DateField(
        'Data do Pagamento'
    )
    
    data_compensacao = models.DateField(
        'Data de Compensação',
        null=True,
        blank=True
    )
    
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_PAGAMENTO_CHOICES,
        default='PENDENTE'
    )
    
    comprovante = models.FileField(
        'Comprovante de Pagamento',
        upload_to='comprovantes_pagamento/%Y/%m/',
        null=True,
        blank=True,
        help_text='Upload do comprovante (PDF, imagem, etc)'
    )
    
    observacao = models.TextField(
        'Observação',
        blank=True
    )
    
    pago_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos_realizados',
        verbose_name='Registrado por'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Pagamento de Conta a Pagar'
        verbose_name_plural = 'Pagamentos de Contas a Pagar'
        ordering = ['-data_pagamento', '-data_criacao']
        indexes = [
            models.Index(fields=['parcela', 'status']),
            models.Index(fields=['data_pagamento']),
        ]
    
    def __str__(self):
        return f"Pagamento {self.pk} - {self.forma_pagamento} - {self.valor_pago}"


# ============================================
# 5. AJUSTE DA CONTA A PAGAR
# ============================================

class AjusteContaPagar(models.Model):
    """Ajustes (descontos, juros, multas, renegociações)"""
    
    TIPO_AJUSTE_CHOICES = [
        ('DESCONTO_DIVERGENCIA', 'Desconto por Divergência'),
        ('ACRESCIMO_JUROS', 'Acréscimo de Juros'),
        ('ACRESCIMO_MULTA', 'Acréscimo de Multa'),
        ('RENEGOCIACAO', 'Renegociação'),
        ('DESCONTO_NEGOCIADO', 'Desconto Negociado'),
        ('OUTRO', 'Outro'),
    ]
    
    conta_pagar = models.ForeignKey(
        ContaPagar,
        on_delete=models.CASCADE,
        related_name='ajustes',
        verbose_name='Conta a Pagar'
    )
    
    tipo = models.CharField(
        'Tipo de Ajuste',
        max_length=50,
        choices=TIPO_AJUSTE_CHOICES
    )
    
    valor_ajuste = models.DecimalField(
        'Valor do Ajuste',
        max_digits=15,
        decimal_places=2,
        help_text='Positivo = acréscimo, Negativo = desconto'
    )
    
    motivo = models.CharField(
        'Motivo',
        max_length=200
    )
    
    divergencia = models.ForeignKey(
        'compras.DivergenciaRecebimento',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ajustes_conta',
        verbose_name='Divergência Associada'
    )
    
    aprovado = models.BooleanField(
        'Aprovado',
        default=False
    )
    
    aprovado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ajustes_aprovados',
        verbose_name='Aprovado por'
    )
    
    observacao = models.TextField(
        'Observação',
        blank=True
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Ajuste de Conta a Pagar'
        verbose_name_plural = 'Ajustes de Contas a Pagar'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.conta_pagar.numero} - {self.get_tipo_display()}"
