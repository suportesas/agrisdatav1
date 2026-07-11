"""
Módulo de Estoque - Models
Sistema de gestão de armazéns, locais de estocagem e lotes
"""
from django.db import models
from django.db import transaction
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


# ============================================
# MANAGERS CUSTOMIZADOS PARA MULTI-TENANCY
# ============================================

class EmpresaQuerySet(models.QuerySet):
    """QuerySet customizado para filtrar por empresa (Multi-tenant)"""
    
    def da_empresa(self, empresa):
        """Filtra registros da empresa especificada"""
        if empresa:
            return self.filter(empresa=empresa)
        return self.none()
    
    def ativos(self):
        """Retorna apenas registros ativos"""
        return self.filter(ativo=True)


class ArmazemManager(models.Manager):
    """Manager customizado para Armazem"""
    
    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db)
    
    def da_empresa(self, empresa):
        return self.get_queryset().da_empresa(empresa)
    
    def ativos(self):
        return self.get_queryset().ativos()


# ============================================
# MODELS
# ============================================

class Armazem(models.Model):
    """
    Armazém/Depósito para armazenamento de produtos
    RF-080: Cadastro de armazéns e depósitos
    """
    
    TIPO_CHOICES = [
        ('ALMOXARIFADO', 'Almoxarifado'),
        ('DEPOSITO', 'Depósito'),
        ('CAMARA_FRIA', 'Câmara Fria'),
        ('SILO', 'Silo'),
        ('PACKING', 'Packing House'),
        ('CAMPO', 'Campo'),
        ('OUTRO', 'Outro'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='armazens',
        verbose_name='Empresa'
    )
    
    # Identificação
    codigo = models.CharField(
        'Código',
        max_length=20,
        help_text='Código único do armazém'
    )
    
    nome = models.CharField(
        'Nome',
        max_length=100,
        help_text='Nome do armazém'
    )
    
    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=TIPO_CHOICES,
        default='DEPOSITO'
    )
    
    # Localização
    localizacao = models.CharField(
        'Localização',
        max_length=200,
        blank=True,
        help_text='Endereço ou local físico'
    )
    
    fazenda = models.ForeignKey(
        'cadastros.Fazenda',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armazens',
        verbose_name='Fazenda'
    )
    
    # Responsável
    responsavel = models.ForeignKey(
        'rh.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armazens_responsavel',
        verbose_name='Responsável'
    )
    
    # Dimensões (para cálculo automático)
    comprimento = models.DecimalField(
        'Comprimento (m)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Comprimento em metros'
    )
    
    largura = models.DecimalField(
        'Largura (m)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Largura em metros'
    )
    
    altura = models.DecimalField(
        'Altura (m)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Altura/Pé-direito em metros'
    )
    
    densidade_media = models.DecimalField(
        'Densidade Média (kg/m³)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Densidade média dos produtos armazenados (para cálculo kg)'
    )
    
    # Capacidade (calculada ou manual)
    capacidade_m3 = models.DecimalField(
        'Capacidade (m³)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Capacidade em metros cúbicos (calculada automaticamente ou manual)'
    )
    
    capacidade_kg = models.DecimalField(
        'Capacidade (kg)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Capacidade em quilogramas (calculada automaticamente ou manual)'
    )
    
    # Controle de temperatura
    controla_temperatura = models.BooleanField(
        'Controla Temperatura',
        default=False,
        help_text='Armazém com controle de temperatura'
    )
    
    temperatura_min = models.DecimalField(
        'Temperatura Mínima (°C)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Temperatura mínima permitida'
    )
    
    temperatura_max = models.DecimalField(
        'Temperatura Máxima (°C)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Temperatura máxima permitida'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Status
    ativo = models.BooleanField(
        'Ativo',
        default=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armazens_cadastrados',
        verbose_name='Cadastrado por'
    )
    
    objects = ArmazemManager()
    
    class Meta:
        verbose_name = 'Armazém'
        verbose_name_plural = 'Armazéns'
        ordering = ['empresa', 'codigo', 'nome']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['tipo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                name='unique_armazem_codigo_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    def save(self, *args, **kwargs):
        """Calcula capacidade automaticamente se dimensões foram informadas"""
        # Calcula m³ se tiver todas as dimensões
        if self.comprimento and self.largura and self.altura:
            volume = self.comprimento * self.largura * self.altura
            # Se capacidade_m3 não foi informada manualmente, calcula
            if not self.capacidade_m3:
                self.capacidade_m3 = volume
        
        # Calcula kg se tiver m³ e densidade
        if self.capacidade_m3 and self.densidade_media:
            peso = self.capacidade_m3 * self.densidade_media
            # Se capacidade_kg não foi informada manualmente, calcula
            if not self.capacidade_kg:
                self.capacidade_kg = peso
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validações customizadas"""
        errors = {}
        
        # Valida temperaturas
        if self.controla_temperatura:
            if not self.temperatura_min or not self.temperatura_max:
                errors['controla_temperatura'] = 'Defina temperaturas mínima e máxima para controle'
            elif self.temperatura_min >= self.temperatura_max:
                errors['temperatura_max'] = 'Temperatura máxima deve ser maior que a mínima'
        
        if errors:
            raise ValidationError(errors)
    
    def get_ocupacao_kg(self):
        """Retorna ocupação em kg baseado nos lotes"""
        total = self.lotes.filter(
            status__in=['DISPONIVEL', 'BLOQUEADO']
        ).aggregate(
            total=models.Sum('quantidade_atual')
        )['total'] or Decimal('0')
        return total
    
    def get_percentual_ocupacao(self):
        """Retorna percentual de ocupação"""
        if not self.capacidade_kg:
            return None
        ocupacao = self.get_ocupacao_kg()
        return (ocupacao / self.capacidade_kg) * 100


class LocalEstocagem(models.Model):
    """
    Local específico dentro do armazém (prateleira, pallet, sala, etc)
    RF-081: Controle de locais de estocagem com endereçamento
    """
    
    TIPO_CHOICES = [
        ('PRATELEIRA', 'Prateleira'),
        ('PALLET', 'Pallet'),
        ('SALA', 'Sala'),
        ('CAMARA', 'Câmara'),
        ('SILO', 'Silo'),
        ('BOX', 'Box'),
        ('GAVETA', 'Gaveta'),
        ('OUTRO', 'Outro'),
    ]
    
    # Relacionamento
    armazem = models.ForeignKey(
        Armazem,
        on_delete=models.CASCADE,
        related_name='locais',
        verbose_name='Armazém'
    )
    
    # Identificação
    codigo = models.CharField(
        'Código do Local',
        max_length=30,
        help_text='Ex: A01-P02-N03 (Ala-Prateleira-Nível)'
    )
    
    descricao = models.CharField(
        'Descrição',
        max_length=200,
        blank=True
    )
    
    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=TIPO_CHOICES,
        default='PRATELEIRA'
    )
    
    # Capacidade
    capacidade_kg = models.DecimalField(
        'Capacidade (kg)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Capacidade máxima em kg'
    )
    
    # Bloqueio
    bloqueado = models.BooleanField(
        'Bloqueado',
        default=False,
        help_text='Local bloqueado para uso'
    )
    
    motivo_bloqueio = models.TextField(
        'Motivo do Bloqueio',
        blank=True
    )
    
    data_bloqueio = models.DateTimeField(
        'Data do Bloqueio',
        null=True,
        blank=True
    )
    
    bloqueado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='locais_bloqueados',
        verbose_name='Bloqueado por'
    )
    
    # Status
    ativo = models.BooleanField(
        'Ativo',
        default=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Local de Estocagem'
        verbose_name_plural = 'Locais de Estocagem'
        ordering = ['armazem', 'codigo']
        indexes = [
            models.Index(fields=['armazem', 'ativo']),
            models.Index(fields=['bloqueado']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['armazem', 'codigo'],
                name='unique_local_codigo_armazem'
            )
        ]
    
    def __str__(self):
        # Concatenate Armazém (codigo or nome) and Descrição for easier identification
        armazem_nome = self.armazem.nome if hasattr(self.armazem, 'nome') else self.armazem.codigo
        local_desc = self.descricao or self.codigo
        return f"{armazem_nome} - {local_desc}"
    
    def get_ocupacao_kg(self):
        """Retorna ocupação atual em kg"""
        total = self.lotes.filter(
            status__in=['DISPONIVEL', 'BLOQUEADO']
        ).aggregate(
            total=models.Sum('quantidade_atual')
        )['total'] or Decimal('0')
        return total
    
    def get_percentual_ocupacao(self):
        """Retorna percentual de ocupação"""
        if not self.capacidade_kg:
            return None
        ocupacao = self.get_ocupacao_kg()
        return (ocupacao / self.capacidade_kg) * 100
    
    def bloquear(self, motivo, usuario=None):
        """Bloqueia o local"""
        self.bloqueado = True
        self.motivo_bloqueio = motivo
        self.data_bloqueio = timezone.now()
        self.bloqueado_por = usuario
        self.save()
    
    def desbloquear(self):
        """Desbloqueia o local"""
        self.bloqueado = False
        self.motivo_bloqueio = ''
        self.data_bloqueio = None
        self.bloqueado_por = None
        self.save()


class Lote(models.Model):
    quantidade_inicial = models.DecimalField(
        'Quantidade Inicial',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Quantidade inicial do lote',
        default=0
    )
    
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('BLOQUEADO', 'Bloqueado'),
        ('VENCIDO', 'Vencido'),
        ('ESGOTADO', 'Esgotado'),
        ('QUARENTENA', 'Quarentena'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='lotes',
        verbose_name='Empresa'
    )
    
    # Produto
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='lotes',
        verbose_name='Produto'
    )
    
    # Localização
    armazem = models.ForeignKey(
        Armazem,
        on_delete=models.PROTECT,
        related_name='lotes',
        verbose_name='Armazém'
    )
    
    local_estocagem = models.ForeignKey(
        LocalEstocagem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes',
        verbose_name='Local de Estocagem'
    )
    
    # Identificação do lote
    numero_lote = models.CharField(
        'Número do Lote',
        max_length=50,
        help_text='Número do lote do fabricante'
    )
    
    # Datas
    data_fabricacao = models.DateField(
        'Data de Fabricação',
        null=True,
        blank=True
    )
    
    data_validade = models.DateField(
        'Data de Validade',
        null=True,
        blank=True,
        help_text='Data de vencimento do lote'
    )
    
    data_entrada = models.DateTimeField(
        'Data de Entrada',
        null=True,
        blank=True
    )
    
    quantidade_atual = models.DecimalField(
        'Quantidade Atual',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Quantidade disponível atual'
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='lotes',
        verbose_name='Unidade de Medida'
    )
    
    # Origem
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_fornecidos',
        verbose_name='Fornecedor'
    )
    
    nota_fiscal = models.CharField(
        'Nota Fiscal',
        max_length=20,
        blank=True,
        help_text='Número da NF de entrada'
    )
    
    # Valores
    valor_unitario = models.DecimalField(
        'Valor Unitário',
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor unitário de compra'
    )
    
    valor_total = models.DecimalField(
        'Valor Total',
        max_digits=15,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor total do lote'
    )
    
    # Status e bloqueio
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='DISPONIVEL'
    )
    
    motivo_bloqueio = models.TextField(
        'Motivo do Bloqueio',
        blank=True
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lotes_cadastrados',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Lote'
        verbose_name_plural = 'Lotes'
        ordering = ['data_validade', 'numero_lote']
        indexes = [
            models.Index(fields=['empresa', 'produto', 'status']),
            models.Index(fields=['armazem', 'status']),
            models.Index(fields=['data_validade']),
            models.Index(fields=['numero_lote']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'produto', 'numero_lote', 'data_fabricacao'],
                name='unique_lote_produto_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.produto.nome} - Lote {self.numero_lote}"
    
    def clean(self):
        """Validações customizadas"""
        from datetime import date as _date
        errors = {}

        # Valida datas
        df = self.data_fabricacao
        dv = self.data_validade
        if isinstance(df, str):
            try:
                df = _date.fromisoformat(df)
            except (ValueError, AttributeError):
                df = None
        if isinstance(dv, str):
            try:
                dv = _date.fromisoformat(dv)
            except (ValueError, AttributeError):
                dv = None
        if df and dv:
            if df > dv:
                errors['data_validade'] = 'Data de validade deve ser posterior à fabricação'
        
        # Valida quantidade
        if self.quantidade_atual > self.quantidade_inicial:
            errors['quantidade_atual'] = 'Quantidade atual não pode ser maior que inicial'
        
        # Valida local pertence ao armazém
        if self.local_estocagem and self.local_estocagem.armazem != self.armazem:
            errors['local_estocagem'] = 'Local de estocagem não pertence ao armazém selecionado'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Atualiza status automaticamente e recalcula estoque_atual do produto."""
        from datetime import date as _date
        if isinstance(self.data_validade, str):
            try:
                self.data_validade = _date.fromisoformat(self.data_validade)
            except (ValueError, AttributeError):
                self.data_validade = None
        if isinstance(self.data_fabricacao, str):
            try:
                self.data_fabricacao = _date.fromisoformat(self.data_fabricacao)
            except (ValueError, AttributeError):
                self.data_fabricacao = None
        # Ao criar, só iguala quantidade_atual à inicial se não foi explicitamente definida
        if self._state.adding and (self.quantidade_atual is None):
            self.quantidade_atual = self.quantidade_inicial
        # Verifica vencimento
        if self.data_validade and self.data_validade < timezone.now().date():
            if self.status == 'DISPONIVEL':
                self.status = 'VENCIDO'
        # Verifica esgotamento
        if self.quantidade_atual == 0 and self.status != 'ESGOTADO':
            self.status = 'ESGOTADO'
        # Restaura status de ESGOTADO para DISPONIVEL se quantidade > 0
        # (não afeta BLOQUEADO, VENCIDO ou QUARENTENA - estatuses que precisam de ação manual)
        if self.quantidade_atual > 0 and self.status == 'ESGOTADO':
            self.status = 'DISPONIVEL'
        # Calcula valor total
        if self.valor_unitario and self.quantidade_inicial:
            self.valor_total = self.valor_unitario * self.quantidade_inicial
        super().save(*args, **kwargs)
        # Sempre recalcula estoque_atual do produto após salvar lote
        if hasattr(self.produto, 'recalcular_estoque'):
            self.produto.recalcular_estoque()
    
    def esta_vencido(self):
        """Verifica se o lote está vencido"""
        if not self.data_validade:
            return False
        return self.data_validade < timezone.now().date()
    
    def dias_para_vencer(self):
        """Retorna dias para vencimento"""
        if not self.data_validade:
            return None
        delta = self.data_validade - timezone.now().date()
        return delta.days
    
    def get_percentual_consumido(self):
        """Retorna percentual consumido do lote"""
        if self.quantidade_inicial == 0:
            return 100
        consumido = self.quantidade_inicial - self.quantidade_atual
        return (consumido / self.quantidade_inicial) * 100
    
    def bloquear(self, motivo):
        """Bloqueia o lote"""
        self.status = 'BLOQUEADO'
        self.motivo_bloqueio = motivo
        self.save()
    
    def desbloquear(self):
        """Desbloqueia o lote"""
        if self.status == 'BLOQUEADO':
            self.status = 'DISPONIVEL'
            self.motivo_bloqueio = ''
            self.save()


class MovimentacaoEstoque(models.Model):
    ORIGEM_CHOICES = [
        ('COMPRA', 'Compra'),
        ('PRODUCAO', 'Produção Interna'),
        ('DEVOLUCAO_CLIENTE', 'Devolução de Cliente'),
        ('TRANSFERENCIA_ENTRADA', 'Transferência (Entrada)'),
        ('AJUSTE_ENTRADA', 'Ajuste de Entrada'),
        ('REQUISICAO', 'Requisição'),
        ('CONSUMO_PRODUCAO', 'Consumo em Produção'),
        ('VENDA', 'Venda'),
        ('PERDA', 'Perda/Avaria'),
        ('TRANSFERENCIA_SAIDA', 'Transferência (Saída)'),
        ('AJUSTE_SAIDA', 'Ajuste de Saída'),
        ('DEVOLUCAO_FORNECEDOR', 'Devolução ao Fornecedor'),
        ('OS_DIRETA', 'Ordem de Serviço (Baixa Direta)'),
        ('PEDIDO_VENDA', 'Pedido de Venda'),
        ('DEVOLUCAO_VENDA', 'Devolução de Venda'),
        ('RECONTRATACAO', 'Recontratação'),
        ('REMESSA_FATURAMENTO', 'Remessa para Faturamento Posterior'),
        ('CANCELAMENTO_REMESSA', 'Cancelamento de Remessa'),
    ]
    origem = models.CharField(
        'Origem',
        max_length=50,
        choices=ORIGEM_CHOICES,
        blank=True,
        null=True
    )
    armazem_origem = models.ForeignKey(
        'Armazem',
        on_delete=models.SET_NULL,
        related_name='movimentacoes_origem',
        verbose_name='Armazém de Origem',
        blank=True,
        null=True
    )
    local_origem = models.CharField(
        'Local de Origem',
        max_length=100,
        blank=True,
        null=True
    )
    numero = models.CharField(
        'Número',
        max_length=30,
        blank=True,
        null=True
    )
    lote = models.ForeignKey(
        'Lote',
        on_delete=models.CASCADE,
        related_name='movimentacoes',
        verbose_name='Lote',
        blank=True,
        null=True
    )
    
    # Produto e Unidade de Medida (alternativos ao lote)
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.SET_NULL,
        related_name='movimentacoes_estoque',
        verbose_name='Produto',
        blank=True,
        null=True
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.SET_NULL,
        related_name='movimentacoes_estoque',
        verbose_name='Unidade de Medida',
        blank=True,
        null=True
    )
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('TRANSFERENCIA', 'Transferência'),
        ('AJUSTE', 'Ajuste de Inventário'),
        ('DEVOLUCAO', 'Devolução'),
    ]
    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=TIPO_CHOICES,
        default='ENTRADA'
    )
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='movimentacoes_estoque',
        verbose_name='Empresa'
    )
    
    # Localização destino (para transferências)
    armazem_destino = models.ForeignKey(
        Armazem,
        on_delete=models.PROTECT,
        related_name='movimentacoes_entrada',
        verbose_name='Armazém Destino',
        null=True,
        blank=True
    )
    
    local_destino = models.ForeignKey(
        LocalEstocagem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_entrada',
        verbose_name='Local Destino'
    )
    
    # Quantidade
    quantidade = models.DecimalField(
        'Quantidade',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Quantidade movimentada'
    )
    
    # Documentos relacionados
    documento = models.CharField(
        'Documento',
        max_length=50,
        blank=True,
        help_text='Nota fiscal, requisição, ordem de serviço, etc'
    )
    
    # Responsável
    requisitante = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_requisitadas',
        verbose_name='Requisitante'
    )
    
    aprovador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_aprovadas',
        verbose_name='Aprovador'
    )
    
    executado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_executadas',
        verbose_name='Executado por'
    )
    
    # Centro de custo (para requisições) - DESABILITADO TEMPORARIAMENTE
    # centro_custo = models.ForeignKey(
    #     'cadastros.CentroCusto',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='movimentacoes_estoque',
    #     verbose_name='Centro de Custo'
    # )
    
    # Observações
    observacao = models.TextField(
        'Observação',
        blank=True
    )
    
    justificativa = models.TextField(
        'Justificativa',
        blank=True,
        help_text='Justificativa para ajustes e perdas'
    )
    
    # Status e datas
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('EXECUTADO', 'Executado'),
        ('CANCELADO', 'Cancelado'),
    ]
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )
    
    data_movimentacao = models.DateTimeField(
        'Data da Movimentação',
        default=timezone.now,
        help_text='Data/hora da movimentação'
    )
    
    data_aprovacao = models.DateTimeField(
        'Data de Aprovação',
        null=True,
        blank=True
    )
    
    data_execucao = models.DateTimeField(
        'Data de Execução',
        null=True,
        blank=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentacoes_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Movimentação de Estoque'
        verbose_name_plural = 'Movimentações de Estoque'
        ordering = ['-data_movimentacao', '-numero']
        indexes = [
            models.Index(fields=['empresa', 'tipo', 'status']),
            models.Index(fields=['lote', 'data_movimentacao']),
            models.Index(fields=['numero']),
            models.Index(fields=['data_movimentacao']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'numero'],
                name='uniq_movimentacao_numero_por_empresa'
            ),
        ]

    def __str__(self):
        return f"{self.numero} - {self.get_tipo_display()} - {self.lote.produto.nome}"
    
    def clean(self):
        """Validações customizadas"""
        errors = {}
        
        # Validações por tipo
        if self.tipo == 'TRANSFERENCIA':
            if not self.armazem_destino:
                errors['armazem_destino'] = 'Armazém de destino é obrigatório para transferências'
            if self.armazem_origem == self.armazem_destino:
                errors['armazem_destino'] = 'Armazéns de origem e destino devem ser diferentes'
        
        # Valida quantidade disponível para saída (apenas validação, sem modificar dados)
        if self.tipo in ['SAIDA', 'TRANSFERENCIA'] and self.lote:
            if self.quantidade > self.lote.quantidade_atual:
                errors['quantidade'] = (
                    f'Quantidade insuficiente. Disponível: {self.lote.quantidade_atual}'
                )
        elif self.tipo == 'AJUSTE' and self.lote and self.origem == 'AJUSTE_SAIDA':
            if self.quantidade > self.lote.quantidade_atual:
                errors['quantidade'] = (
                    f'Quantidade insuficiente para ajuste de saída. '
                    f'Disponível: {self.lote.quantidade_atual}'
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Gera número automático mas NÃO atualiza estoque aqui"""
        if not self.numero:
            self.numero = self.gerar_numero()
        
        # Define armazém origem automaticamente se não informado
        if not self.armazem_origem and self.tipo in ['SAIDA', 'TRANSFERENCIA']:
            if self.lote:
                self.armazem_origem = self.lote.armazem
                self.local_origem = self.lote.local_estocagem
        
        super().save(*args, **kwargs)
    
    def gerar_numero(self):
        """Gera número sequencial da movimentação"""
        prefixo_tipo = {
            'ENTRADA': 'ENT',
            'SAIDA': 'SAI',
            'TRANSFERENCIA': 'TRF',
            'AJUSTE': 'AJU',
            'DEVOLUCAO': 'DEV',
        }
        prefixo = prefixo_tipo.get(self.tipo, 'MOV')
        
        # Busca último número
        ultima = MovimentacaoEstoque.objects.filter(
            empresa=self.empresa,
            numero__startswith=f"{prefixo}-"
        ).order_by('-numero').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero.split('-')[1])
                proximo_num = ultimo_num + 1
            except (IndexError, ValueError):
                proximo_num = 1
        else:
            proximo_num = 1
        
        return f"{prefixo}-{proximo_num:06d}"
    
    def aprovar(self, usuario):
        """Aprova a movimentação"""
        if self.status != 'PENDENTE':
            raise ValidationError('Apenas movimentações pendentes podem ser aprovadas')
        
        self.status = 'APROVADO'
        self.aprovador = usuario
        self.data_aprovacao = timezone.now()
        self.save()
    
    from django.db import transaction

    @transaction.atomic
    def executar(self, usuario):
        """
        Executa a movimentação e atualiza estoque (atomicamente)
        """
        if self.status not in ['PENDENTE', 'APROVADO']:
            raise ValidationError('Movimentação não pode ser executada')
        self._atualizar_estoque()
        self.status = 'EXECUTADO'
        self.executado_por = usuario
        self.data_execucao = timezone.now()
        self.save()

    def _atualizar_estoque(self):
        """
        Atualiza quantidade do lote e estoque do produto
        Chamado apenas por executar() para movimentações que precisam de validação
        Suporta AMBOS: movimentações com lote e movimentações diretas (sem lote)
        """
        from decimal import Decimal
        from django.db.models import Sum, Q
        
        # Se não tem lote, atualiza estoque direto do produto
        if not self.lote:
            if self.tipo in ['ENTRADA', 'SAIDA'] and self.produto:
                # Recalcula estoque do produto
                movimentacoes = MovimentacaoEstoque.objects.filter(
                    Q(produto=self.produto) | Q(lote__produto=self.produto)
                )
                entrada = movimentacoes.filter(tipo='ENTRADA').aggregate(
                    total=Sum('quantidade')
                )['total'] or Decimal('0.000')
                saida = movimentacoes.filter(tipo='SAIDA').aggregate(
                    total=Sum('quantidade')
                )['total'] or Decimal('0.000')
                self.produto.estoque_atual = Decimal(entrada) - Decimal(saida)
                self.produto.save(update_fields=['estoque_atual'])
            return

        # Trava a linha do lote para evitar lost update em execuções concorrentes
        self.lote = Lote.objects.select_for_update().get(pk=self.lote.pk)
        produto = self.lote.produto

        # ENTRADA
        if self.tipo == 'ENTRADA':
            self.lote.quantidade_atual += self.quantidade
            self.lote.save()
        
        # SAIDA ou DEVOLUCAO
        elif self.tipo in ['SAIDA', 'DEVOLUCAO']:
            if self.lote.quantidade_atual < self.quantidade:
                raise ValidationError(f'Quantidade insuficiente em estoque. Disponível: {self.lote.quantidade_atual}')
            self.lote.quantidade_atual -= self.quantidade
            self.lote.save()
        
        # TRANSFERENCIA
        elif self.tipo == 'TRANSFERENCIA':
            if self.lote.quantidade_atual < self.quantidade:
                raise ValidationError(f'Quantidade insuficiente em estoque. Disponível: {self.lote.quantidade_atual}')
            # Diminui do lote origem
            self.lote.quantidade_atual -= self.quantidade
            self.lote.save()
            
            # Busca ou cria lote destino
            try:
                lote_destino = Lote.objects.select_for_update().get(
                    empresa=self.empresa,
                    produto=self.lote.produto,
                    armazem=self.armazem_destino,
                    numero_lote=self.lote.numero_lote,
                    data_fabricacao=self.lote.data_fabricacao,
                )
                # Lote JÁ existe, apenas atualiza
                lote_destino.quantidade_atual += self.quantidade
                if lote_destino.quantidade_atual > lote_destino.quantidade_inicial:
                    lote_destino.quantidade_inicial = lote_destino.quantidade_atual
                if lote_destino.quantidade_atual > 0:
                    lote_destino.status = 'DISPONIVEL'
                lote_destino.save()
            except Lote.DoesNotExist:
                # Lote NÃO existe, cria novo
                Lote.objects.create(
                    empresa=self.empresa,
                    produto=self.lote.produto,
                    armazem=self.armazem_destino,
                    local_estocagem=self.local_destino,
                    numero_lote=self.lote.numero_lote,
                    data_fabricacao=self.lote.data_fabricacao,
                    data_validade=self.lote.data_validade,
                    data_entrada=timezone.now(),
                    quantidade_inicial=self.quantidade,
                    quantidade_atual=self.quantidade,
                    unidade_medida=self.lote.unidade_medida,
                    fornecedor=self.lote.fornecedor,
                    nota_fiscal=getattr(self.lote, 'nota_fiscal', None),
                    valor_unitario=self.lote.valor_unitario,
                    cadastrado_por=self.executado_por,
                    status='DISPONIVEL',
                )
        
        # AJUSTE
        elif self.tipo == 'AJUSTE':
            if self.origem == 'AJUSTE_ENTRADA':
                self.lote.quantidade_atual += self.quantidade
            else:  # AJUSTE_SAIDA
                if self.lote.quantidade_atual < self.quantidade:
                    raise ValidationError(f'Quantidade insuficiente para ajuste de saída. Disponível: {self.lote.quantidade_atual}')
                self.lote.quantidade_atual -= self.quantidade
            self.lote.save()
        
        # Atualiza estoque_atual do produto sempre ao final
        if hasattr(produto, 'recalcular_estoque'):
            produto.recalcular_estoque()
        else:
            lotes_filtrados = produto.lotes.filter(status__in=['DISPONIVEL', 'BLOQUEADO'])
            total = lotes_filtrados.aggregate(total=models.Sum('quantidade_atual'))['total']
            produto.estoque_atual = Decimal(total) if total is not None else Decimal('0.000')
            produto.save(update_fields=['estoque_atual'])
    
    def cancelar(self):
        """Cancela a movimentação"""
        if self.status == 'EXECUTADO':
            raise ValidationError('Movimentações executadas não podem ser canceladas')
        
        self.status = 'CANCELADO'
        self.save()
    
    # O método atualizar_estoque foi substituído por _atualizar_estoque e não deve ser chamado diretamente.


# ============================================
# INVENTÁRIO CÍCLICO (RF-056)
# ============================================

class InventarioCiclicoSchedule(models.Model):
    """Agendamento de inventários cíclicos"""
    
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('PAUSADO', 'Pausado'),
        ('ENCERRADO', 'Encerrado'),
    ]
    
    PERIODICIDADE_CHOICES = [
        ('SEMANAL', 'Semanal'),
        ('QUINZENAL', 'Quinzenal'),
        ('MENSAL', 'Mensal'),
        ('TRIMESTRAL', 'Trimestral'),
    ]
    
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    periodicidade = models.CharField(max_length=20, choices=PERIODICIDADE_CHOICES)
    armazen = models.ForeignKey(Armazem, on_delete=models.CASCADE)
    categoria_amostragem = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')], default='A')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    proxima_contagem = models.DateField()
    ultima_contagem = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nome} - {self.armazen.nome}"
    
    class Meta:
        ordering = ['-data_inicio']
        verbose_name = 'Agendamento de Inventário Cíclico'
        verbose_name_plural = 'Agendamentos de Inventário Cíclico'


class InventarioCiclico(models.Model):
    """Contagem cíclica de estoque"""
    
    STATUS_CHOICES = [
        ('PLANEJADO', 'Planejado'),
        ('EM_CONTAGEM', 'Em Contagem'),
        ('CONCILIADO', 'Conciliado'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    RESULTADO_CHOICES = [
        ('CONFORME', 'Conforme'),
        ('DIVERGENCIA', 'Com Divergência'),
    ]
    
    TIPO_CHOICES = [
        ('POR_LOTE', 'Por Lote'),
        ('POR_ITEM', 'Por Item (Estoque Agregado)'),
    ]
    
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE)
    schedule = models.ForeignKey(InventarioCiclicoSchedule, on_delete=models.SET_NULL, null=True, blank=True)
    numero = models.CharField(max_length=20, unique=True)
    armazem = models.ForeignKey(Armazem, on_delete=models.CASCADE)
    tipo_inventario = models.CharField(max_length=20, choices=TIPO_CHOICES, default='POR_LOTE')
    data_contagem = models.DateField()
    data_conciliacao = models.DateField(null=True, blank=True)
    data_finalizacao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANEJADO')
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES, null=True, blank=True)
    
    # Estatísticas
    total_items_sistema = models.IntegerField(default=0)
    total_items_contados = models.IntegerField(default=0)
    total_items_divergencia = models.IntegerField(default=0)
    acuracia_percentual = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    valor_divergencia = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    observacoes = models.TextField(blank=True)
    responsavel = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.numero} - {self.armazem.nome} ({self.data_contagem})"
    
    def calcular_acuracia(self):
        """Calcula acurácia do inventário"""
        if self.total_items_sistema == 0:
            self.acuracia_percentual = 100
        else:
            itens_corretos = self.total_items_sistema - self.total_items_divergencia
            self.acuracia_percentual = (itens_corretos / self.total_items_sistema) * 100
        self.save(update_fields=['acuracia_percentual'])
    
    def conciliar(self):
        """Realiza conciliação automática"""
        from django.utils import timezone
        
        self.data_conciliacao = timezone.now().date()
        self.status = 'CONCILIADO'
        
        # Processa divergências
        itens_divergencia = self.itens.filter(tem_divergencia=True)
        for item in itens_divergencia:
            item.processar_ajuste()
        
        self.calcular_acuracia()
        self.resultado = 'CONFORME' if self.total_items_divergencia == 0 else 'DIVERGENCIA'
        self.save()
    
    def finalizar(self):
        """Finaliza o inventário"""
        from django.utils import timezone
        
        self.data_finalizacao = timezone.now().date()
        self.status = 'FINALIZADO'
        self.save()
    
    class Meta:
        ordering = ['-data_contagem']
        verbose_name = 'Inventário Cíclico'
        verbose_name_plural = 'Inventários Cíclicos'


class InventarioCiclicoItem(models.Model):
    """Item/Lote a ser contado no inventário cíclico"""
    
    inventario = models.ForeignKey(InventarioCiclico, on_delete=models.CASCADE, related_name='itens')
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE, null=True, blank=True)  # Null quando for por item
    produto = models.ForeignKey('produtos.Produto', on_delete=models.CASCADE)
    
    # Dados do sistema
    quantidade_sistema = models.DecimalField(max_digits=15, decimal_places=3)
    valor_unitario_sistema = models.DecimalField(max_digits=12, decimal_places=2)
    valor_total_sistema = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Dados da contagem
    quantidade_contada = models.DecimalField(max_digits=15, decimal_places=3, null=True, blank=True)
    data_contagem = models.DateTimeField(null=True, blank=True)
    contado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Divergência
    tem_divergencia = models.BooleanField(default=False)
    quantidade_diferenca = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    valor_diferenca = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    motivo_divergencia = models.CharField(max_length=200, blank=True)
    
    # Classificação ABC
    classificacao_abc = models.CharField(max_length=1, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')], default='C')
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.lote:
            return f"{self.produto.nome} - {self.lote.numero_lote}"
        return f"{self.produto.nome} (Agregado)"
    
    def registrar_contagem(self, quantidade, contado_por):
        """Registra a contagem de um item"""
        from django.utils import timezone
        
        self.quantidade_contada = quantidade
        self.data_contagem = timezone.now()
        self.contado_por = contado_por
        
        # Calcula divergência
        self.quantidade_diferenca = self.quantidade_contada - self.quantidade_sistema
        self.valor_diferenca = self.quantidade_diferenca * self.valor_unitario_sistema
        self.tem_divergencia = self.quantidade_diferenca != 0
        
        self.save()
        
        # Atualiza estatísticas do inventário
        inventario = self.inventario
        inventario.total_items_contados = inventario.itens.filter(quantidade_contada__isnull=False).count()
        inventario.total_items_divergencia = inventario.itens.filter(tem_divergencia=True).count()
        inventario.valor_divergencia = sum(
            item.valor_diferenca for item in inventario.itens.all()
        )
        inventario.save()
    
    def processar_ajuste(self):
        """Cria movimentação de ajuste para divergência"""
        if not self.tem_divergencia:
            return
        
        tipo_movimento = 'AJUSTE_ENTRADA' if self.quantidade_diferenca > 0 else 'AJUSTE_SAIDA'
        
        movimentacao = MovimentacaoEstoque.objects.create(
            empresa=self.inventario.empresa,
            produto=self.produto,
            lote=self.lote,
            tipo='AJUSTE',
            origem=tipo_movimento,
            quantidade=abs(self.quantidade_diferenca),
            armazem_origem=self.inventario.armazem,
            observacao=f'Ajuste de inventário cíclico {self.inventario.numero}',
            status='PENDENTE',
            executado_por=self.inventario.responsavel,
        )

        # Executa para atualizar lote e estoque_atual do produto
        movimentacao.executar(self.inventario.responsavel)
    
    class Meta:
        ordering = ['classificacao_abc', 'produto__nome']
        verbose_name = 'Item de Inventário Cíclico'
        verbose_name_plural = 'Itens de Inventário Cíclico'

