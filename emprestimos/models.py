from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class EmprestimoProdutor(models.Model):
    """Controle de saldo de empréstimo por item e produtor."""

    STATUS_CHOICES = [
        ('PROMESSA', 'Promessa de Devolução'),
        ('NORMAL', 'Empréstimo Normal'),
        ('PARCIAL', 'Devolução Parcial'),
        ('DEVOLVIDO', 'Devolvido'),
        ('CANCELADO', 'Cancelado'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='emprestimos_produtor')
    produtor = models.ForeignKey('cadastros.Produtor', on_delete=models.PROTECT, related_name='emprestimos')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='emprestimos_produtor')
    unidade_medida = models.ForeignKey('produtos.UnidadeMedida', on_delete=models.PROTECT, related_name='emprestimos_produtor')
    requisicao = models.ForeignKey('cadastros.Requisicao', on_delete=models.SET_NULL, null=True, blank=True, related_name='emprestimos_gerados')
    requisicao_item = models.ForeignKey('cadastros.RequisicaoItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='emprestimos_gerados')
    direcao = models.CharField('Direção', max_length=30, choices=[
        ('EMPRESA_PARA_PRODUTOR', 'Empresa para Produtor'),
        ('PRODUTOR_PARA_EMPRESA', 'Produtor para Empresa'),
    ], default='EMPRESA_PARA_PRODUTOR')
    data_emprestimo = models.DateTimeField('Data do Empréstimo', default=timezone.now)
    data_promessa_devolucao = models.DateField('Data Promessa de Devolução', null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='NORMAL')
    liberado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emprestimos_liberados',
        verbose_name='Liberado por',
    )
    assinatura_liberador_imagem = models.ImageField(
        'Assinatura Eletrônica do Liberador',
        upload_to='emprestimos/assinaturas/%Y/%m/',
        null=True,
        blank=True,
    )
    assinatura_liberador_nome = models.CharField('Nome do Liberador', max_length=120, blank=True)
    assinatura_liberador_datahora = models.DateTimeField('Data/Hora da Assinatura do Liberador', null=True, blank=True)
    assinatura_produtor_usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emprestimos_assinados_como_produtor',
        verbose_name='Usuário do Portal do Produtor',
    )
    assinatura_produtor_imagem = models.ImageField(
        'Assinatura Eletrônica do Produtor',
        upload_to='emprestimos/assinaturas/%Y/%m/',
        null=True,
        blank=True,
    )
    assinatura_produtor_nome = models.CharField('Nome do Produtor Assinante', max_length=120, blank=True)
    assinatura_produtor_datahora = models.DateTimeField('Data/Hora da Assinatura do Produtor', null=True, blank=True)
    quantidade_emprestada = models.DecimalField('Quantidade Emprestada', max_digits=15, decimal_places=3)
    quantidade_devolvida = models.DecimalField('Quantidade Devolvida', max_digits=15, decimal_places=3, default=0)
    saldo_pendente = models.DecimalField('Saldo Pendente', max_digits=15, decimal_places=3, default=0)
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emprestimos_criados',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)
    aceite_produtor = models.BooleanField('Aceite do Produtor', default=False)
    aceite_produtor_data = models.DateTimeField('Data do Aceite', null=True, blank=True)
    aceite_produtor_usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emprestimos_aceitos_como_produtor',
        verbose_name='Usuário que deu o aceite',
    )
    aceite_editavel = models.BooleanField('Aceite editável (apenas empresa pode reverter)', default=True)

    class Meta:
        db_table = 'cadastros_emprestimoprodutor'
        verbose_name = 'Empréstimo de Produtor'
        verbose_name_plural = 'Empréstimos de Produtores'
        ordering = ['-data_emprestimo']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'produtor']),
            models.Index(fields=['empresa', 'produto']),
            models.Index(fields=['data_promessa_devolucao']),
        ]

    def __str__(self):
        return f"{self.produtor.razao_social} - {self.produto.nome} ({self.saldo_pendente})"

    @property
    def possui_assinatura_liberador(self):
        return bool(self.assinatura_liberador_imagem and self.assinatura_liberador_datahora)

    @property
    def possui_assinatura_produtor(self):
        return bool(self.assinatura_produtor_imagem and self.assinatura_produtor_datahora)

    @property
    def possui_dupla_assinatura(self):
        return self.possui_assinatura_liberador and self.possui_assinatura_produtor

    @property
    def unread_mensagens_interno(self):
        annotated_value = getattr(self, 'unread_mensagens_interno_count', None)
        if annotated_value is not None:
            return annotated_value
        return self.mensagens.filter(perfil_autor='PRODUTOR', lido_interno_em__isnull=True).count()

    @property
    def unread_mensagens_produtor(self):
        annotated_value = getattr(self, 'unread_mensagens_produtor_count', None)
        if annotated_value is not None:
            return annotated_value
        return self.mensagens.filter(perfil_autor='INTERNO', lido_produtor_em__isnull=True).count()

    def clean(self):
        if self.quantidade_devolvida < 0:
            raise ValidationError({'quantidade_devolvida': 'Quantidade devolvida não pode ser negativa.'})
        if self.quantidade_emprestada <= 0:
            raise ValidationError({'quantidade_emprestada': 'Quantidade emprestada deve ser maior que zero.'})

    def atualizar_status_automatico(self, hoje=None):
        hoje = hoje or date.today()
        if self.saldo_pendente <= 0:
            self.status = 'DEVOLVIDO'
            return
        if self.quantidade_devolvida > 0:
            self.status = 'PARCIAL'
            return
        if self.status == 'PROMESSA' and self.data_promessa_devolucao and self.data_promessa_devolucao < hoje:
            self.status = 'NORMAL'

    def save(self, *args, **kwargs):
        self.saldo_pendente = (self.quantidade_emprestada or Decimal('0')) - (self.quantidade_devolvida or Decimal('0'))
        if self.data_promessa_devolucao and self.status == 'NORMAL' and self.saldo_pendente > 0:
            self.status = 'PROMESSA'
        self.atualizar_status_automatico()
        super().save(*args, **kwargs)


class EmprestimoMovimento(models.Model):
    """Timeline estilo extrato bancário para empréstimos/devoluções."""

    TIPO_MOVIMENTO_CHOICES = [
        ('EMPRESTIMO', 'Empréstimo'),
        ('DEVOLUCAO', 'Devolução'),
        ('AJUSTE', 'Ajuste Manual'),
        ('ASSINATURA_LIBERACAO', 'Assinatura de Liberação'),
        ('ASSINATURA_PRODUTOR', 'Assinatura do Produtor'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='movimentos_emprestimo')
    emprestimo = models.ForeignKey(EmprestimoProdutor, on_delete=models.CASCADE, related_name='movimentos')
    tipo_movimento = models.CharField('Tipo de Movimento', max_length=20, choices=TIPO_MOVIMENTO_CHOICES)
    quantidade = models.DecimalField('Quantidade', max_digits=15, decimal_places=3)
    saldo_resultante = models.DecimalField('Saldo Resultante', max_digits=15, decimal_places=3, default=0)
    data_movimento = models.DateTimeField('Data do Movimento', default=timezone.now)
    documento_referencia = models.CharField('Documento Referência', max_length=60, blank=True)
    comprovante = models.FileField(
        'Comprovante da Devolução',
        upload_to='emprestimos/comprovantes/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg'])],
    )
    observacoes = models.TextField('Observações', blank=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimentos_emprestimo_criados',
    )
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_emprestimomovimento'
        verbose_name = 'Movimento de Empréstimo'
        verbose_name_plural = 'Movimentos de Empréstimo'
        ordering = ['-data_movimento', '-id']
        indexes = [
            models.Index(fields=['empresa', 'data_movimento']),
            models.Index(fields=['tipo_movimento']),
        ]

    def __str__(self):
        return f"{self.get_tipo_movimento_display()} - {self.emprestimo.produtor.razao_social}"


class EmprestimoInteracao(models.Model):
    """Log auditável de interações relacionadas ao empréstimo."""

    TIPO_INTERACAO_CHOICES = [
        ('WHATSAPP_SUCESSO', 'WhatsApp enviado'),
        ('WHATSAPP_FALHA', 'Falha no WhatsApp'),
        ('NOTIFICACAO_INTERNA', 'Notificação interna'),
        ('MENSAGEM_INTERNA', 'Mensagem interna'),
        ('MENSAGEM_PRODUTOR', 'Mensagem do produtor'),
        ('DOWNLOAD_ANEXO', 'Download de anexo'),
        ('ALERTA_VISUAL_EXIBIDO', 'Alerta visual exibido'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='interacoes_emprestimo')
    emprestimo = models.ForeignKey(EmprestimoProdutor, on_delete=models.CASCADE, related_name='interacoes')
    tipo_interacao = models.CharField('Tipo de Interação', max_length=30, choices=TIPO_INTERACAO_CHOICES)
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='interacoes_emprestimo',
    )
    descricao = models.TextField('Descrição')
    destinatario = models.CharField('Destinatário', max_length=120, blank=True)
    sucesso = models.BooleanField('Sucesso', default=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_emprestimointeracao'
        verbose_name = 'Interação do Empréstimo'
        verbose_name_plural = 'Interações do Empréstimo'
        ordering = ['-criado_em', '-id']

    def __str__(self):
        return f"{self.emprestimo_id} - {self.get_tipo_interacao_display()}"


class EmprestimoMensagem(models.Model):
    """Conversa auditável entre equipe interna e produtor."""

    PERFIL_AUTOR_CHOICES = [
        ('INTERNO', 'Interno'),
        ('PRODUTOR', 'Produtor'),
    ]

    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='mensagens_emprestimo')
    emprestimo = models.ForeignKey(EmprestimoProdutor, on_delete=models.CASCADE, related_name='mensagens')
    autor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mensagens_emprestimo',
    )
    perfil_autor = models.CharField('Perfil do Autor', max_length=20, choices=PERFIL_AUTOR_CHOICES)
    mensagem = models.TextField('Mensagem')
    lido_interno_em = models.DateTimeField('Lido pelo Interno em', null=True, blank=True)
    lido_produtor_em = models.DateTimeField('Lido pelo Produtor em', null=True, blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_emprestimomensagem'
        verbose_name = 'Mensagem do Empréstimo'
        verbose_name_plural = 'Mensagens do Empréstimo'
        ordering = ['criado_em', 'id']

    def __str__(self):
        return f"{self.emprestimo_id} - {self.perfil_autor}"

    @property
    def foi_lida_pelo_interno(self):
        return bool(self.lido_interno_em)

    @property
    def foi_lida_pelo_produtor(self):
        return bool(self.lido_produtor_em)


class EmprestimoMensagemAnexo(models.Model):
    """Anexos enviados na conversa do empréstimo."""

    mensagem = models.ForeignKey(EmprestimoMensagem, on_delete=models.CASCADE, related_name='anexos')
    arquivo = models.FileField(
        'Arquivo',
        upload_to='emprestimos/mensagens/%Y/%m/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'])],
    )
    nome_original = models.CharField('Nome Original', max_length=255, blank=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        db_table = 'cadastros_emprestimomensagemanexo'
        verbose_name = 'Anexo da Mensagem do Empréstimo'
        verbose_name_plural = 'Anexos das Mensagens do Empréstimo'
        ordering = ['criado_em', 'id']

    def __str__(self):
        import os
        return self.nome_original or os.path.basename(self.arquivo.name)
