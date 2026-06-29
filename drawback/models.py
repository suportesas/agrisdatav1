from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError


class AtoConcessorio(models.Model):
    TIPO_CHOICES = [
        ('SUSPENSAO', 'Suspensão'),
        ('ISENCAO', 'Isenção'),
        ('RESTITUICAO', 'Restituição'),
    ]
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('VENCIDO', 'Vencido'),
        ('ENCERRADO', 'Encerrado'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE,
        related_name='atos_concessorios', verbose_name='Empresa',
    )
    numero_ac = models.CharField('Número do AC', max_length=30,
                                 help_text='Ex: 23/0001234-0')
    tipo = models.CharField('Tipo', max_length=15, choices=TIPO_CHOICES, default='SUSPENSAO')
    data_inicio = models.DateField('Data de Início')
    data_vencimento = models.DateField('Data de Vencimento')
    data_prorrogacao = models.DateField('Data de Prorrogação', null=True, blank=True,
                                        help_text='Preencher apenas se o AC foi prorrogado')
    status = models.CharField('Status', max_length=15, choices=STATUS_CHOICES, default='ATIVO')
    despachante = models.CharField('Despachante Aduaneiro', max_length=150, blank=True)
    numero_processo_siscomex = models.CharField('Nº Processo Siscomex', max_length=50, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.PROTECT,
        related_name='atos_concessorios_criados', verbose_name='Criado por',
    )
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Ato Concessório'
        verbose_name_plural = 'Atos Concessórios'
        ordering = ['-data_inicio']
        unique_together = [('empresa', 'numero_ac')]
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['data_vencimento']),
        ]

    def __str__(self):
        return f'AC {self.numero_ac} ({self.get_tipo_display()}) — {self.get_status_display()}'

    @property
    def data_fim_efetiva(self):
        return self.data_prorrogacao or self.data_vencimento

    @property
    def dias_para_vencer(self):
        return (self.data_fim_efetiva - timezone.now().date()).days

    @property
    def esta_vencendo(self):
        return self.status == 'ATIVO' and 0 <= self.dias_para_vencer <= 30

    @property
    def nivel_alerta(self):
        if self.status != 'ATIVO':
            return None
        dias = self.dias_para_vencer
        if dias < 0:
            return 'vencido'
        if dias <= 5:
            return 'critico'
        if dias <= 15:
            return 'danger'
        if dias <= 30:
            return 'warning'
        return None


class DrawbackProdutoAC(models.Model):
    TIPO_PRODUTO_CHOICES = [
        ('EXPORTACAO',      'Exportação (produto final)'),
        ('IMPORTACAO',      'Importação (insumo importado)'),
        ('MERCADO_INTERNO', 'Mercado Interno (insumo nacional)'),
    ]

    ato_concessorio = models.ForeignKey(
        AtoConcessorio, on_delete=models.CASCADE,
        related_name='produtos', verbose_name='Ato Concessório',
    )
    produto = models.ForeignKey(
        'produtos.Produto', on_delete=models.PROTECT,
        related_name='drawback_produtos', verbose_name='Produto',
    )
    tipo_produto = models.CharField(
        'Tipo', max_length=20,
        choices=TIPO_PRODUTO_CHOICES,
        default='MERCADO_INTERNO',
    )
    ncm = models.CharField('NCM', max_length=10, blank=True)
    descricao_mercadoria = models.CharField('Descrição conforme AC', max_length=200)
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida', on_delete=models.PROTECT,
        related_name='drawback_produtos', verbose_name='Unidade de Medida',
    )
    quantidade_autorizada = models.DecimalField(
        'Quantidade Autorizada', max_digits=15, decimal_places=3,
        help_text='Total autorizado pelo MDIC para este produto',
    )
    quantidade_minima_export = models.DecimalField(
        'Quantidade Mínima a Exportar', max_digits=15, decimal_places=3,
        null=True, blank=True,
        help_text='Apenas para itens de Exportação',
    )
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Produto do AC'
        verbose_name_plural = 'Produtos do AC'
        ordering = ['tipo_produto', 'produto__nome']
        unique_together = [('ato_concessorio', 'produto', 'tipo_produto')]

    def __str__(self):
        return f'{self.produto.nome} [{self.get_tipo_produto_display()}] — AC {self.ato_concessorio.numero_ac}'

    def save(self, *args, **kwargs):
        if not self.ncm and self.produto_id:
            ncm_produto = getattr(self.produto, 'ncm', None)
            if ncm_produto:
                self.ncm = str(ncm_produto)
        super().save(*args, **kwargs)

    # ── saldos calculados dinamicamente ──────────────────────────────────

    @property
    def quantidade_comprada(self):
        return self.entradas.filter(anulado=False).aggregate(
            total=Sum('quantidade')
        )['total'] or Decimal('0')

    @property
    def quantidade_exportada(self):
        return self.saidas.filter(anulado=False).aggregate(
            total=Sum('quantidade')
        )['total'] or Decimal('0')

    @property
    def saldo_compra(self):
        if self.tipo_produto == 'EXPORTACAO':
            return Decimal('0')
        return self.quantidade_autorizada - self.quantidade_comprada

    @property
    def saldo_exportacao(self):
        if self.tipo_produto == 'EXPORTACAO':
            return self.quantidade_autorizada - self.quantidade_exportada
        return Decimal('0')

    @property
    def percentual_cumprido(self):
        if self.tipo_produto == 'EXPORTACAO':
            if not self.quantidade_minima_export:
                return Decimal('0')
            return (self.quantidade_exportada / self.quantidade_minima_export * 100).quantize(Decimal('0.1'))
        # Para insumos: percentual de uso em relação ao autorizado
        if not self.quantidade_autorizada:
            return Decimal('0')
        return (self.quantidade_comprada / self.quantidade_autorizada * 100).quantize(Decimal('0.1'))


class EntradaDrawback(models.Model):
    TIPO_COMPRA_CHOICES = [
        ('IMPORTACAO', 'Importação'),
        ('MERCADO_INTERNO', 'Mercado Interno'),
    ]
    ORIGEM_CHOICES = [
        ('ERP', 'ERP (vinculado ao recebimento)'),
        ('MANUAL', 'Manual (lançamento retroativo)'),
    ]

    ato_concessorio = models.ForeignKey(
        AtoConcessorio, on_delete=models.PROTECT,
        related_name='entradas', verbose_name='Ato Concessório',
    )
    drawback_produto = models.ForeignKey(
        DrawbackProdutoAC, on_delete=models.PROTECT,
        related_name='entradas', verbose_name='Produto do AC',
    )
    # Vínculo ERP (opcional — null para lançamentos manuais)
    item_recebimento = models.OneToOneField(
        'compras.ItemRecebimento', on_delete=models.PROTECT,
        related_name='drawback_entrada', verbose_name='Item do Recebimento',
        null=True, blank=True,
    )
    # Campos para lançamento manual
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor', on_delete=models.PROTECT,
        related_name='drawback_entradas', verbose_name='Fornecedor',
        null=True, blank=True,
    )
    numero_nf = models.CharField('Número da NF', max_length=20)
    serie_nf = models.CharField('Série', max_length=5, blank=True, default='1')
    data_nf = models.DateField('Data da NF')
    data_recebimento = models.DateField('Data do Recebimento')
    quantidade = models.DecimalField('Quantidade', max_digits=15, decimal_places=3)
    valor_unitario = models.DecimalField(
        'Valor Unitário (R$)', max_digits=15, decimal_places=4,
        null=True, blank=True,
    )
    tipo_compra = models.CharField(
        'Tipo de Compra', max_length=20,
        choices=TIPO_COMPRA_CHOICES, default='MERCADO_INTERNO',
    )
    origem = models.CharField('Origem', max_length=10, choices=ORIGEM_CHOICES, default='MANUAL')
    retroativo = models.BooleanField(
        'Lançamento Retroativo', default=False,
        help_text='Marcado para lançamentos de regularização de períodos anteriores',
    )
    anulado = models.BooleanField('Anulado', default=False)
    motivo_anulacao = models.TextField('Motivo da Anulação', blank=True)
    observacoes = models.TextField('Observações', blank=True)
    registrado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.PROTECT,
        related_name='drawback_entradas_registradas', verbose_name='Registrado por',
    )
    data_registro = models.DateTimeField('Data do Registro', auto_now_add=True)

    class Meta:
        verbose_name = 'Entrada Drawback'
        verbose_name_plural = 'Entradas Drawback'
        ordering = ['data_recebimento', 'numero_nf']
        indexes = [
            models.Index(fields=['ato_concessorio', 'anulado']),
            models.Index(fields=['drawback_produto', 'anulado']),
            models.Index(fields=['data_recebimento']),
        ]

    def __str__(self):
        return (f'Entrada {self.numero_nf} — {self.drawback_produto.produto.nome} '
                f'{self.quantidade} ({self.data_recebimento:%d/%m/%Y})')

    def clean(self):
        if self.origem == 'ERP' and not self.item_recebimento_id:
            raise ValidationError('Para origem ERP, o item do recebimento é obrigatório.')
        if self.origem == 'MANUAL' and not self.fornecedor_id:
            raise ValidationError('Para lançamento manual, o fornecedor é obrigatório.')
        if self.anulado and not self.motivo_anulacao:
            raise ValidationError('Informe o motivo da anulação.')
        if self.drawback_produto_id and self.ato_concessorio_id:
            if self.drawback_produto.ato_concessorio_id != self.ato_concessorio_id:
                raise ValidationError('O produto não pertence a este Ato Concessório.')
        if self.data_recebimento and self.ato_concessorio_id:
            ac = self.ato_concessorio
            if self.data_recebimento > ac.data_fim_efetiva:
                raise ValidationError(
                    f'Data de recebimento ({self.data_recebimento:%d/%m/%Y}) '
                    f'fora da vigência do AC (até {ac.data_fim_efetiva:%d/%m/%Y}).'
                )

    @property
    def valor_total(self):
        if self.valor_unitario:
            return self.valor_unitario * self.quantidade
        return None


class SaidaDrawback(models.Model):
    ORIGEM_CHOICES = [
        ('ERP', 'ERP (vinculado à NF-e)'),
        ('MANUAL', 'Manual (lançamento retroativo)'),
    ]

    ato_concessorio = models.ForeignKey(
        AtoConcessorio, on_delete=models.PROTECT,
        related_name='saidas', verbose_name='Ato Concessório',
    )
    drawback_produto = models.ForeignKey(
        DrawbackProdutoAC, on_delete=models.PROTECT,
        related_name='saidas', verbose_name='Produto do AC',
    )
    # Vínculo ERP (opcional)
    item_nfe = models.OneToOneField(
        'faturamento.ItemNotaFiscal', on_delete=models.PROTECT,
        related_name='drawback_saida', verbose_name='Item da NF-e',
        null=True, blank=True,
    )
    # Campos para lançamento manual / retroativo
    cliente = models.ForeignKey(
        'cadastros.Cliente', on_delete=models.PROTECT,
        related_name='drawback_saidas', verbose_name='Cliente',
        null=True, blank=True,
    )
    numero_nfe = models.CharField('Número da NF-e / Invoice', max_length=20, blank=True)
    numero_re = models.CharField('RE (Registro de Exportação)', max_length=30, blank=True,
                                 help_text='Número do RE no Siscomex')
    numero_due = models.CharField('DUE (Declaração Única de Exportação)', max_length=30, blank=True)
    data_embarque = models.DateField('Data de Embarque')
    quantidade = models.DecimalField('Quantidade', max_digits=15, decimal_places=3)
    valor_fob_usd = models.DecimalField(
        'Valor FOB (USD)', max_digits=15, decimal_places=2,
        null=True, blank=True,
    )
    origem = models.CharField('Origem', max_length=10, choices=ORIGEM_CHOICES, default='MANUAL')
    retroativo = models.BooleanField('Lançamento Retroativo', default=False)
    anulado = models.BooleanField('Anulado', default=False)
    motivo_anulacao = models.TextField('Motivo da Anulação', blank=True)
    observacoes = models.TextField('Observações', blank=True)
    registrado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.PROTECT,
        related_name='drawback_saidas_registradas', verbose_name='Registrado por',
    )
    data_registro = models.DateTimeField('Data do Registro', auto_now_add=True)

    class Meta:
        verbose_name = 'Saída Drawback'
        verbose_name_plural = 'Saídas Drawback'
        ordering = ['data_embarque', 'numero_nfe']
        indexes = [
            models.Index(fields=['ato_concessorio', 'anulado']),
            models.Index(fields=['drawback_produto', 'anulado']),
            models.Index(fields=['data_embarque']),
        ]

    def __str__(self):
        ref = self.numero_nfe or self.numero_re or self.numero_due or '—'
        return (f'Saída {ref} — {self.drawback_produto.produto.nome} '
                f'{self.quantidade} ({self.data_embarque:%d/%m/%Y})')

    def clean(self):
        if self.anulado and not self.motivo_anulacao:
            raise ValidationError('Informe o motivo da anulação.')
        if self.drawback_produto_id and self.ato_concessorio_id:
            if self.drawback_produto.ato_concessorio_id != self.ato_concessorio_id:
                raise ValidationError('O produto não pertence a este Ato Concessório.')
        if self.data_embarque and self.ato_concessorio_id:
            ac = self.ato_concessorio
            if self.data_embarque > ac.data_fim_efetiva:
                raise ValidationError(
                    f'Data de embarque ({self.data_embarque:%d/%m/%Y}) '
                    f'fora da vigência do AC (até {ac.data_fim_efetiva:%d/%m/%Y}).'
                )
