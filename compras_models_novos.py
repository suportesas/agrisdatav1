# NOVOS MODELOS A ADICIONAR EM compras/models.py

"""
Modelos para:
1. Tipos de Divergência (CRUD)
2. Registros de Divergência por Recebimento
3. Avaliação de Fornecedor após compra concluída
"""

class TipoDivergencia(models.Model):
    """
    Tipos de divergência que podem ocorrer no recebimento
    Permite configuração flexível pelo usuário
    """
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='tipos_divergencia',
        verbose_name='Empresa'
    )
    
    codigo = models.CharField(
        'Código',
        max_length=20,
        unique=True,
        help_text='Código único para identificação (e.g., DANO_EXT, LACRE_ROMPIDO)'
    )
    
    nome = models.CharField(
        'Nome do Tipo de Divergência',
        max_length=100,
        help_text='Ex: Danos Externos, Lacre Rompido, Sujeira, Vencido'
    )
    
    descricao = models.TextField(
        'Descrição',
        blank=True,
        help_text='Detalhe o que caracteriza este tipo de divergência'
    )
    
    # Severidade para priorizar tratamento
    SEVERIDADE_CHOICES = [
        ('LEVE', 'Leve'),
        ('MEDIO', 'Médio'),
        ('GRAVE', 'Grave'),
    ]
    
    severidade = models.CharField(
        'Nível de Severidade',
        max_length=10,
        choices=SEVERIDADE_CHOICES,
        default='MEDIO',
        help_text='Define a prioridade de resolução'
    )
    
    # Controle
    ativo = models.BooleanField(
        'Ativo',
        default=True,
        help_text='Desative para ocultar em seleções futuras'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Tipo de Divergência'
        verbose_name_plural = 'Tipos de Divergência'
        ordering = ['empresa', 'severidade', 'nome']
        unique_together = ['empresa', 'codigo']
    
    def __str__(self):
        return f"[{self.severidade}] {self.nome}"


class DivergenciaRecebimento(models.Model):
    """
    Registro individual de cada divergência encontrada em um recebimento
    Permite múltiplas divergências por recebimento com detalhes
    """
    
    recebimento = models.ForeignKey(
        'RecebimentoCompra',
        on_delete=models.CASCADE,
        related_name='divergencias_detalhes',
        verbose_name='Recebimento'
    )
    
    tipo_divergencia = models.ForeignKey(
        'TipoDivergencia',
        on_delete=models.PROTECT,
        verbose_name='Tipo de Divergência'
    )
    
    item_recebimento = models.ForeignKey(
        'ItemRecebimento',
        on_delete=models.CASCADE,
        related_name='divergencias',
        verbose_name='Item Recebimento',
        blank=True,
        null=True,
        help_text='Deixe em branco se a divergência é geral do recebimento'
    )
    
    # Detalhes da divergência
    quantidade_afetada = models.DecimalField(
        'Quantidade Afetada',
        max_digits=12,
        decimal_places=4,
        blank=True,
        null=True,
        help_text='Quantidade de itens com problemas'
    )
    
    descricao_detalhes = models.TextField(
        'Descrição Detalhada',
        help_text='Descreva precisamente o problema encontrado'
    )
    
    # Ações propostas
    acao_proposta = models.TextField(
        'Ação Proposta',
        blank=True,
        help_text='Ex: Devolução total, devolução parcial, ajuste de preço, etc'
    )
    
    # Fotos/evidências (para integração futura com armazenamento)
    foto_1 = models.ImageField(
        'Foto 1',
        upload_to='compras/divergencias/%Y/%m/',
        blank=True,
        null=True
    )
    
    foto_2 = models.ImageField(
        'Foto 2',
        upload_to='compras/divergencias/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Status da divergência
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente Resolução'),
        ('EM_ANALISE', 'Em Análise'),
        ('RESOLVIDO', 'Resolvido'),
        ('NEGAR', 'Divergência Negada'),
    ]
    
    status_divergencia = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )
    
    # Resolução
    data_resolucao = models.DateTimeField(
        'Data de Resolução',
        blank=True,
        null=True
    )
    
    descricao_resolucao = models.TextField(
        'Como foi Resolvido',
        blank=True,
        help_text='Detalhe como a divergência foi solucionada'
    )
    
    # Auditoria
    registrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='divergencias_registradas',
        verbose_name='Registrado por'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Divergência de Recebimento'
        verbose_name_plural = 'Divergências de Recebimento'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.recebimento.numero} - {self.tipo_divergencia.nome}"


class AvaliacaoFornecedor(models.Model):
    """
    Avaliação de fornecedor após conclusão da compra
    Permite rastreabilidade de desempenho do fornecedor
    """
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='avaliacoes_fornecedor',
        verbose_name='Empresa'
    )
    
    recebimento = models.OneToOneField(
        'RecebimentoCompra',
        on_delete=models.CASCADE,
        related_name='avaliacao_fornecedor',
        verbose_name='Recebimento'
    )
    
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='avaliacoes',
        verbose_name='Fornecedor'
    )
    
    # Critérios de avaliação (1-5 estrelas)
    qualidade_produto = models.IntegerField(
        'Qualidade do Produto',
        choices=[(i, f"{i} Estrelas") for i in range(1, 6)],
        help_text='Avalie a qualidade do produto entregue'
    )
    
    prazo_entrega = models.IntegerField(
        'Cumprimento de Prazos',
        choices=[(i, f"{i} Estrelas") for i in range(1, 6)],
        help_text='Avalie o cumprimento do prazo acordado'
    )
    
    documentacao = models.IntegerField(
        'Documentação/NF-e',
        choices=[(i, f"{i} Estrelas") for i in range(1, 6)],
        help_text='Avalie a qualidade da documentação'
    )
    
    atendimento = models.IntegerField(
        'Qualidade do Atendimento',
        choices=[(i, f"{i} Estrelas") for i in range(1, 6)],
        help_text='Avalie como foi o atendimento do fornecedor'
    )
    
    preco = models.IntegerField(
        'Relação Preço/Qualidade',
        choices=[(i, f"{i} Estrelas") for i in range(1, 6)],
        help_text='Avalie a relação custo-benefício'
    )
    
    # Média geral (calculada)
    nota_media = models.DecimalField(
        'Nota Média',
        max_digits=3,
        decimal_places=2,
        editable=False,
        help_text='Calculada automaticamente (média das 5 categorias)'
    )
    
    # Comentários
    pontos_positivos = models.TextField(
        'Pontos Positivos',
        blank=True,
        help_text='Destaque o que foi bom na entrega'
    )
    
    pontos_negativos = models.TextField(
        'Pontos a Melhorar',
        blank=True,
        help_text='Indique o que pode ser melhorado'
    )
    
    recomendacao = models.TextField(
        'Recomendação para Compras Futuras',
        blank=True,
        help_text='Sua opinião sobre trabalhar novamente com este fornecedor'
    )
    
    # Controle
    recomenda = models.BooleanField(
        'Recomenda este Fornecedor?',
        default=True
    )
    
    # Auditoria
    avaliador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='avaliacoes_realizadas',
        verbose_name='Avaliador'
    )
    
    data_avaliacao = models.DateTimeField(
        'Data da Avaliação',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Avaliação de Fornecedor'
        verbose_name_plural = 'Avaliações de Fornecedor'
        ordering = ['-data_avaliacao']
        unique_together = ['recebimento']
    
    def save(self, *args, **kwargs):
        """Calcula nota média automaticamente"""
        self.nota_media = (
            self.qualidade_produto +
            self.prazo_entrega +
            self.documentacao +
            self.atendimento +
            self.preco
        ) / 5
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Avaliação {self.fornecedor.nome} - {self.recebimento.numero} ({self.nota_media})"
