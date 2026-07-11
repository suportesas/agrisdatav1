"""
Módulo Vendas — Pré-venda / Pedido de Venda
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.core.validators import MinValueValidator


class PedidoVenda(models.Model):
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('APROVADO', 'Aprovado'),
        ('CONFIRMADO', 'Confirmado'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    TIPO_VENDA_CHOICES = [
        ('MERCADO_INTERNO', 'Mercado Interno'),
        ('EXPORTACAO', 'Exportação'),
    ]
    MOEDA_CHOICES = [
        ('BRL', 'Real (BRL)'),
        ('USD', 'Dólar (USD)'),
        ('EUR', 'Euro (EUR)'),
        ('GBP', 'Libra (GBP)'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='pedidos_venda', verbose_name='Empresa',
    )
    numero = models.CharField('Número', max_length=20, unique=True)
    cliente = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='pedidos_venda', verbose_name='Cliente',
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_venda_como_vendedor',
        verbose_name='Vendedor',
    )
    data_pedido = models.DateField('Data do Pedido', default=timezone.now)
    data_entrega_prevista = models.DateField('Entrega Prevista', null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='RASCUNHO')
    tipo_venda = models.CharField('Tipo de Venda', max_length=20, choices=TIPO_VENDA_CHOICES, default='MERCADO_INTERNO')
    natureza_operacao = models.CharField('Natureza da Operação', max_length=100, blank=True)
    condicao_pagamento = models.CharField('Condição de Pagamento', max_length=100, blank=True)
    forma_pagamento = models.CharField('Forma de Pagamento', max_length=100, blank=True)
    moeda = models.CharField('Moeda', max_length=3, choices=MOEDA_CHOICES, default='BRL')
    taxa_cambio = models.DecimalField(
        'Taxa de Câmbio', max_digits=10, decimal_places=4,
        null=True, blank=True,
        help_text='Câmbio para BRL. Obrigatório para moeda estrangeira.',
    )
    valor_produtos = models.DecimalField(
        'Valor dos Produtos', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )
    valor_desconto = models.DecimalField(
        'Desconto', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )
    valor_frete = models.DecimalField(
        'Frete', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )
    valor_total = models.DecimalField(
        'Total', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )
    observacoes = models.TextField('Observações', blank=True)
    observacoes_fiscais = models.TextField(
        'Informações Complementares (NF-e)', blank=True,
        help_text='Texto que será incluído nas observações da NF-e gerada.',
    )
    gerar_nota_fiscal = models.BooleanField(
        'Gerar Nota Fiscal', default=True,
        help_text='Ao emitir, cria automaticamente NF-e (MI) ou Invoice (EXP).',
    )
    nota_fiscal = models.ForeignKey(
        'faturamento.NotaFiscal', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_venda',
        verbose_name='NF-e Gerada',
    )
    invoice = models.ForeignKey(
        'faturamento.InvoiceExportacao', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_venda',
        verbose_name='Invoice Gerada',
    )
    gerar_conta_receber = models.BooleanField(
        'Gerar Conta a Receber', default=True,
        help_text='Ao emitir, cria automaticamente um Conta a Receber no Financeiro.',
    )
    conta_receber = models.ForeignKey(
        'financeiro.ContaReceber', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_venda',
        verbose_name='Conta a Receber Gerada',
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_venda_criados',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Pedido de Venda'
        verbose_name_plural = 'Pedidos de Venda'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['cliente', 'status']),
        ]

    def __str__(self):
        return f"{self.numero} — {self.cliente.razao_social}"

    def calcular_total(self):
        total_itens = sum(item.preco_total for item in self.itens.all())
        self.valor_produtos = total_itens
        self.valor_total = total_itens + self.valor_frete - self.valor_desconto
        return self.valor_total

    @classmethod
    def _gerar_numero(cls, empresa):
        from django.utils import timezone as tz
        ano = tz.now().year
        prefixo = f"PV-{ano}-"
        ultimo = (
            cls.objects
            .filter(empresa=empresa, numero__startswith=prefixo)
            .order_by('numero')
            .last()
        )
        seq = int(ultimo.numero.split('-')[-1]) + 1 if ultimo else 1
        return f"{prefixo}{seq:04d}"


class TabelaPreco(models.Model):
    """Preço negociado por cliente/produto/porto de destino, com vigência.

    Serve de fonte de verdade para pré-preencher `preco_unitario` em
    ItemPedidoVenda/ItemInvoice em vez de digitação manual item a item.
    `cliente` nulo = tabela padrão, aplicável a qualquer cliente.
    """
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='tabelas_preco', verbose_name='Empresa',
    )
    cliente = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        null=True, blank=True, related_name='tabelas_preco',
        verbose_name='Cliente', help_text='Deixe em branco para uma tabela padrão (qualquer cliente).',
    )
    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT,
        related_name='tabelas_preco', verbose_name='Produto',
    )
    porto_destino = models.ForeignKey(
        'cadastros.Porto', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tabelas_preco',
        verbose_name='Porto de Destino',
    )
    moeda = models.CharField('Moeda', max_length=3, choices=PedidoVenda.MOEDA_CHOICES, default='BRL')
    preco_unitario = models.DecimalField(
        'Preço Unitário', max_digits=14, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    vigencia_inicio = models.DateField('Vigência — Início', default=timezone.now)
    vigencia_fim = models.DateField('Vigência — Fim', null=True, blank=True, help_text='Deixe em branco para vigência em aberto.')
    ativo = models.BooleanField('Ativo', default=True)
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='tabelas_preco_criadas',
        verbose_name='Criado por',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Tabela de Preço'
        verbose_name_plural = 'Tabelas de Preço'
        ordering = ['-vigencia_inicio']
        indexes = [
            models.Index(fields=['empresa', 'cliente', 'produto', 'vigencia_inicio']),
            models.Index(fields=['empresa', 'ativo']),
        ]

    def __str__(self):
        cliente_str = self.cliente.razao_social if self.cliente_id else 'Padrão (qualquer cliente)'
        return f'{self.produto} — {cliente_str} — {self.moeda} {self.preco_unitario}'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.vigencia_fim and self.vigencia_fim < self.vigencia_inicio:
            raise ValidationError({'vigencia_fim': 'A data de fim da vigência não pode ser anterior ao início.'})

        qs = TabelaPreco.objects.filter(
            empresa=self.empresa,
            cliente=self.cliente,
            produto=self.produto,
            porto_destino=self.porto_destino,
            moeda=self.moeda,
            ativo=True,
        ).exclude(pk=self.pk)
        fim = self.vigencia_fim or timezone.datetime.max.date()
        for outra in qs:
            outra_fim = outra.vigencia_fim or timezone.datetime.max.date()
            if self.vigencia_inicio <= outra_fim and outra.vigencia_inicio <= fim:
                raise ValidationError(
                    'Já existe uma tabela de preço ativa com vigência sobreposta para '
                    'este cliente/produto/porto/moeda.'
                )


class ItemPedidoVenda(models.Model):
    pedido = models.ForeignKey(
        PedidoVenda, on_delete=models.CASCADE,
        related_name='itens', verbose_name='Pedido',
    )
    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='itens_pedido_venda',
        verbose_name='Produto',
    )
    descricao = models.CharField('Descrição', max_length=200)
    ncm = models.CharField('NCM', max_length=10, blank=True)
    cfop = models.CharField('CFOP', max_length=10, blank=True)
    unidade = models.CharField('Unidade', max_length=10, default='UN')
    quantidade = models.DecimalField(
        'Quantidade', max_digits=15, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    preco_unitario = models.DecimalField(
        'Preço Unitário', max_digits=15, decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    preco_total = models.DecimalField(
        'Total', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )
    desconto_item = models.DecimalField(
        'Desconto Item', max_digits=15, decimal_places=2, default=Decimal('0.00'),
    )

    class Meta:
        verbose_name = 'Item do Pedido de Venda'
        verbose_name_plural = 'Itens do Pedido de Venda'
        ordering = ['pk']

    def __str__(self):
        return f"{self.pedido.numero} — {self.descricao}"

    def save(self, *args, **kwargs):
        self.preco_total = (self.quantidade * self.preco_unitario) - self.desconto_item
        super().save(*args, **kwargs)
