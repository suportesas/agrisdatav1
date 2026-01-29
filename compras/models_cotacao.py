# models_cotacao.py - Sistema de Cotações Inteligentes
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class CotacaoInteligente(models.Model):
    """Cotação de compra inteligente - agrupa múltiplos produtos com busca automática de fornecedores"""
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('enviada', 'Enviada aos Fornecedores'),
        ('em_analise', 'Em Análise'),
        ('aprovada', 'Aprovada'),
        ('cancelada', 'Cancelada'),
    ]
    
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='cotacoes_inteligentes')
    numero = models.CharField(max_length=20, verbose_name='Número da Cotação')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_validade = models.DateField(verbose_name='Válida até')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='rascunho')
    
    # Dados adicionais
    observacoes = models.TextField(blank=True, verbose_name='Observações Gerais')
    condicoes_pagamento = models.TextField(blank=True, verbose_name='Condições de Pagamento')
    prazo_entrega_desejado = models.IntegerField(
        blank=True, 
        null=True, 
        verbose_name='Prazo de Entrega Desejado (dias)',
        help_text='Prazo máximo desejado para entrega'
    )
    
    # Rastreamento
    criado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, related_name='cotacoes_criadas')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'compras_cotacao_inteligente'
        verbose_name = 'Cotação Inteligente'
        verbose_name_plural = 'Cotações Inteligentes'
        ordering = ['-data_criacao']
        unique_together = ['empresa', 'numero']
    
    def __str__(self):
        return f"Cotação {self.numero} - {self.get_status_display()}"
    
    @property
    def total_itens(self):
        """Total de itens na cotação"""
        return self.itens.count()
    
    @property
    def total_fornecedores(self):
        """Total de fornecedores envolvidos"""
        return self.propostas.values('fornecedor').distinct().count()
    
    @property
    def possui_propostas(self):
        """Verifica se há propostas registradas"""
        return self.propostas.exists()
    
    @property
    def total_propostas_selecionadas(self):
        """Total de propostas já selecionadas"""
        return self.propostas.filter(selecionada=True).count()
    
    @property
    def todas_propostas_selecionadas(self):
        """Verifica se todos os itens têm propostas selecionadas"""
        return self.total_itens > 0 and self.total_propostas_selecionadas == self.total_itens
    
    @property
    def status_calculado(self):
        """Calcula o status real baseado no estado da cotação"""
        if self.status == 'cancelada':
            return self.status
        
        if self.todas_propostas_selecionadas:
            return 'aprovada'
        elif self.possui_propostas:
            return 'em_analise'
        elif self.total_fornecedores > 0:
            return 'enviada'
        else:
            return 'rascunho'


class CotacaoInteligenteItem(models.Model):
    """Item de produto na cotação inteligente"""
    cotacao = models.ForeignKey(CotacaoInteligente, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.CASCADE)
    quantidade = models.DecimalField(
        max_digits=15, 
        decimal_places=3, 
        validators=[MinValueValidator(Decimal('0.001'))],
        verbose_name='Quantidade'
    )
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT)
    especificacao = models.TextField(blank=True, verbose_name='Especificações Adicionais')
    
    # Preço de referência (último preço pago ou média)
    preco_referencia = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        blank=True, 
        null=True,
        verbose_name='Preço de Referência'
    )
    
    class Meta:
        db_table = 'compras_cotacao_inteligente_item'
        verbose_name = 'Item da Cotação Inteligente'
        verbose_name_plural = 'Itens da Cotação Inteligente'
        unique_together = ['cotacao', 'produto']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade} {self.unidade_medida.sigla}"
    
    @property
    def fornecedores_cadastrados(self):
        """Retorna fornecedores cadastrados para este produto"""
        return self.produto.fornecedores_relacionados.filter(ativo=True)


class CotacaoInteligenteFornecedor(models.Model):
    """Relaciona fornecedores à cotação inteligente"""
    cotacao = models.ForeignKey(CotacaoInteligente, on_delete=models.CASCADE, related_name='cotacao_fornecedores')
    fornecedor = models.ForeignKey('cadastros.Fornecedor', on_delete=models.CASCADE)
    
    # Dados de envio
    enviado_em = models.DateTimeField(blank=True, null=True)
    enviado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    email_enviado = models.BooleanField(default=False)
    
    # Resposta
    respondido_em = models.DateTimeField(blank=True, null=True)
    observacoes_fornecedor = models.TextField(blank=True)
    
    class Meta:
        db_table = 'compras_cotacao_inteligente_fornecedor'
        verbose_name = 'Fornecedor na Cotação Inteligente'
        verbose_name_plural = 'Fornecedores na Cotação Inteligente'
        unique_together = ['cotacao', 'fornecedor']
    
    def __str__(self):
        return f"{self.fornecedor.nome} - Cotação {self.cotacao.numero}"


class CotacaoInteligenteProposta(models.Model):
    """Proposta de preço de um fornecedor para um item da cotação inteligente"""
    cotacao = models.ForeignKey(CotacaoInteligente, on_delete=models.CASCADE, related_name='propostas')
    item = models.ForeignKey(CotacaoInteligenteItem, on_delete=models.CASCADE, related_name='propostas')
    fornecedor = models.ForeignKey('cadastros.Fornecedor', on_delete=models.CASCADE)
    
    # Dados da proposta
    preco_unitario = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Preço Unitário'
    )
    prazo_entrega = models.IntegerField(verbose_name='Prazo de Entrega (dias)')
    quantidade_minima = models.DecimalField(
        max_digits=15, 
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name='Quantidade Mínima'
    )
    
    # Condições comerciais
    condicao_pagamento = models.CharField(max_length=200, blank=True, verbose_name='Condição de Pagamento')
    frete = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Valor do Frete')
    impostos = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Impostos')
    
    # Observações e anexos
    observacoes = models.TextField(blank=True)
    arquivo_proposta = models.FileField(upload_to='cotacoes/propostas/', blank=True, null=True)
    
    # Status
    selecionada = models.BooleanField(default=False, verbose_name='Proposta Selecionada')
    motivo_selecao = models.TextField(blank=True, verbose_name='Motivo da Seleção')
    
    # Rastreamento
    cadastrado_em = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'compras_cotacao_inteligente_proposta'
        verbose_name = 'Proposta de Cotação Inteligente'
        verbose_name_plural = 'Propostas de Cotação Inteligente'
        ordering = ['item', 'preco_unitario']
        unique_together = ['cotacao', 'item', 'fornecedor']
    
    def __str__(self):
        return f"{self.fornecedor.nome} - {self.item.produto.nome} - R$ {self.preco_unitario}"
    
    @property
    def preco_total(self):
        """Calcula o preço total (unitário * quantidade + frete)"""
        return (self.preco_unitario * self.item.quantidade) + self.frete + self.impostos
    
    @property
    def melhor_preco(self):
        """Verifica se é o melhor preço para este item"""
        propostas_item = CotacaoInteligenteProposta.objects.filter(
            cotacao=self.cotacao,
            item=self.item
        ).order_by('preco_unitario')
        
        if propostas_item.exists():
            return propostas_item.first().id == self.id
        return False


class HistoricoPrecoFornecedor(models.Model):
    """Histórico de preços praticados por fornecedores"""
    produto = models.ForeignKey('produtos.Produto', on_delete=models.CASCADE, related_name='historico_precos')
    fornecedor = models.ForeignKey('cadastros.Fornecedor', on_delete=models.CASCADE)
    
    # Dados do preço
    preco_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    quantidade = models.DecimalField(max_digits=15, decimal_places=3)
    data_cotacao = models.DateField()
    
    # Origem
    cotacao = models.ForeignKey(CotacaoInteligente, on_delete=models.SET_NULL, null=True, blank=True)
    documento_referencia = models.CharField(max_length=100, blank=True, help_text='NF, Pedido, etc')
    
    # Condições
    prazo_entrega = models.IntegerField(blank=True, null=True)
    condicao_pagamento = models.CharField(max_length=200, blank=True)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'compras_historico_preco_fornecedor'
        verbose_name = 'Histórico de Preço'
        verbose_name_plural = 'Histórico de Preços'
        ordering = ['-data_cotacao']
        indexes = [
            models.Index(fields=['produto', 'fornecedor', '-data_cotacao']),
        ]
    
    def __str__(self):
        return f"{self.produto.nome} - {self.fornecedor.nome} - R$ {self.preco_unitario} ({self.data_cotacao})"
