
"""
Módulo de Compras - Models
Sistema completo de solicitação, cotação e pedido de compras
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

# Modelos legados da extinta "Cotação Inteligente" — sem tela ativa, mantidos
# apenas para não perder cotações já registradas por ali. Precisam continuar
# importados aqui para que o Django registre o model no app registry, já que
# HistoricoPrecoFornecedor (abaixo, em uso ativo) referencia CotacaoInteligente.
from .models_cotacao import (  # noqa: F401
    CotacaoInteligente,
    CotacaoInteligenteItem,
    CotacaoInteligenteFornecedor,
    CotacaoInteligenteProposta,
)

# ...existing code...

# Comunicação de divergências em recebimentos
class RecebimentoMensagem(models.Model):
    recebimento = models.ForeignKey(
        'RecebimentoCompra',
        on_delete=models.CASCADE,
        related_name='mensagens_recebimento',
        verbose_name='Recebimento'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='mensagens_recebimento_autor',
        verbose_name='Autor'
    )
    destinatario = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='mensagens_recebimento_destinatario',
        verbose_name='Fornecedor Destinatário',
        blank=True,
        null=True
    )
    mensagem = models.TextField('Mensagem')
    data_envio = models.DateTimeField('Data de Envio', auto_now_add=True)

    class Meta:
        verbose_name = 'Mensagem de Recebimento'
        verbose_name_plural = 'Mensagens de Recebimento'
        ordering = ['data_envio']

    def __str__(self):
        return f"{self.autor} ({self.data_envio:%d/%m/%Y %H:%M}): {self.mensagem[:30]}..."

"""
Módulo de Compras - Models
Sistema completo de solicitação, cotação e pedido de compras
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


# ... (restante dos models)

# Adicionar ao final do arquivo, após todos os outros models:
class SolicitacaoMensagem(models.Model):
    """
    Mensagens de diálogo entre aprovador e solicitante de uma solicitação de compra
    """
    solicitacao = models.ForeignKey(
        'SolicitacaoCompra',
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name='Solicitação'
    )
    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='mensagens_solicitacao',
        verbose_name='Autor'
    )
    mensagem = models.TextField('Mensagem')
    data_envio = models.DateTimeField('Data de Envio', auto_now_add=True)

    class Meta:
        verbose_name = 'Mensagem da Solicitação'
        verbose_name_plural = 'Mensagens das Solicitações'
        ordering = ['data_envio']

    def __str__(self):
        return f"{self.autor.get_full_name()} ({self.data_envio:%d/%m/%Y %H:%M}): {self.mensagem[:30]}..."
"""
Módulo de Compras - Models
Sistema completo de solicitação, cotação e pedido de compras
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal


class SolicitacaoCompra(models.Model):
    cancelado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_canceladas',
        verbose_name='Usuário que Cancelou'
    )
    # Controle de leitura de mensagens
    data_leitura_solicitante = models.DateTimeField('Última leitura do solicitante', null=True, blank=True)
    data_leitura_aprovador = models.DateTimeField('Última leitura do aprovador', null=True, blank=True)

    def tem_nova_mensagem_para(self, usuario):
        """Retorna True se há mensagens não lidas para o usuário informado.

        Opera sobre self.mensagens.all() para aproveitar o cache de
        prefetch_related('mensagens') feito na view — não usar .filter()/
        .order_by() aqui, pois isso ignora o cache do prefetch e gera uma
        query nova por chamada (N+1 em listagens).
        """
        mensagens = list(self.mensagens.all())
        if not mensagens:
            return False
        if usuario == self.solicitante:
            autor_esperado, ultima_leitura = self.aprovador, self.data_leitura_solicitante
        elif usuario == self.aprovador:
            autor_esperado, ultima_leitura = self.solicitante, self.data_leitura_aprovador
        else:
            return False
        return any(
            m.autor_id == getattr(autor_esperado, 'id', None) and (ultima_leitura is None or m.data_envio > ultima_leitura)
            for m in mensagens
        )
    """
    Solicitação de Compra (Requisição Interna)
    RF-050: Solicitações de compra com aprovações por nível
    """
    
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('PENDENTE', 'Pendente Aprovação'),
        ('APROVADA', 'Aprovada'),
        ('PARCIALMENTE_COTADA', 'Parcialmente Cotada'),
        ('TOTALMENTE_COTADA', 'Totalmente Cotada'),
        ('EM_COMPRA', 'Em Processo de Compra'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='solicitacoes_compra',
        verbose_name='Empresa'
    )
    
    # Identificação
    numero = models.CharField(
        'Número',
        max_length=30,
        unique=True,
        help_text='Número único da solicitação'
    )
    
    # Solicitante
    solicitante = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='solicitacoes_compra',
        verbose_name='Solicitante'
    )
    
    # Datas
    data_solicitacao = models.DateTimeField(
        'Data da Solicitação',
        default=timezone.now
    )
    
    data_necessidade = models.DateField(
        'Data de Necessidade',
        help_text='Quando os produtos são necessários'
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=30,
        choices=STATUS_CHOICES,
        default='RASCUNHO'
    )
    
    # Aprovação
    aprovador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_aprovadas',
        verbose_name='Aprovador'
    )
    
    data_aprovacao = models.DateTimeField(
        'Data de Aprovação',
        null=True,
        blank=True
    )
    
    # Informações adicionais
    justificativa = models.TextField(
        'Justificativa',
        help_text='Motivo da solicitação'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Centro de custo
    departamento = models.CharField(
        'Departamento',
        max_length=100,
        blank=True
    )
    
    # Emergencial
    emergencial = models.BooleanField(
        'Compra Emergencial',
        default=False,
        help_text='Marcado como emergencial pula a aprovação formal'
    )

    ORIGEM_CHOICES = [
        ('MANUAL', 'Manual'),
        ('ESTOQUE_MINIMO', 'Estoque Mínimo'),
        ('FORNECEDOR_UNICO', 'Fornecedor Único'),
        ('REGULARIZACAO_POSTERIOR', 'Regularização Posterior'),
    ]
    origem = models.CharField(
        'Origem',
        max_length=30,
        choices=ORIGEM_CHOICES,
        default='MANUAL',
        help_text='Como esta solicitação foi gerada'
    )

    justificativa_emergencial = models.TextField(
        'Justificativa da Emergência',
        blank=True,
        help_text='Obrigatório para compras emergenciais'
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
    
    class Meta:
        verbose_name = 'Solicitação de Compra'
        verbose_name_plural = 'Solicitações de Compra'
        ordering = ['-data_solicitacao']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['numero']),
            models.Index(fields=['data_solicitacao']),
        ]
        permissions = [
            ('criar_solicitacao_emergencial', 'Pode criar solicitação de compra emergencial'),
            ('criar_cotacao_direto_estoque_minimo', 'Pode gerar cotação direto da Central de Alertas de Estoque Mínimo'),
            ('criar_pedido_direto_fornecedor_unico', 'Pode gerar pedido de compra direto sem cotação formal'),
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.solicitante.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.gerar_numero()
        super().save(*args, **kwargs)
    
    def gerar_numero(self):
        """Gera número sequencial da solicitação"""
        ultima = SolicitacaoCompra.objects.filter(
            empresa=self.empresa,
            numero__startswith='SC-'
        ).order_by('-numero').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero.split('-')[1])
                proximo_num = ultimo_num + 1
            except (IndexError, ValueError):
                proximo_num = 1
        else:
            proximo_num = 1
        
        return f"SC-{proximo_num:06d}"
    
    def calcular_percentual_cotado(self):
        """Calcula percentual de itens já cotados ou aprovados para compra.

        Opera sobre self.itens.all() em memória (não .filter().count()) para
        aproveitar o cache de prefetch_related('itens') feito nas listagens —
        .filter() sobre o related manager ignora o cache do prefetch e gera
        uma query nova por chamada (mesmo problema de tem_nova_mensagem_para).
        """
        itens = list(self.itens.all())
        total_itens = len(itens)
        if total_itens == 0:
            return 0
        itens_cotados = sum(1 for item in itens if item.status_item in ('COTADO', 'APROVADO'))
        return int((itens_cotados / total_itens) * 100)
    
    def atualizar_status_cotacao(self):
        """Atualiza status baseado no percentual cotado ou aprovado, exceto se já estiver CANCELADA ou CONCLUIDA"""
        if self.status in ['CANCELADA', 'CONCLUIDA']:
            return
        percentual = self.calcular_percentual_cotado()
        if percentual == 0:
            if self.status == 'APROVADA':
                return  # Mantém aprovada
            self.status = 'PENDENTE'
        elif percentual == 100:
            self.status = 'TOTALMENTE_COTADA'
        else:
            self.status = 'PARCIALMENTE_COTADA'
        self.save()
    
    def aprovar(self, usuario):
        """Aprova a solicitação"""
        if self.status != 'PENDENTE':
            raise ValidationError('Apenas solicitações pendentes podem ser aprovadas')
        if self.emergencial and not self.justificativa_emergencial:
            raise ValidationError('Solicitações emergenciais precisam de justificativa da emergência')
        self.status = 'APROVADA'
        self.aprovador = usuario
        self.data_aprovacao = timezone.now()
        self.save()

    def cancelar(self, usuario=None):
        """Cancela a solicitação e registra o usuário que cancelou"""
        if self.status in ['CONCLUIDA']:
            raise ValidationError('Solicitações concluídas não podem ser canceladas')
        self.status = 'CANCELADA'
        if usuario:
            self.cancelado_por = usuario
        self.save()


class ItemSolicitacaoCompra(models.Model):
    motivo_recusa = models.TextField('Motivo da Recusa', blank=True, null=True)
    aprovador_recusa = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_reprovados',
        verbose_name='Aprovador que Reprovou'
    )
    """
    Item da Solicitação de Compra
    """
    
    STATUS_ITEM_CHOICES = [
        ('PENDENTE', 'Pendente Cotação'),
        ('SELECIONADO', 'Selecionado para Cotação'),
        ('EM_COTACAO', 'Em Cotação'),
        ('COTADO', 'Cotado'),
        ('APROVADO', 'Aprovado para Compra'),
    ]
    
    # Relacionamento
    solicitacao = models.ForeignKey(
        SolicitacaoCompra,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Solicitação'
    )
    
    # Produto
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='itens_solicitacao',
        verbose_name='Produto'
    )
    
    # Quantidade
    quantidade = models.DecimalField(
        'Quantidade',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='itens_solicitacao',
        verbose_name='Unidade de Medida'
    )
    
    # Seleção para cotação
    selecionado_para_cotar = models.BooleanField(
        'Selecionado para Cotação',
        default=False,
        help_text='Marca se este item foi selecionado para cotação'
    )
    
    # Status
    status_item = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_ITEM_CHOICES,
        default='PENDENTE'
    )
    
    # Cotação vinculada
    cotacao_vinculada = models.ForeignKey(
        'Cotacao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_origem',
        verbose_name='Cotação Vinculada'
    )
    
    # Informações adicionais
    especificacao = models.TextField(
        'Especificação Técnica',
        blank=True,
        help_text='Especificações técnicas do produto'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Item da Solicitação'
        verbose_name_plural = 'Itens da Solicitação'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade} {self.unidade_medida.sigla}"


class Cotacao(models.Model):
    """
    Cotação de Preços
    RF-051: Cotações com múltiplos fornecedores
    """
    
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='cotacoes',
        verbose_name='Empresa'
    )
    
    # Identificação
    numero = models.CharField(
        'Número',
        max_length=30,
        unique=True
    )
    
    # Solicitação origem
    solicitacao = models.ForeignKey(
        SolicitacaoCompra,
        on_delete=models.PROTECT,
        related_name='cotacoes',
        verbose_name='Solicitação de Compra'
    )
    
    # Responsável
    comprador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='cotacoes',
        verbose_name='Comprador'
    )
    
    # Datas
    data_cotacao = models.DateTimeField(
        'Data da Cotação',
        default=timezone.now
    )
    
    data_limite_resposta = models.DateField(
        'Data Limite para Resposta',
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='RASCUNHO'
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
    
    data_conclusao = models.DateTimeField(
        'Data de Conclusão',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Cotação'
        verbose_name_plural = 'Cotações'
        ordering = ['-data_cotacao']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['solicitacao']),
        ]

    def pode_concluir(self):
        """Só pode concluir se todos os itens estiverem cotados"""
        return all(item.status_item == 'COTADO' for item in self.itens.all())

    def concluir(self):
        """Marca cotação como concluída se todos os itens estiverem cotados"""
        for item in self.itens.all():
            item.atualizar_status()
        if not self.pode_concluir():
            raise Exception('Cotação não pode ser concluída: há itens pendentes ou parcialmente cotados.')
        self.status = 'CONCLUIDA'
        self.data_conclusao = timezone.now()
        self.save()
        # Atualiza status da solicitação
        self.solicitacao.atualizar_status_cotacao()
    
    def __str__(self):
        return f"{self.numero} - SC {self.solicitacao.numero}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.gerar_numero()
        super().save(*args, **kwargs)
    
    def gerar_numero(self):
        """Gera número sequencial da cotação"""
        ultima = Cotacao.objects.filter(
            empresa=self.empresa,
            numero__startswith='COT-'
        ).order_by('-numero').first()
        
        if ultima:
            try:
                ultimo_num = int(ultima.numero.split('-')[1])
                proximo_num = ultimo_num + 1
            except (IndexError, ValueError):
                proximo_num = 1
        else:
            proximo_num = 1
        
        return f"COT-{proximo_num:06d}"
    
    def concluir(self):
        """Marca cotação como concluída e atualiza status dos itens"""
        self.status = 'CONCLUIDA'
        self.data_conclusao = timezone.now()
        self.save()
        
        # Marca todos os itens desta cotação como COTADO
        for item_cotacao in self.itens.all():
            if item_cotacao.item_solicitacao:
                item_cotacao.item_solicitacao.status_item = 'COTADO'
                item_cotacao.item_solicitacao.save()
        
        # Atualiza status da solicitação
        self.solicitacao.atualizar_status_cotacao()


class ItemCotacao(models.Model):
    """
    Item da Cotação
    """
    
    # Relacionamento
    cotacao = models.ForeignKey(
        Cotacao,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Cotação'
    )
    
    # Item origem da solicitação
    item_solicitacao = models.ForeignKey(
        ItemSolicitacaoCompra,
        on_delete=models.PROTECT,
        related_name='cotacoes_item',
        verbose_name='Item da Solicitação'
    )
    
    # Produto
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='itens_cotacao',
        verbose_name='Produto'
    )
    
    # Quantidade
    quantidade = models.DecimalField(
        'Quantidade',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='itens_cotacao',
        verbose_name='Unidade de Medida'
    )
    
    # Informações
    especificacao = models.TextField(
        'Especificação',
        blank=True
    )
    
    class Meta:
        verbose_name = 'Item da Cotação'
        verbose_name_plural = 'Itens da Cotação'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade}"
    
    STATUS_ITEM_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PARCIALMENTE_COTADO', 'Parcialmente Cotado'),
        ('COTADO', 'Cotado'),
    ]

    status_item = models.CharField(
        'Status do Item',
        max_length=30,
        choices=STATUS_ITEM_CHOICES,
        default='PENDENTE'
    )

    def atualizar_status(self):
        propostas = self.propostas.all()
        if not propostas.exists():
            self.status_item = 'PENDENTE'
        elif propostas.filter(selecionado=True).exists():
            self.status_item = 'COTADO'
        elif any(p.preco_unitario > 0 for p in propostas):
            self.status_item = 'PARCIALMENTE_COTADO'
        else:
            self.status_item = 'PENDENTE'
        self.save(update_fields=['status_item'])

class FornecedorCotacao(models.Model):
    """
    Proposta do Fornecedor na Cotação
    """
    
    # Relacionamento
    item_cotacao = models.ForeignKey(
        ItemCotacao,
        on_delete=models.CASCADE,
        related_name='propostas',
        verbose_name='Item da Cotação'
    )
    
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='propostas_cotacao',
        verbose_name='Fornecedor'
    )
    
    # Valores
    preco_unitario = models.DecimalField(
        'Preço Unitário',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    preco_total = models.DecimalField(
        'Preço Total',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Condições
    prazo_entrega = models.PositiveIntegerField(
        'Prazo de Entrega (dias)',
        help_text='Prazo em dias úteis'
    )
    
    forma_pagamento = models.CharField(
        'Forma de Pagamento',
        max_length=100,
        blank=True
    )
    
    condicao_pagamento = models.CharField(
        'Condição de Pagamento',
        max_length=200,
        blank=True,
        help_text='Ex: 30/60 dias, à vista, etc'
    )
    
    # Seleção
    selecionado = models.BooleanField(
        'Selecionado',
        default=False,
        help_text='Marca este fornecedor como vencedor'
    )
    
    # Informações adicionais
    marca = models.CharField(
        'Marca',
        max_length=100,
        blank=True
    )

    observacoes = models.TextField(
        'Observações',
        blank=True
    )

    motivo_escolha = models.TextField(
        'Motivo da Escolha',
        blank=True,
        help_text='Informe o motivo da escolha caso não seja o menor preço.'
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data do Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Proposta do Fornecedor'
        verbose_name_plural = 'Propostas dos Fornecedores'
        ordering = ['preco_total']
    
    def __str__(self):
        return f"{self.fornecedor.nome_fantasia} - R$ {self.preco_total}"
    
    def save(self, *args, **kwargs):
        # Calcula preço total
        if self.preco_unitario and self.item_cotacao:
            self.preco_total = self.preco_unitario * self.item_cotacao.quantidade
        super().save(*args, **kwargs)


class PedidoCompra(models.Model):
    """
    Pedido de Compra (Purchase Order)
    Gerado após conclusão da cotação
    """
    
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('PENDENTE', 'Pendente Envio'),
        ('ENVIADO', 'Enviado ao Fornecedor'),
        ('CONFIRMADO', 'Confirmado pelo Fornecedor'),
        ('EM_ENTREGA', 'Em Entrega'),
        ('PARCIALMENTE_RECEBIDO', 'Parcialmente Recebido'),
        ('RECEBIDO', 'Totalmente Recebido'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='pedidos_compra',
        verbose_name='Empresa'
    )
    
    # Identificação
    numero = models.CharField(
        'Número do Pedido',
        max_length=20,
        unique=True,
        blank=True
    )
    
    # Relacionamentos
    cotacao = models.ForeignKey(
        Cotacao,
        on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name='Cotação Origem',
        null=True,  # Permite pedido sem cotação (modo simples)
        blank=True,
        help_text='Opcional no modo simples de compras'
    )

    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='pedidos_compra',
        verbose_name='Fornecedor'
    )

    comprador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='pedidos_realizados',
        verbose_name='Comprador'
    )
    
    # Status e Datas
    status = models.CharField(
        'Status',
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )
    
    data_pedido = models.DateTimeField(
        'Data do Pedido',
        auto_now_add=True
    )
    
    data_envio = models.DateTimeField(
        'Data de Envio',
        null=True,
        blank=True
    )
    
    data_confirmacao = models.DateTimeField(
        'Data de Confirmação',
        null=True,
        blank=True
    )
    
    data_entrega_prevista = models.DateField(
        'Data de Entrega Prevista',
        null=True,
        blank=True
    )
    
    data_entrega_real = models.DateField(
        'Data de Entrega Real',
        null=True,
        blank=True
    )
    
    # Condições Comerciais
    forma_pagamento = models.CharField(
        'Forma de Pagamento',
        max_length=100,
        blank=True
    )
    
    condicao_pagamento = models.CharField(
        'Condição de Pagamento',
        max_length=100,
        blank=True
    )
    
    prazo_entrega_dias = models.IntegerField(
        'Prazo de Entrega (dias)',
        default=0
    )
    
    # Valores
    valor_total = models.DecimalField(
        'Valor Total',
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    valor_desconto = models.DecimalField(
        'Desconto',
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    valor_frete = models.DecimalField(
        'Frete',
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    valor_final = models.DecimalField(
        'Valor Final',
        max_digits=15,
        decimal_places=2,
        default=0
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    observacoes_internas = models.TextField(
        'Observações Internas',
        blank=True,
        help_text='Não aparece no PDF do pedido'
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Data de Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Pedido de Compra'
        verbose_name_plural = 'Pedidos de Compra'
        ordering = ['-data_pedido']
    
    def __str__(self):
        return f"{self.numero} - {self.fornecedor.nome_fantasia}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.gerar_numero()
        # Proteção: se já foi ENVIADO, nunca volta para PENDENTE
        if self.pk:
            from django.db import transaction
            try:
                old = type(self).objects.get(pk=self.pk)
                if old.status == 'ENVIADO' and self.status == 'PENDENTE':
                    self.status = 'ENVIADO'
            except type(self).DoesNotExist:
                pass
        # Calcula valor final
        self.valor_final = self.valor_total - self.valor_desconto + self.valor_frete
        super().save(*args, **kwargs)
    
    def gerar_numero(self):
        """Gera número sequencial PO-XXXXXX"""
        ultimo = PedidoCompra.objects.filter(
            empresa=self.empresa
        ).order_by('-id').first()
        
        if ultimo and ultimo.numero:
            try:
                ultimo_num = int(ultimo.numero.split('-')[1])
                novo_num = ultimo_num + 1
            except (IndexError, ValueError):
                novo_num = 1
        else:
            novo_num = 1
        
        return f"PO-{novo_num:06d}"
    
    def enviar(self):
        """Marca pedido como enviado"""
        self.status = 'ENVIADO'
        self.data_envio = timezone.now()
        self.save()
    
    def confirmar(self):
        """Marca pedido como confirmado pelo fornecedor"""
        self.status = 'CONFIRMADO'
        self.data_confirmacao = timezone.now()
        self.save()
    
    def iniciar_entrega(self):
        """Marca pedido como em entrega"""
        self.status = 'EM_ENTREGA'
        self.save()
    
    def receber_parcial(self):
        """Marca pedido como parcialmente recebido"""
        self.status = 'PARCIALMENTE_RECEBIDO'
        self.save()
    
    def receber_total(self):
        """Marca pedido como totalmente recebido"""
        self.status = 'RECEBIDO'
        self.data_entrega_real = timezone.now().date()
        self.save()
    
    def cancelar(self, motivo=''):
        """Cancela o pedido"""
        self.status = 'CANCELADO'
        if motivo:
            self.observacoes_internas += f"\n\nCancelado: {motivo}"
        self.save()
    
    def calcular_total(self):
        """Calcula o valor total baseado nos itens"""
        total = sum(item.preco_total for item in self.itens.all())
        self.valor_total = total
        self.save()
        return total


class ItemPedidoCompra(models.Model):
    """
    Item do Pedido de Compra
    """
    
    # Relacionamentos
    pedido = models.ForeignKey(
        PedidoCompra,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Pedido'
    )
    
    proposta_fornecedor = models.ForeignKey(
        FornecedorCotacao,
        on_delete=models.PROTECT,
        related_name='itens_pedido',
        verbose_name='Proposta Origem',
        null=True,  # Permite item sem proposta (modo simples)
        blank=True,
        help_text='Opcional no modo simples de compras'
    )
    
    # Produto
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='itens_pedido_compra',
        verbose_name='Produto'
    )
    
    # Quantidades
    quantidade_pedida = models.DecimalField(
        'Quantidade Pedida',
        max_digits=15,
        decimal_places=3
    )
    
    quantidade_recebida = models.DecimalField(
        'Quantidade Recebida',
        max_digits=15,
        decimal_places=3,
        default=0
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='itens_pedido_compra',
        verbose_name='Unidade de Medida'
    )
    
    # Preços
    preco_unitario = models.DecimalField(
        'Preço Unitário',
        max_digits=15,
        decimal_places=2
    )
    
    preco_total = models.DecimalField(
        'Preço Total',
        max_digits=15,
        decimal_places=2
    )

    valor_desconto = models.DecimalField(
        'Desconto',
        max_digits=15,
        decimal_places=2,
        default=0
    )

    # Detalhes
    especificacao = models.TextField(
        'Especificação',
        blank=True
    )
    
    marca = models.CharField(
        'Marca',
        max_length=100,
        blank=True
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        ordering = ['id']
    
    def __str__(self):
        return f"{self.produto.nome} - {self.quantidade_pedida} {self.unidade_medida.sigla}"
    
    def save(self, *args, **kwargs):
        bruto = self.preco_unitario * self.quantidade_pedida
        desconto = self.valor_desconto or Decimal('0')
        self.preco_total = max(Decimal('0'), bruto - desconto)
        super().save(*args, **kwargs)
    
    @property
    def quantidade_pendente(self):
        """Retorna quantidade ainda não recebida"""
        return self.quantidade_pedida - self.quantidade_recebida
    
    @property
    def percentual_recebido(self):
        """Retorna percentual recebido"""
        if self.quantidade_pedida > 0:
            return (self.quantidade_recebida / self.quantidade_pedida) * 100
        return 0

    @property
    def ja_faturado_pedido_completo(self):
        """
        True se algum recebimento anterior deste item já foi marcado, na
        conferência, com uma divergência cujo tipo tem gera_valor_pedido_completo=True
        — ou seja, o fornecedor já faturou (e já foi pago) pela quantidade PEDIDA
        deste item, mesmo tendo entregue menos. Recebimentos seguintes deste mesmo
        item não devem contribuir com novo valor financeiro.
        """
        recebimento_ids = self.recebimentos.values_list('recebimento_id', flat=True)
        if not recebimento_ids:
            return False
        return DivergenciaRecebimento.objects.filter(
            recebimento_id__in=recebimento_ids,
            tipo_divergencia__gera_valor_pedido_completo=True
        ).filter(
            models.Q(item_recebimento__item_pedido=self) | models.Q(item_recebimento__isnull=True)
        ).exists()


class RecebimentoCompra(models.Model):
    """
    Recebimento de Mercadorias do Pedido de Compra
    Permite recebimentos parciais e múltiplos
    """
    
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente Conferência'),
        ('CONFERIDO', 'Conferido'),
        ('DIVERGENTE', 'Com Divergência'),
        ('CANCELADO', 'Cancelado'),
        ('FINALIZADO', 'Finalizado'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='recebimentos_compra',
        verbose_name='Empresa'
    )
    
    # Vinculação
    pedido = models.ForeignKey(
        PedidoCompra,
        on_delete=models.PROTECT,
        related_name='recebimentos',
        verbose_name='Pedido de Compra',
        blank=True,
        null=True,
        help_text='Deixe em branco para entrada direta sem pedido'
    )
    
    # Para recebimentos sem pedido
    fornecedor = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.PROTECT,
        related_name='recebimentos_diretos',
        verbose_name='Fornecedor',
        blank=True,
        null=True,
        help_text='Obrigatório apenas para entradas diretas sem pedido'
    )
    
    # Identificação
    numero = models.CharField(
        'Número do Recebimento',
        max_length=30,
        unique=True,
        help_text='Número único do recebimento'
    )
    
    # Dados da Nota Fiscal
    nota_fiscal = models.CharField(
        'Número da NF-e',
        max_length=20,
        help_text='Número da Nota Fiscal de entrada'
    )
    
    serie_nota = models.CharField(
        'Série',
        max_length=5,
        default='1'
    )
    
    chave_nfe = models.CharField(
        'Chave NF-e',
        max_length=44,
        blank=True,
        help_text='Chave de acesso da NF-e (44 dígitos)'
    )
    
    data_emissao_nf = models.DateField(
        'Data de Emissão NF',
        help_text='Data de emissão da nota fiscal'
    )
    
    # Recebimento
    data_recebimento = models.DateField(
        'Data do Recebimento',
        default=timezone.now
    )
    
    hora_recebimento = models.TimeField(
        'Hora do Recebimento',
        default=timezone.now
    )
    
    # Responsável
    recebido_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='recebimentos_realizados',
        verbose_name='Recebido por'
    )
    
    # Status e controle
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )
    
    # Valores
    valor_total_nf = models.DecimalField(
        'Valor Total da NF',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Pode ser 0 quando este recebimento apenas completa fisicamente um pedido '
                   'cujo valor já foi integralmente faturado em uma entrega anterior '
                   '(divergência de quantidade "nota completa").'
    )

    valor_frete = models.DecimalField(
        'Frete',
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Valor do frete informado na nota fiscal'
    )

    valor_desconto = models.DecimalField(
        'Desconto',
        max_digits=15,
        decimal_places=2,
        default=0,
        help_text='Valor do desconto informado na nota fiscal'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Observações sobre o recebimento'
    )
    
    divergencias = models.TextField(
        'Divergências',
        blank=True,
        help_text='Registrar divergências encontradas (quantidade, qualidade, etc)'
    )
    
    # Anexos
    arquivo_nfe = models.FileField(
        'Arquivo XML da NF-e',
        upload_to='compras/nfe/%Y/%m/',
        blank=True,
        null=True
    )
    
    # Manifestação do Destinatário (MD-e)
    MANIFESTACAO_TIPO_CHOICES = [
        ('ciencia_operacao', 'Ciência da Operação'),
        ('confirmacao_operacao', 'Confirmação da Operação'),
        ('desconhecimento_operacao', 'Desconhecimento da Operação'),
        ('operacao_nao_realizada', 'Operação Não Realizada'),
    ]
    manifestacao_tipo = models.CharField(
        'Tipo de Manifestação',
        max_length=40,
        blank=True,
        choices=MANIFESTACAO_TIPO_CHOICES,
    )
    manifestacao_protocolo = models.CharField('Protocolo da Manifestação', max_length=50, blank=True)
    manifestacao_data = models.DateTimeField('Data/Hora da Manifestação', null=True, blank=True)

    # Auditoria
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )

    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Recebimento de Compra'
        verbose_name_plural = 'Recebimentos de Compras'
        ordering = ['-data_recebimento', '-numero']
    
    def __str__(self):
        if self.pedido:
            return f"Recebimento {self.numero} - NF {self.nota_fiscal} - Pedido {self.pedido.numero}"
        else:
            return f"Recebimento {self.numero} - NF {self.nota_fiscal} - Entrada Direta"
    
    def clean(self):
        """Valida que pelo menos pedido ou fornecedor foi informado"""
        # Só exige fornecedor se não houver pedido
        if not self.pedido and not self.fornecedor:
            raise ValidationError('É necessário informar o Pedido de Compra OU o Fornecedor.')
        # Se houver pedido, não exige fornecedor
        # Se não houver pedido, exige fornecedor
    
    def save(self, *args, **kwargs):
        # Gera número automático se não existir
        if not self.numero:
            ultimo = RecebimentoCompra.objects.filter(
                empresa=self.empresa
            ).order_by('-numero').first()
            
            if ultimo and ultimo.numero:
                try:
                    ultimo_num = int(ultimo.numero.split('-')[1])
                    proximo_num = ultimo_num + 1
                except:
                    proximo_num = 1
            else:
                proximo_num = 1
            
            self.numero = f"REC-{proximo_num:06d}"
        
        super().save(*args, **kwargs)
        
        # Atualiza status do pedido (apenas se houver pedido)
        if self.pedido:
            self.atualizar_status_pedido()
    
    def atualizar_status_pedido(self):
        """Atualiza status do pedido baseado nos recebimentos"""
        if not self.pedido:
            return
            
        pedido = self.pedido
        
        # Verifica se todos os itens foram recebidos completamente
        todos_recebidos = all(
            item.quantidade_recebida >= item.quantidade_pedida
            for item in pedido.itens.all()
        )
        
        # Verifica se algum item foi parcialmente recebido
        algum_recebido = any(
            item.quantidade_recebida > 0
            for item in pedido.itens.all()
        )
        
        if todos_recebidos:
            pedido.status = 'RECEBIDO'
        elif algum_recebido:
            pedido.status = 'PARCIALMENTE_RECEBIDO'

        pedido.save(update_fields=['status'])

    def valor_calculado_nf(self):
        """
        Recalcula o valor total da NF a partir dos itens recebidos.

        Por padrão, cada item contribui com quantidade_recebida × preço − desconto
        (a NF cobre exatamente o que chegou). Quando o item está coberto por uma
        divergência cujo tipo tem `gera_valor_pedido_completo=True` (ex.: "entrega
        curta, mas o fornecedor faturou o pedido cheio"), o item passa a contribuir
        com o valor total do pedido (item_pedido.preco_total) em vez do recebido.
        """
        itens_com_valor_cheio = set(
            DivergenciaRecebimento.objects.filter(
                recebimento=self,
                tipo_divergencia__gera_valor_pedido_completo=True
            ).values_list('item_recebimento_id', flat=True)
        )
        afeta_todos_itens = None in itens_com_valor_cheio

        total = Decimal('0')
        for item in self.itens.select_related('item_pedido').all():
            usa_valor_cheio = afeta_todos_itens or item.pk in itens_com_valor_cheio
            if usa_valor_cheio and item.item_pedido:
                total += item.item_pedido.preco_total
            else:
                preco = item.preco_unitario
                if preco is None and item.item_pedido:
                    preco = item.item_pedido.preco_unitario
                preco = preco or Decimal('0')
                desconto = item.valor_desconto or Decimal('0')
                total += max(Decimal('0'), item.quantidade_recebida * preco - desconto)
        return total


class ItemRecebimento(models.Model):
    """
    Item recebido do Pedido de Compra
    """
    
    # Vinculação
    recebimento = models.ForeignKey(
        RecebimentoCompra,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Recebimento'
    )
    
    item_pedido = models.ForeignKey(
        ItemPedidoCompra,
        on_delete=models.PROTECT,
        related_name='recebimentos',
        verbose_name='Item do Pedido',
        blank=True,
        null=True,
        help_text='Obrigatório apenas para recebimentos vinculados a pedido'
    )
    
    # Para entradas diretas sem pedido
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='recebimentos_diretos',
        verbose_name='Produto',
        blank=True,
        null=True,
        help_text='Obrigatório apenas para entradas diretas sem pedido'
    )
    
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        verbose_name='Unidade de Medida',
        blank=True,
        null=True,
        help_text='Obrigatório apenas para entradas diretas sem pedido'
    )
    
    preco_unitario = models.DecimalField(
        'Preço Unitário',
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        blank=True,
        null=True,
        help_text='Obrigatório apenas para entradas diretas sem pedido'
    )
    
    # Quantidade
    quantidade_recebida = models.DecimalField(
        'Quantidade Recebida',
        max_digits=15,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    
    valor_desconto = models.DecimalField(
        'Valor de Desconto',
        max_digits=15,
        decimal_places=2,
        default=0,
        blank=True,
        null=True,
        help_text='Valor de desconto aplicado neste item'
    )
    
    # Armazenamento
    local_estoque = models.ForeignKey(
        'estoque.LocalEstocagem',
        on_delete=models.PROTECT,
        verbose_name='Local de Estoque'
    )
    
    lote = models.ForeignKey(
        'estoque.Lote',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Lote',
        help_text='Lote do fornecedor ou lote interno'
    )
    
    data_fabricacao = models.DateField(
        'Data de Fabricação',
        blank=True,
        null=True
    )
    
    data_validade = models.DateField(
        'Data de Validade',
        blank=True,
        null=True
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
    
    class Meta:
        verbose_name = 'Item do Recebimento'
        verbose_name_plural = 'Itens do Recebimento'
        ordering = ['id']
    
    def __str__(self):
        if self.item_pedido:
            return f"{self.item_pedido.produto.nome} - {self.quantidade_recebida} {self.item_pedido.unidade_medida.sigla}"
        else:
            return f"{self.produto.nome} - {self.quantidade_recebida} {self.unidade_medida.sigla}"
    
    def clean(self):
        """Valida que os campos necessários foram preenchidos"""
        if not self.item_pedido and not self.produto:
            raise ValidationError('É necessário informar o Item do Pedido OU o Produto.')
        
        if not self.item_pedido:
            # Entrada direta - valida campos obrigatórios
            if not self.unidade_medida:
                null=True,
                blank=True,
                raise ValidationError('Preço Unitário é obrigatório para entradas diretas.')
    
    def save(self, *args, **kwargs):
        # Se houver item_pedido, preenche produto e unidade_medida automaticamente
        if self.item_pedido and not self.produto:
            self.produto = self.item_pedido.produto
            self.unidade_medida = self.item_pedido.unidade_medida
            
        # Valida se não está recebendo mais do que foi pedido (apenas para itens com pedido)
        if self.item_pedido:
            total_ja_recebido = ItemRecebimento.objects.filter(
                item_pedido=self.item_pedido
            ).exclude(
                id=self.id
            ).aggregate(
                total=models.Sum('quantidade_recebida')
            )['total'] or Decimal('0')
            novo_total = total_ja_recebido + self.quantidade_recebida
            if novo_total > self.item_pedido.quantidade_pedida:
                raise ValidationError(
                    f"A quantidade total recebida ({novo_total}) não pode ser maior "
                    f"que a quantidade pedida ({self.item_pedido.quantidade_pedida})"
                )
            # Atualiza quantidade recebida no item do pedido
            self.item_pedido.quantidade_recebida = novo_total
            self.item_pedido.save(update_fields=['quantidade_recebida'])
            # Atualiza status do pedido após atualizar quantidades
            if self.recebimento and self.recebimento.pedido:
                self.recebimento.atualizar_status_pedido()

        # Cria automaticamente um lote padrão se não for informado
        if not self.lote:
            from estoque.models import Lote, Armazem
            try:
                armazem = None
                # Determina produto e unidade de medida
                if self.item_pedido:
                    produto = self.item_pedido.produto
                    unidade_medida = self.item_pedido.unidade_medida
                else:
                    produto = self.produto
                    unidade_medida = self.unidade_medida
                
                # Obtém armazém do local de estoque
                if self.local_estoque:
                    armazem = self.local_estoque.armazem
                
                # Se não conseguiu armazém, pega o primeiro da empresa
                if not armazem:
                    armazem = Armazem.objects.filter(empresa=self.recebimento.empresa).first()
                
                # Se ainda não há armazém, não consegue criar lote
                if not armazem:
                    import logging
                    logging.error(f"Nenhum armazém disponível para criar lote. Empresa: {self.recebimento.empresa}")
                    raise ValidationError("Nenhum armazém disponível. Configure um armazém para a empresa.")

                # Preço unitário de compra deste item, usado como custo do lote.
                # Prioriza o preço efetivamente informado no recebimento (pode
                # divergir do preço do pedido) e desconta o valor_desconto
                # rateado pela quantidade — senão o desconto lançado no
                # recebimento nunca refletia no custo do estoque.
                preco_compra = None
                preco_base = self.preco_unitario or (self.item_pedido.preco_unitario if self.item_pedido else None)
                if preco_base:
                    desconto = self.valor_desconto or Decimal('0')
                    if self.quantidade_recebida:
                        preco_compra = preco_base - (desconto / self.quantidade_recebida)
                    else:
                        preco_compra = preco_base

                # Cria o lote
                self.lote = Lote.objects.create(
                    empresa=self.recebimento.empresa,
                    produto=produto,
                    armazem=armazem,
                    local_estocagem=self.local_estoque,
                    numero_lote=f"AUTO-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    quantidade_inicial=self.quantidade_recebida,
                    quantidade_atual=self.quantidade_recebida,
                    data_fabricacao=self.data_fabricacao or timezone.now().date(),
                    data_validade=self.data_validade,
                    status='DISPONIVEL',
                    unidade_medida=unidade_medida,
                    valor_unitario=preco_compra,
                    fornecedor=self.recebimento.fornecedor if hasattr(self.recebimento, 'fornecedor') else None,
                    nota_fiscal=self.recebimento.nota_fiscal,
                )
            except Exception as e:
                import logging
                logging.exception(f"Erro ao criar lote para ItemRecebimento: {str(e)}")
                raise ValidationError(f"Erro ao criar lote: {str(e)}")

        super().save(*args, **kwargs)
        # NÃO registra movimento aqui - será registrado apenas quando o recebimento for FINALIZADO
        # Evita entrada falsa no estoque quando item está em PENDENTE/CONFERIDO
    
    def registrar_movimento_estoque(self):
        """
        Registra entrada no estoque e atualiza estoque do produto.
        IMPORTANTE: Deve ser chamado APENAS quando recebimento é FINALIZADO.
        É idempotente - pode ser chamada várias vezes sem duplicar movimentação.
        """
        from estoque.models import MovimentacaoEstoque
        import logging
        
        try:
            # Determina produto e unidade
            if self.item_pedido:
                produto = self.item_pedido.produto
                unidade = self.item_pedido.unidade_medida
            else:
                produto = self.produto
                unidade = self.unidade_medida
            
            # Chave única para evitar duplicatas
            documento_nf = f'NF-e: {self.recebimento.nota_fiscal}'
            
            # VERIFICAÇÃO CRÍTICA DE IDEMPOTÊNCIA: Check if movement already exists
            existe_mov = MovimentacaoEstoque.objects.filter(
                observacao__contains=f"Item Recebimento #{self.id}"
            ).exists()
            
            if existe_mov:
                # Movimentação já foi registrada - retorn early without updating quantities
                logging.info(f"Movimentação já registrada para ItemRecebimento #{self.id}")
                return
            
            # Preço unitário de compra deste item, usado como custo do lote.
            # Ver comentário equivalente em save() sobre priorizar o preço do
            # recebimento e descontar valor_desconto rateado pela quantidade.
            preco_compra = None
            preco_base = self.preco_unitario or (self.item_pedido.preco_unitario if self.item_pedido else None)
            if preco_base:
                desconto = self.valor_desconto or Decimal('0')
                if self.quantidade_recebida:
                    preco_compra = preco_base - (desconto / self.quantidade_recebida)
                else:
                    preco_compra = preco_base

            # Se chegou aqui, é a PRIMEIRA chamada para este item
            # Apenas cria lote se não existir
            if not self.lote:
                from estoque.models import Lote, Armazem
                armazem = None
                if self.local_estoque:
                    armazem = self.local_estoque.armazem
                if not armazem:
                    armazem = Armazem.objects.filter(empresa=self.recebimento.empresa).first()
                if not armazem:
                    raise ValidationError("Nenhum armazém disponível para criar lote.")
                self.lote = Lote.objects.create(
                    empresa=self.recebimento.empresa,
                    produto=produto,
                    armazem=armazem,
                    local_estocagem=self.local_estoque,
                    numero_lote=f"AUTO-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                    quantidade_inicial=self.quantidade_recebida,
                    quantidade_atual=self.quantidade_recebida,
                    data_fabricacao=self.data_fabricacao or timezone.now().date(),
                    data_validade=self.data_validade,
                    status='DISPONIVEL',
                    unidade_medida=unidade,
                    valor_unitario=preco_compra,
                    fornecedor=self.recebimento.fornecedor if hasattr(self.recebimento, 'fornecedor') else None,
                    nota_fiscal=self.recebimento.nota_fiscal,
                )
                ItemRecebimento.objects.filter(pk=self.pk).update(lote=self.lote)
            elif preco_compra is not None and self.lote.valor_unitario is None:
                # Lote já existia sem custo informado (ex.: criado no save() inicial) - preenche agora
                self.lote.valor_unitario = preco_compra
                self.lote.save(update_fields=['valor_unitario', 'valor_total'])

            # Cria a movimentação de estoque
            if self.lote:
                MovimentacaoEstoque.objects.create(
                    empresa=self.recebimento.empresa,
                    lote=self.lote,
                    tipo='ENTRADA',
                    origem='COMPRA',
                    quantidade=self.quantidade_recebida,
                    local_destino=self.local_estoque,
                    documento=documento_nf,
                    observacao=f"Recebimento {self.recebimento.numero} - Item Recebimento #{self.id}" + (f" - Pedido {self.recebimento.pedido.numero}" if self.recebimento.pedido else " - Entrada Direta"),
                    executado_por=self.recebimento.recebido_por,
                    data_movimentacao=self.recebimento.data_recebimento,
                )

            # CORREÇÃO: Atualizar estoque do produto somando APENAS lotes disponíveis
            if produto:
                total_estoque = Decimal('0')
                lotes_disponiveis = produto.lotes.filter(status='DISPONIVEL')
                for lote in lotes_disponiveis:
                    total_estoque += lote.quantidade_atual

                produto.estoque_atual = total_estoque
                produto.save(update_fields=['estoque_atual'])
                logging.info(f"Estoque atualizado para {produto.nome}: {total_estoque}")

                # Atualiza custo médio ponderado do produto com base nos lotes ativos
                produto.recalcular_custo_medio()
                logging.info(f"Custo médio ponderado atualizado para {produto.nome}: {produto.preco_custo}")
                logging.info(f"Movimentação ENTRADA registrada para ItemRecebimento #{self.id}")
        
        except Exception as e:
            logging.exception(f"Erro ao registrar movimento de estoque: {str(e)}")


# ===== TIPOS DE DIVERGÊNCIA =====

class TipoDivergencia(models.Model):
    """
    Tipos de divergência que podem ocorrer no recebimento
    Permite configuração flexível pelo usuário da empresa
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
    
    ativo = models.BooleanField(
        'Ativo',
        default=True,
        help_text='Desative para ocultar em seleções futuras'
    )

    gera_valor_pedido_completo = models.BooleanField(
        'Fornecedor faturou o pedido completo',
        default=False,
        help_text='Marque quando este tipo de divergência significa que o fornecedor '
                   'faturou a quantidade PEDIDA mesmo entregando menos — o financeiro '
                   'deste recebimento deve ser gerado pelo valor do pedido completo, '
                   'não pela quantidade recebida.'
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


# ===== REGISTROS DE DIVERGÊNCIA =====

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
    
    acao_proposta = models.TextField(
        'Ação Proposta',
        blank=True,
        help_text='Ex: Devolução total, devolução parcial, ajuste de preço, etc'
    )
    
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

    resposta_fornecedor = models.TextField(
        'Resposta do Fornecedor',
        blank=True,
        help_text='Justificativa ou resposta do fornecedor sobre esta divergência'
    )

    data_resposta_fornecedor = models.DateTimeField(
        'Data da Resposta do Fornecedor',
        blank=True,
        null=True
    )

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


# ===== AVALIAÇÃO DE FORNECEDOR =====

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
        choices=[(i, f"{i} Estrela(s)") for i in range(1, 6)],
        help_text='Avalie a qualidade do produto entregue'
    )
    
    prazo_entrega = models.IntegerField(
        'Cumprimento de Prazos',
        choices=[(i, f"{i} Estrela(s)") for i in range(1, 6)],
        help_text='Avalie o cumprimento do prazo acordado'
    )
    
    documentacao = models.IntegerField(
        'Documentação/NF-e',
        choices=[(i, f"{i} Estrela(s)") for i in range(1, 6)],
        help_text='Avalie a qualidade da documentação'
    )
    
    atendimento = models.IntegerField(
        'Qualidade do Atendimento',
        choices=[(i, f"{i} Estrela(s)") for i in range(1, 6)],
        help_text='Avalie como foi o atendimento do fornecedor'
    )
    
    preco = models.IntegerField(
        'Relação Preço/Qualidade',
        choices=[(i, f"{i} Estrela(s)") for i in range(1, 6)],
        help_text='Avalie a relação custo-benefício'
    )
    
    nota_media = models.DecimalField(
        'Nota Média',
        max_digits=3,
        decimal_places=2,
        editable=False,
        help_text='Calculada automaticamente (média das 5 categorias)'
    )
    
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
    
    recomenda = models.BooleanField(
        'Recomenda este Fornecedor?',
        default=True
    )
    
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
        # Garantir valores padrão se vazio
        self.qualidade_produto = self.qualidade_produto or 0
        self.prazo_entrega = self.prazo_entrega or 0
        self.documentacao = self.documentacao or 0
        self.atendimento = self.atendimento or 0
        self.preco = self.preco or 0
        
        # Calcular nota média apenas se houver pelo menos uma avaliação
        total = (
            self.qualidade_produto +
            self.prazo_entrega +
            self.documentacao +
            self.atendimento +
            self.preco
        )
        
        if total > 0:
            self.nota_media = total / 5
        else:
            self.nota_media = 0
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Avaliação {self.fornecedor.nome} - {self.recebimento.numero} ({self.nota_media})"


class PedidoCompraMensagem(models.Model):
    """Mensagens de interação entre fornecedor e equipe de compras por pedido."""

    pedido = models.ForeignKey(
        'PedidoCompra',
        on_delete=models.CASCADE,
        related_name='mensagens',
        verbose_name='Pedido'
    )

    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='mensagens_pedido_compra',
        verbose_name='Autor'
    )

    mensagem = models.TextField('Mensagem')

    data_envio = models.DateTimeField(
        'Data de Envio',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Mensagem do Pedido de Compra'
        verbose_name_plural = 'Mensagens dos Pedidos de Compra'
        ordering = ['data_envio']

    def __str__(self):
        return f"{self.pedido.numero} - {self.autor} ({self.data_envio:%d/%m/%Y %H:%M})"


# ============================================================
# PLANEJAMENTO DE COMPRAS DE EMBALAGENS
# ============================================================

class PlanejamentoComprasEmbalagem(models.Model):
    """
    Documento de planejamento anual/safra para compra de embalagens.
    Não é uma requisição nem pedido — é uma previsão de necessidade que
    pode gerar SolicitacaoCompra ou PedidoCompra conforme a safra avança.
    """

    STATUS = [
        ('RASCUNHO', 'Rascunho'),
        ('EM_REVISAO', 'Em Revisão'),
        ('APROVADO', 'Aprovado'),
        ('ENCERRADO', 'Encerrado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='planejamentos_embalagem',
        verbose_name='Empresa',
    )
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planejamentos_embalagem',
        verbose_name='Safra',
    )
    numero = models.CharField(
        'Número',
        max_length=20,
        unique=True,
        editable=False,
    )
    nome = models.CharField('Nome do Planejamento', max_length=200)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='RASCUNHO')
    data_inicio = models.DateField('Início da Safra')
    data_fim = models.DateField('Fim da Safra')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='planejamentos_embalagem_responsavel',
        verbose_name='Responsável',
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Planejamento de Compras de Embalagens'
        verbose_name_plural = 'Planejamentos de Compras de Embalagens'
        ordering = ['-criado_em']

    def save(self, *args, **kwargs):
        if not self.numero:
            from django.db.models import Max
            ultimo = (
                PlanejamentoComprasEmbalagem.objects
                .filter(empresa=self.empresa)
                .aggregate(Max('numero'))['numero__max']
            )
            if ultimo:
                try:
                    seq = int(ultimo.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = 1
            else:
                seq = 1
            self.numero = f'PLAN-EMBAL-{seq:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.numero} — {self.nome}'

    @property
    def custo_estimado_total(self):
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        resultado = self.itens.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantidade_planejada') * F('preco_estimado_unitario'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        from decimal import Decimal
        return resultado['total'] or Decimal('0')

    @property
    def custo_atual_total(self):
        from django.db.models import Sum, F, ExpressionWrapper, DecimalField
        resultado = self.itens.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantidade_planejada') * F('preco_atual_unitario'),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        from decimal import Decimal
        return resultado['total'] or Decimal('0')

    @property
    def variacao_custo_pct(self):
        estimado = self.custo_estimado_total
        atual = self.custo_atual_total
        if estimado and estimado != 0:
            return ((atual - estimado) / estimado) * 100
        return None

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def itens_convertidos(self):
        return self.itens.exclude(status='PLANEJADO').count()


class ItemPlanejamentoEmbalagem(models.Model):
    """
    Linha do planejamento de compras de embalagens.
    Cada linha representa um tipo de embalagem necessária em determinada fase/data da safra.
    """

    FASE_CHOICES = [
        ('GERAL', 'Geral'),
        ('INICIO_SAFRA', 'Início da Safra'),
        ('MEIO_SAFRA', 'Meio da Safra'),
        ('FINAL_SAFRA', 'Final da Safra'),
    ]

    STATUS_ITEM = [
        ('PLANEJADO', 'Planejado'),
        ('SOLICITADO', 'Solicitação Gerada'),
        ('PEDIDO', 'Pedido Gerado'),
        ('RECEBIDO', 'Recebido'),
    ]

    planejamento = models.ForeignKey(
        PlanejamentoComprasEmbalagem,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Planejamento',
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='itens_planejamento_embalagem',
        null=True,
        blank=True,
        verbose_name='Produto',
    )
    tipo_embalagem = models.ForeignKey(
        'embalagem.TipoEmbalagem',
        on_delete=models.PROTECT,
        related_name='itens_planejamento',
        null=True,
        blank=True,
        verbose_name='Tipo de Embalagem',
    )
    fase = models.CharField(
        'Fase da Safra',
        max_length=20,
        choices=FASE_CHOICES,
        default='GERAL',
    )
    data_prevista = models.DateField('Data Prevista de Necessidade')
    quantidade_planejada = models.DecimalField(
        'Quantidade Planejada',
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        verbose_name='Unidade',
    )
    preco_estimado_unitario = models.DecimalField(
        'Preço Estimado (unitário)',
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    preco_atual_unitario = models.DecimalField(
        'Preço Atual (unitário)',
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(0)],
        help_text='Pode ser atualizado durante a safra conforme cotações.',
    )
    fornecedor_preferencial = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_planejamento_preferencial',
        verbose_name='Fornecedor Preferencial',
    )
    fornecedor_alternativo = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_planejamento_alternativo',
        verbose_name='Fornecedor Alternativo',
    )
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_ITEM,
        default='PLANEJADO',
    )
    solicitacao_compra = models.ForeignKey(
        'SolicitacaoCompra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_planejamento_embalagem',
        verbose_name='Solicitação de Compra',
    )
    pedido_compra = models.ForeignKey(
        'PedidoCompra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='itens_planejamento_embalagem',
        verbose_name='Pedido de Compra',
    )
    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Item do Planejamento de Embalagens'
        verbose_name_plural = 'Itens do Planejamento de Embalagens'
        ordering = ['data_prevista', 'fase']

    def __str__(self):
        return f'{self.produto or self.tipo_embalagem} — {self.quantidade_planejada} {self.unidade_medida}'

    def save(self, *args, **kwargs):
        if not self.pk and not self.preco_atual_unitario:
            self.preco_atual_unitario = self.preco_estimado_unitario
        super().save(*args, **kwargs)

    @property
    def custo_estimado(self):
        return self.quantidade_planejada * self.preco_estimado_unitario

    @property
    def custo_atual(self):
        return self.quantidade_planejada * self.preco_atual_unitario

    @property
    def variacao_custo_pct(self):
        if self.preco_estimado_unitario and self.preco_estimado_unitario != 0:
            return ((self.preco_atual_unitario - self.preco_estimado_unitario) / self.preco_estimado_unitario) * 100
        return None


class HistoricoPrecoFornecedor(models.Model):
    """Histórico de preços praticados por fornecedores, alimentado pelo fluxo
    tradicional de cotação (ver adicionar_proposta em compras/views.py)."""
    produto = models.ForeignKey('produtos.Produto', on_delete=models.CASCADE, related_name='historico_precos')
    fornecedor = models.ForeignKey('cadastros.Fornecedor', on_delete=models.CASCADE)

    # Dados do preço
    preco_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    quantidade = models.DecimalField(max_digits=15, decimal_places=3)
    data_cotacao = models.DateField()

    # Origem — cotacao aponta para a extinta Cotação Inteligente (legado);
    # documento_referencia (número da Cotacao tradicional) é o campo em uso.
    cotacao = models.ForeignKey('CotacaoInteligente', on_delete=models.SET_NULL, null=True, blank=True)
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
