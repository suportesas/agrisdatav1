"""
Módulo de Cadastro de Fazendas - ERP Agrícola
Sistema completo com endereços, contatos, bancos e documentos
"""
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import os
from django.core.validators import MaxValueValidator, RegexValidator
import re
import random
import time

# Lista de UFs (inclui 'EX' para Exterior)
UF_CHOICES = [
    ('AC','AC'), ('AL','AL'), ('AP','AP'), ('AM','AM'), ('BA','BA'), ('CE','CE'), ('DF','DF'),
    ('ES','ES'), ('GO','GO'), ('MA','MA'), ('MT','MT'), ('MS','MS'), ('MG','MG'), ('PA','PA'),
    ('PB','PB'), ('PR','PR'), ('PE','PE'), ('PI','PI'), ('RJ','RJ'), ('RN','RN'), ('RS','RS'),
    ('RO','RO'), ('RR','RR'), ('SC','SC'), ('SE','SE'), ('SP','SP'), ('TO','TO'), ('EX','Exterior'),
]

# ============================================
# MANAGERS CUSTOMIZADOS PARA MULTI-TENANCY
# ============================================

class HistoricoFuncionario(models.Model):
    """
    Histórico de recontratações, promoções, mudanças de salário, suspensões, etc.
    """
    TIPO_EVENTO = [
        ("RECONTRATACAO", "Recontratação"),
        ("PROMOCAO", "Promoção"),
        ("MUDANCA_SALARIO", "Mudança de Salário"),
        ("SUSPENSAO", "Suspensão"),
        ("OUTRO", "Outro"),
    ]

    funcionario = models.ForeignKey(
        'Funcionario',
        on_delete=models.CASCADE,
        related_name='historicos',
        verbose_name='Funcionário'
    )
    data_evento = models.DateField('Data do Evento', auto_now_add=True)
    tipo_evento = models.CharField('Tipo de Evento', max_length=30, choices=TIPO_EVENTO)
    funcao = models.ForeignKey(
        'FuncaoFuncionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Função/Cargo'
    )
    salario = models.DecimalField('Salário (R$)', max_digits=10, decimal_places=2, null=True, blank=True)
    motivo = models.TextField('Motivo/Observação', blank=True)
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Usuário Responsável'
    )

    class Meta:
        verbose_name = 'Histórico do Funcionário'
        verbose_name_plural = 'Históricos dos Funcionários'
        ordering = ['-data_evento']

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_evento_display()} ({self.data_evento})"
"""
Módulo de Cadastro de Fazendas - ERP Agrícola
Sistema completo com endereços, contatos, bancos e documentos
"""
from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import os
from django.core.validators import MaxValueValidator, RegexValidator
import re
import random
import time

# Lista de UFs (inclui 'EX' para Exterior)
UF_CHOICES = [
    ('AC','AC'), ('AL','AL'), ('AP','AP'), ('AM','AM'), ('BA','BA'), ('CE','CE'), ('DF','DF'),
    ('ES','ES'), ('GO','GO'), ('MA','MA'), ('MT','MT'), ('MS','MS'), ('MG','MG'), ('PA','PA'),
    ('PB','PB'), ('PR','PR'), ('PE','PE'), ('PI','PI'), ('RJ','RJ'), ('RN','RN'), ('RS','RS'),
    ('RO','RO'), ('RR','RR'), ('SC','SC'), ('SE','SE'), ('SP','SP'), ('TO','TO'), ('EX','Exterior'),
]

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


class AreaManager(models.Manager):
    """Manager customizado para Area com suporte a multi-tenancy"""
    
    def get_queryset(self):
        """Retorna QuerySet customizado"""
        return EmpresaQuerySet(self.model, using=self._db)
    
    def da_empresa(self, empresa):
        """Retorna áreas da empresa"""
        return self.get_queryset().da_empresa(empresa)
    
    def ativos(self):
        """Retorna apenas áreas ativas"""
        return self.get_queryset().ativos()
    
    def disponiveis(self, empresa):
        """Retorna áreas disponíveis para uso"""
        return self.da_empresa(empresa).filter(
            ativo=True,
            status__in=['DISPONIVEL', 'EM_USO']
        )


class TalhaoManager(models.Manager):
    """Manager customizado para Talhao com suporte a multi-tenancy"""
    
    def get_queryset(self):
        """Retorna QuerySet customizado"""
        return EmpresaQuerySet(self.model, using=self._db)
    
    def da_empresa(self, empresa):
        """Retorna talhões da empresa"""
        return self.get_queryset().da_empresa(empresa)
    
    def ativos(self):
        """Retorna apenas talhões ativos"""
        return self.get_queryset().ativos()
    
    def disponiveis_plantio(self, empresa):
        """Retorna talhões prontos para plantio"""
        return self.da_empresa(empresa).filter(
            ativo=True,
            pronto_para_plantio=True,
            status__in=['DISPONIVEL', 'DESCANSO']
        )
    
    def em_cultivo(self, empresa):
        """Retorna talhões com cultivo ativo"""
        return self.da_empresa(empresa).filter(
            ativo=True,
            status='PLANTADO'
        ).exclude(cultura_atual__isnull=True)


# ============================================
# AGORA SUAS CLASSES DE MODELO VÊM AQUI
# (Fazenda, Cultura, Funcionario, etc.)
# ============================================




class Fazenda(models.Model):
    """
    Cadastro principal de Fazendas/Propriedades Rurais
    Suporta cadastro via API (CNPJ) ou manual
    """
    
    TIPO_PESSOA = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]
    
    REGIME_TRIBUTARIO = [
        ('SIMPLES', 'Simples Nacional'),
        ('PRESUMIDO', 'Lucro Presumido'),
        ('REAL', 'Lucro Real'),
        ('MEI', 'Microempreendedor Individual'),
        ('PRODUTOR_RURAL', 'Produtor Rural (Pessoa Física)'),
    ]
    
    # Vinculação multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='fazendas',
        verbose_name='Empresa',
        help_text='Empresa proprietária da fazenda'
    )
    
    # Dados básicos
    nome = models.CharField(
        'Nome da Fazenda',
        max_length=200,
        help_text='Razão social ou nome da propriedade'
    )
    
    nome_fantasia = models.CharField(
        'Nome Fantasia',
        max_length=200,
        blank=True,
        help_text='Nome comercial/popular'
    )
    
    tipo_pessoa = models.CharField(
        'Tipo de Pessoa',
        max_length=2,
        choices=TIPO_PESSOA,
        default='PJ'
    )
    
    # Documentos - ✅ CORREÇÃO: REMOVIDO unique=True
    cnpj_cpf = models.CharField(
        'CNPJ/CPF',
        max_length=18,
        # unique=True,  ❌ REMOVIDO - usa UniqueConstraint por empresa
        help_text='Formato: 00.000.000/0000-00 ou 000.000.000-00'
    )
    
    inscricao_estadual = models.CharField(
        'Inscrição Estadual',
        max_length=20,
        blank=True,
        help_text='IE da propriedade'
    )
    
    inscricao_municipal = models.CharField(
        'Inscrição Municipal',
        max_length=20,
        blank=True
    )
    
    # ✅ NOVOS CAMPOS SOLICITADOS
    eori = models.CharField(
        'Código EORI',
        max_length=20,
        blank=True,
        help_text='Economic Operators Registration and Identification (para exportação)'
    )
    
    regime_tributario = models.CharField(
        'Regime Tributário',
        max_length=20,
        choices=REGIME_TRIBUTARIO,
        default='PRODUTOR_RURAL',
        help_text='Regime de tributação da propriedade'
    )
    
    # Dados da propriedade
    area_total = models.DecimalField(
        'Área Total (hectares)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Área total da propriedade em hectares'
    )
    
    area_agricultavel = models.DecimalField(
        'Área Agricultável (hectares)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Área disponível para plantio'
    )
    
    # Contato principal (telefone e email da fazenda)
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True
    )
    
    email = models.EmailField(
        'E-mail',
        blank=True
    )
    
    website = models.URLField(
        'Website',
        blank=True
    )
    
    # Dados complementares
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Informações adicionais sobre a fazenda'
    )
    
    # Coordenadas geográficas
    latitude = models.DecimalField(
        'Latitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text='Coordenada GPS'
    )
    
    longitude = models.DecimalField(
        'Longitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text='Coordenada GPS'
    )
    
    # Status
    ativa = models.BooleanField(
        'Fazenda Ativa',
        default=True
    )
    
    # Auditoria
    cadastrado_via_api = models.BooleanField(
        'Cadastrado via API',
        default=False,
        help_text='Se foi preenchido automaticamente via API de CNPJ'
    )
    
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
        related_name='fazendas_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Fazenda'
        verbose_name_plural = 'Fazendas'
        ordering = ['nome']
        permissions = [
            ('view_other_fazendas_estoque', 'Pode visualizar estoque de outras fazendas'),
        ]
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['cnpj_cpf']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'cnpj_cpf'],
                name='unique_cnpj_cpf_por_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.nome} - {self.get_cnpj_cpf_formatado()}"
    
    def clean(self):
        """Validações customizadas"""
        # Valida área agricultável
        if self.area_agricultavel and self.area_total:
            if self.area_agricultavel > self.area_total:
                raise ValidationError({
                    'area_agricultavel': 'Área agricultável não pode ser maior que área total'
                })
        
        # ✅ CORRIGIDO: Valida limite de fazendas usando empresa_id
        if not self.pk and self.empresa_id:  # Apenas na criação e se tem empresa_id
            total_fazendas = Fazenda.objects.filter(
                empresa_id=self.empresa_id,
                ativa=True
            ).count()
            
            # Pega limite da empresa
            from empresas.models import Empresa
            try:
                empresa = Empresa.objects.get(pk=self.empresa_id)
                if total_fazendas >= empresa.limite_fazendas:
                    raise ValidationError(
                        f'Limite de fazendas atingido! Seu plano permite apenas '
                        f'{empresa.limite_fazendas} fazenda(s) ativa(s). '
                        f'Faça upgrade do plano para cadastrar mais.'
                    )
            except Empresa.DoesNotExist:
                pass  # Se empresa não existe, deixa passar
    
    def get_cnpj_cpf_formatado(self):
        """Retorna CNPJ/CPF formatado"""
        import re
        doc = re.sub(r'\D', '', self.cnpj_cpf)
        
        if len(doc) == 14:  # CNPJ
            return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        elif len(doc) == 11:  # CPF
            return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
        
        return self.cnpj_cpf
    
    def get_total_talhoes(self):
        """Retorna total de talhões cadastrados"""
        return self.talhoes.count()
    
    def get_area_total_talhoes(self):
        """Retorna soma das áreas dos talhões"""
        from django.db.models import Sum
        total = self.talhoes.aggregate(Sum('area'))['area__sum']
        return total or Decimal('0.00')


class EnderecoFazenda(models.Model):
    recebedor_notify = models.CharField(
        'Destinatário (Notify Party)',
        max_length=255,
        blank=True,
        null=True,
        help_text='Obrigatório apenas para endereço Notify Party'
    )
    # Endereços múltiplos da fazenda. Tipos: Faturamento, Cobrança, Entrega, Notify
    
    TIPO_ENDERECO = [
        ('PRINCIPAL', 'Endereço Principal'),
        ('FATURAMENTO', 'Faturamento'),
        ('COBRANCA', 'Cobrança'),
        ('ENTREGA', 'Entrega'),
        ('NOTIFY', 'Notify Party'),
    ]
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='enderecos',
        verbose_name='Fazenda'
    )
    
    tipo = models.CharField(
        'Tipo de Endereço',
        max_length=20,
        choices=TIPO_ENDERECO,
        default='PRINCIPAL'
    )
    
    # Dados do endereço
    cep = models.CharField(
        'CEP',
        max_length=10,
        help_text='Formato: 00000-000'
    )
    
    logradouro = models.CharField(
        'Logradouro',
        max_length=200,
        help_text='Rua, Avenida, Estrada, etc.'
    )
    
    numero = models.CharField(
        'Número',
        max_length=10,
        blank=True,
        help_text='Deixe vazio para S/N'
    )
    
    complemento = models.CharField(
        'Complemento',
        max_length=100,
        blank=True,
        help_text='Apartamento, Bloco, Sala, etc.'
    )
    
    bairro = models.CharField(
        'Bairro',
        max_length=100
    )
    
    cidade = models.CharField(
        'Cidade',
        max_length=100
    )
    
    uf = models.CharField(
        'UF',
        max_length=2,
        choices=UF_CHOICES,
        help_text='Sigla do estado; use EX para Exterior'
    )
    
    pais = models.CharField(
        'País',
        max_length=50,
        default='Brasil'
    )
    
    # Controle
    padrao = models.BooleanField(
        'Endereço Padrão',
        default=False,
        help_text='Define como endereço principal'
    )
    
    preenchido_via_api = models.BooleanField(
        'Preenchido via API',
        default=False
    )
    
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Endereço da Fazenda'
        verbose_name_plural = 'Endereços das Fazendas'
        ordering = ['-padrao', 'tipo']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cidade}/{self.uf}"
    
    def save(self, *args, **kwargs):
        """Garante que apenas um endereço seja padrão por fazenda"""
        if self.padrao:
            EnderecoFazenda.objects.filter(
                fazenda=self.fazenda,
                padrao=True
            ).update(padrao=False)
        super().save(*args, **kwargs)
    
    def get_endereco_completo(self):
        """Retorna endereço formatado"""
        numero = self.numero or 'S/N'
        complemento = f", {self.complemento}" if self.complemento else ""
        return (
            f"{self.logradouro}, {numero}{complemento} - "
            f"{self.bairro}, {self.cidade}/{self.uf} - CEP: {self.cep}"
        )


class ContatoFazenda(models.Model):
    """
    Contatos da fazenda (múltiplos)
    Gerentes, responsáveis técnicos, administrativo, etc.
    """
    
    TIPO_CONTATO = [
        ('PRINCIPAL', 'Contato Principal'),
        ('FINANCEIRO', 'Financeiro'),
        ('OPERACIONAL', 'Operacional'),
        ('TECNICO', 'Técnico/Agrônomo'),
        ('EMERGENCIA', 'Emergência'),
    ]
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='contatos',
        verbose_name='Fazenda'
    )
    
    tipo = models.CharField(
        'Tipo de Contato',
        max_length=20,
        choices=TIPO_CONTATO,
        default='PRINCIPAL'
    )
    
    # Dados pessoais
    nome = models.CharField(
        'Nome Completo',
        max_length=150
    )
    
    cargo = models.CharField(
        'Cargo/Função',
        max_length=100,
        blank=True,
        help_text='Ex: Gerente, Agrônomo, Contador'
    )
    
    # Contatos
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True,
        help_text='Formato: (00) 0000-0000'
    )
    
    celular = models.CharField(
        'Celular/WhatsApp',
        max_length=20,
        blank=True,
        help_text='Formato: (00) 00000-0000'
    )
    
    email = models.EmailField(
        'E-mail',
        blank=True
    )
    
    whatsapp = models.BooleanField(
        'Tem WhatsApp',
        default=True,
        help_text='Celular é WhatsApp?'
    )
    
    # Controle
    preferencial = models.BooleanField(
        'Contato Preferencial',
        default=False
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Horário de contato, idioma, etc.'
    )
    
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Contato da Fazenda'
        verbose_name_plural = 'Contatos das Fazendas'
        ordering = ['-preferencial', 'tipo', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"


class ContaBancariaFazenda(models.Model):
    """
    Contas bancárias da fazenda
    Inclui dados nacionais e internacionais (SWIFT, IBAN)
    """
    
    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('SALARIO', 'Conta Salário'),
    ]
    
    TIPO_PIX = [
        ('CPF', 'CPF'),
        ('CNPJ', 'CNPJ'),
        ('EMAIL', 'E-mail'),
        ('TELEFONE', 'Telefone'),
        ('CHAVE_ALEATORIA', 'Chave Aleatória'),
    ]
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='contas_bancarias',
        verbose_name='Fazenda'
    )
    
    # Dados bancários nacionais
    banco = models.CharField(
        'Banco',
        max_length=100,
        help_text='Nome do banco'
    )
    
    codigo_banco = models.CharField(
        'Código do Banco',
        max_length=4,
        blank=True,
        help_text='Ex: 001, 033, 104'
    )
    
    agencia = models.CharField(
        'Agência',
        max_length=10,
        help_text='Número da agência (sem dígito)'
    )
    
    agencia_digito = models.CharField(
        'Dígito Agência',
        max_length=2,
        blank=True
    )
    
    conta = models.CharField(
        'Conta',
        max_length=20,
        help_text='Número da conta (sem dígito)'
    )
    
    conta_digito = models.CharField(
        'Dígito Conta',
        max_length=2
    )
    
    tipo_conta = models.CharField(
        'Tipo de Conta',
        max_length=20,
        choices=TIPO_CONTA,
        default='CORRENTE'
    )
    
    # PIX
    pix_habilitado = models.BooleanField(
        'PIX Habilitado',
        default=False
    )
    
    tipo_chave_pix = models.CharField(
        'Tipo de Chave PIX',
        max_length=20,
        choices=TIPO_PIX,
        blank=True
    )
    
    chave_pix = models.CharField(
        'Chave PIX',
        max_length=100,
        blank=True
    )
    
    # Dados internacionais (para exportação)
    swift = models.CharField(
        'Código SWIFT/BIC',
        max_length=11,
        blank=True,
        help_text='Código internacional do banco'
    )
    
    iban = models.CharField(
        'IBAN',
        max_length=34,
        blank=True,
        help_text='International Bank Account Number'
    )
    
    # Informações adicionais
    dados_adicionais = models.TextField(
        'Dados Adicionais',
        blank=True,
        help_text='Informações complementares para transferências internacionais'
    )
    
    # Controle
    conta_principal = models.BooleanField(
        'Conta Principal',
        default=False
    )
    
    ativa = models.BooleanField(
        'Conta Ativa',
        default=True
    )
    
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Conta Bancária'
        verbose_name_plural = 'Contas Bancárias'
        ordering = ['-conta_principal', 'banco']
    
    def __str__(self):
        return f"{self.banco} - Ag: {self.agencia} / Cc: {self.conta}-{self.conta_digito}"
    
    def save(self, *args, **kwargs):
        """Garante que apenas uma conta seja principal por fazenda"""
        if self.conta_principal:
            ContaBancariaFazenda.objects.filter(
                fazenda=self.fazenda,
                conta_principal=True
            ).exclude(pk=self.pk).update(conta_principal=False)
        super().save(*args, **kwargs)


class DocumentoFazenda(models.Model):
    """
    Documentos anexados à fazenda
    Escritura, CAR, ITR, Licenças, Certificados, etc.
    Sistema de alertas de vencimento
    """
    
    TIPO_DOCUMENTO = [
        ('ESCRITURA', 'Escritura'),
        ('CAR', 'CAR (Cadastro Ambiental Rural)'),
        ('ITR', 'ITR (Imposto Territorial Rural)'),
        ('CCIR', 'CCIR (Certificado de Cadastro de Imóvel Rural)'),
        ('LICENCA_AMBIENTAL', 'Licença Ambiental'),
        ('OUTORGA_AGUA', 'Outorga de Água'),
        ('CERTIFICADO_ORGANICO', 'Certificado Orgânico'),
        ('CERTIFICADO_EXPORTACAO', 'Certificado de Exportação'),
        ('ALVARA', 'Alvará'),
        ('CONTRATO', 'Contrato'),
        ('OUTROS', 'Outros'),
    ]
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Fazenda'
    )
    
    tipo = models.CharField(
        'Tipo de Documento',
        max_length=30,
        choices=TIPO_DOCUMENTO
    )
    
    titulo = models.CharField(
        'Título/Descrição',
        max_length=200,
        help_text='Descrição do documento'
    )

    numero_documento = models.CharField(
        'Número do Documento',
        max_length=100,
        blank=True,
        help_text='Número de protocolo, registro, etc.'
    )

    arquivo = models.FileField(
        'Arquivo',
        upload_to='fazendas/documentos/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            )
        ],
        help_text='Formatos: PDF, JPG, PNG, DOC, XLS (máx 10MB)'
    )
    
    # Datas
    data_emissao = models.DateField(
        'Data de Emissão',
        blank=True,
        null=True
    )
    
    data_validade = models.DateField(
        'Data de Validade',
        blank=True,
        null=True,
        help_text='Deixe em branco se não houver validade'
    )
    
    # Controle de alertas
    gerar_alerta_vencimento = models.BooleanField(
        'Gerar Alerta de Vencimento',
        default=True,
        help_text='Notificar quando próximo do vencimento'
    )
    
    dias_antecedencia_alerta = models.IntegerField(
        'Dias de Antecedência para Alerta',
        default=30,
        help_text='Quantos dias antes do vencimento alertar'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    data_upload = models.DateTimeField(
        'Data do Upload',
        auto_now_add=True
    )
    
    enviado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_enviados', verbose_name='Enviado por'
    )

    class Meta:
        verbose_name = 'Documento da Fazenda'
        verbose_name_plural = 'Documentos das Fazendas'
        ordering = ['-data_upload']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"
    
    def esta_vencido(self):
        """Verifica se documento está vencido"""
        if self.data_validade:
            return timezone.now().date() > self.data_validade
        return False
    
    def dias_para_vencimento(self):
        """Retorna dias restantes até vencimento"""
        if self.data_validade:
            dias = (self.data_validade - timezone.now().date()).days
            return dias
        return None
    
    def precisa_alerta(self):
        """Verifica se deve gerar alerta"""
        if not self.gerar_alerta_vencimento or not self.data_validade:
            return False
        
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= self.dias_antecedencia_alerta
        
        return False
    
    def get_nome_arquivo(self):
        """Retorna apenas o nome do arquivo sem o caminho"""
        return os.path.basename(self.arquivo.name)


class DocumentoFornecedor(models.Model):
    """Documentos anexados ao fornecedor (certificados, contratos, licenças)"""

    TIPO_DOCUMENTO = DocumentoFazenda.TIPO_DOCUMENTO

    fornecedor = models.ForeignKey(
        'Fornecedor',
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Fornecedor'
    )

    tipo = models.CharField('Tipo de Documento', max_length=30, choices=TIPO_DOCUMENTO)
    titulo = models.CharField('Título/Descrição', max_length=200, help_text='Descrição do documento')
    numero_documento = models.CharField('Número do Documento', max_length=100, blank=True, help_text='Número de protocolo, registro, etc.')
    numero_documento = models.CharField('Número do Documento', max_length=100, blank=True, help_text='Número de protocolo, registro, etc.')

    arquivo = models.FileField(
        'Arquivo',
        upload_to='fornecedores/documentos/%Y/%m/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx'])
        ],
        help_text='Formatos: PDF, JPG, PNG, DOC, XLS (máx 10MB)'
    )

    data_emissao = models.DateField('Data de Emissão', blank=True, null=True)
    data_validade = models.DateField('Data de Validade', blank=True, null=True, help_text='Deixe em branco se não houver validade')

    gerar_alerta_vencimento = models.BooleanField('Gerar Alerta de Vencimento', default=True)
    dias_antecedencia_alerta = models.IntegerField('Dias de Antecedência para Alerta', default=30)

    observacoes = models.TextField('Observações', blank=True)

    data_upload = models.DateTimeField('Data do Upload', auto_now_add=True)

    enviado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documentos_fornecedor_enviados', verbose_name='Enviado por'
    )

    class Meta:
        verbose_name = 'Documento do Fornecedor'
        verbose_name_plural = 'Documentos dos Fornecedores'
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"

    def esta_vencido(self):
        if self.data_validade:
            return timezone.now().date() > self.data_validade
        return False

    def dias_para_vencimento(self):
        if self.data_validade:
            return (self.data_validade - timezone.now().date()).days
        return None

    def precisa_alerta(self):
        if not self.gerar_alerta_vencimento or not self.data_validade:
            return False
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= self.dias_antecedencia_alerta
        return False

    def get_nome_arquivo(self):
        return os.path.basename(self.arquivo.name)



# ==========================
# MODELOS DE CLIENTES
# ==========================

def _normalize_doc(value):
    """Remove tudo que não for dígito"""
    return re.sub(r"\D", "", (value or ""))


def _generate_fake_cnpj(empresa_id=None):
    """Gera um CNPJ fictício de 14 dígitos único por empresa sempre que possível."""
    # Prefixo 99 para evitar colisão com CNPJs reais
    for _ in range(1000):
        core = ''.join(str(random.randint(0,9)) for _ in range(12))
        candidate = f"99{core}"
        if empresa_id:
            exists = Cliente.objects.filter(empresa_id=empresa_id, cnpj_cpf=candidate).exists()
        else:
            exists = Cliente.objects.filter(cnpj_cpf=candidate).exists()
        if not exists:
            return candidate
    # Fallback usando timestamp para garantir um valor numérico único
    ts = str(int(time.time()*1000))[-12:]
    return f"99{ts}"


class Cliente(models.Model):
    """Cadastro de Clientes multi-tenant"""

    TIPO_CLIENTE = [
        ('NACIONAL', 'Nacional'),
        ('IMPORTADOR', 'Importador'),
    ]

    TIPO_PESSOA = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]

    STATUS = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='clientes', verbose_name='Empresa'
    )

    codigo = models.CharField('Código', max_length=20, blank=True, db_index=True)

    tipo_cliente = models.CharField('Tipo de Cliente', max_length=20, choices=TIPO_CLIENTE, default='NACIONAL')
    tipo_pessoa = models.CharField('Tipo de Pessoa', max_length=2, choices=TIPO_PESSOA, default='PJ')

    razao_social = models.CharField('Razão Social / Nome', max_length=250)
    nome_comercial = models.CharField('Nome Comercial', max_length=250, blank=True, null=True)

    cnpj_cpf = models.CharField('CNPJ/CPF', max_length=18, blank=True, null=True, help_text='Apenas números ou formato usual (Opcional para IMPORTADOR)')

    status = models.CharField('Status', max_length=10, choices=STATUS, default='ATIVO')

    # Documentação fiscal
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=30, blank=True, null=True)
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=30, blank=True, null=True)
    eori = models.CharField('EORI', max_length=30, blank=True, null=True)
    vat = models.CharField('VAT/Número Registro', max_length=50, blank=True, null=True, help_text='Número de registro do cliente no exterior (VAT)')
    regime_tributario = models.CharField('Regime Tributário', max_length=50, blank=True, null=True)

    contribuinte_icms = models.BooleanField('Contribuinte ICMS', default=False)
    indicador_ie = models.CharField('Indicador IE', max_length=1, blank=True, null=True, help_text='1,2 ou 9')
    inscricao_suframa = models.CharField('Inscrição SUFRAMA', max_length=50, blank=True, null=True)

    # Comerciais
    limite_credito = models.DecimalField('Limite de Crédito', max_digits=14, decimal_places=2, default=0, blank=True, null=True)
    prazo_pagamento = models.IntegerField('Prazo de Pagamento (dias)', null=True, blank=True)
    # Link para prazos de pagamento predefinidos (ex.: 30,60,90)
    prazo_pagamento_padrao = models.ForeignKey('PrazoPagamentoPadrao', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')

    FORMA_PGTO = [
        ('BOLETO','Boleto'),('PIX','PIX'),('TRANSFERENCIA','Transferência'),('CARTAO','Cartão'),('CREDITO','Crédito'),('INVOICE','Invoice'),('OUTRO','Outro')
    ]
    forma_pagamento_padrao = models.CharField('Forma de Pagamento Padrão', max_length=20, choices=FORMA_PGTO, blank=True, null=True)
    desconto_padrao = models.DecimalField('Desconto Padrão (%)', max_digits=5, decimal_places=2, default=0, blank=True, null=True)

    vendedor_responsavel = models.ForeignKey('cadastros.Vendedor', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')
    observacoes_comerciais = models.TextField('Observações Comerciais', blank=True, null=True)

    # Exportação / Importador
    pais = models.CharField('País', max_length=100, blank=True, default='Brasil')
    moeda_padrao = models.CharField('Moeda Padrão', max_length=10, blank=True, null=True)
    porto_destino = models.ForeignKey('cadastros.Porto', on_delete=models.SET_NULL, null=True, blank=True)
    incoterm_padrao = models.CharField('Incoterm', max_length=20, blank=True, null=True)
    idioma_preferido = models.CharField('Idioma Preferido', max_length=20, blank=True, null=True)
    certificacoes_exigidas = models.TextField('Certificações Exigidas', blank=True, null=True)


    # Contato principal (simplificado)
    contato_principal_nome = models.CharField('Contato Principal', max_length=150, blank=True, null=True)
    contato_principal_telefone = models.CharField('Telefone Contato', max_length=30, blank=True, null=True)
    contato_principal_email = models.EmailField('E-mail Contato', blank=True, null=True)

    # Portal
    acesso_portal = models.BooleanField('Acesso ao Portal', default=False)
    usuario_vinculado = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='cliente_vinculado')

    # Auditoria
    cadastrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_cadastrados')
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['-data_cadastro']
        constraints = [
            models.UniqueConstraint(fields=['empresa','cnpj_cpf'], name='unique_cnpj_cpf_por_empresa_cliente')
        ]
        indexes = [models.Index(fields=['empresa', 'codigo']), models.Index(fields=['cnpj_cpf'])]

    def __str__(self):
        return f"{self.codigo or ''} {self.razao_social}"

    def clean(self):
        """Validações de negócio - mais tolerante para importadores e com avisos anexados."""
        # Normaliza documento
        doc = _normalize_doc(self.cnpj_cpf)
        if not doc:
            # Permite importador sem CNPJ (será gerado no save)
            if self.tipo_cliente != 'IMPORTADOR':
                raise ValidationError({'cnpj_cpf': 'CNPJ/CPF é obrigatório para clientes nacionais'})
        else:
            if len(doc) not in (11, 14):
                raise ValidationError({'cnpj_cpf': 'CNPJ/CPF inválido. Deve ter 11 (CPF) ou 14 (CNPJ) dígitos.'})
            # Atualiza campo para forma normalizada (apenas dígitos)
            self.cnpj_cpf = doc

        # Indicador IE e inscrição estadual
        if self.contribuinte_icms:
            if not self.inscricao_estadual:
                raise ValidationError({'inscricao_estadual': 'Inscrição Estadual é obrigatória para contribuinte ICMS'})
            self.indicador_ie = '1'
        else:
            if self.tipo_pessoa == 'PF':
                self.indicador_ie = '9'
            else:
                self.indicador_ie = '2'

        # =========================
        # Importador: flexibilidade
        # =========================
        importer_warnings = []
        if self.tipo_cliente == 'IMPORTADOR':
            # Define país padrão se não informado
            if not self.pais or not self.pais.strip():
                self.pais = 'Não informado'

            if not self.eori:
                importer_warnings.append('EORI não informado')
            if not self.porto_destino:
                importer_warnings.append('Porto de destino não selecionado')
            if not (self.vat or '').strip():
                importer_warnings.append('VAT não informado')

            # Se houver avisos e não houver observações, anexa-os (append para não sobrescrever)
            if importer_warnings:
                note = 'Avisos importador: ' + '; '.join(importer_warnings)
                if self.observacoes_comerciais:
                    self.observacoes_comerciais = (self.observacoes_comerciais.rstrip() + '\n' + note) if note not in self.observacoes_comerciais else self.observacoes_comerciais
                else:
                    self.observacoes_comerciais = note

        # ============================================================
        # Validação de Inscrição Estadual por UF (ignora para exterior)
        # ============================================================
        from .validators import validate_inscricao_estadual
        uf = None

        # Se cliente for do exterior, força UF = 'EX' para pular validações estaduais
        if self.pais and self.pais.strip().lower() not in ['brasil', '', 'não informado']:
            uf = 'EX'
        else:
            try:
                endereco_padrao = self.enderecos.filter(padrao=True).first() if hasattr(self, 'enderecos') else None
                if endereco_padrao:
                    uf = endereco_padrao.uf
            except Exception:
                uf = None

        if self.contribuinte_icms and uf != 'EX' and self.inscricao_estadual:
            try:
                validate_inscricao_estadual(
                    self.inscricao_estadual,
                    uf=uf,
                    is_contribuinte=self.contribuinte_icms,
                    tipo_pessoa=self.tipo_pessoa,
                )
            except ValidationError as e:
                msg = e.messages[0] if getattr(e, 'messages', None) else str(e)
                raise ValidationError({'inscricao_estadual': msg})

    def save(self, *args, **kwargs):
        # Normaliza cnpj_cpf para dígitos
        self.cnpj_cpf = _normalize_doc(self.cnpj_cpf)

        # Para importador sem CNPJ informado, gera um CNPJ fictício único
        if self.tipo_cliente == 'IMPORTADOR' and not self.cnpj_cpf:
            empresa_id = getattr(self, 'empresa_id', None)
            self.cnpj_cpf = _generate_fake_cnpj(empresa_id)

        # Garantir que o indicador_ie reflita a regra do NF-e
        if self.contribuinte_icms:
            # Contribuinte ICMS: obriga IE e indicador = '1'
            self.indicador_ie = '1'
        else:
            # Não contribuinte: PF -> 9, PJ -> 2
            self.indicador_ie = '9' if self.tipo_pessoa == 'PF' else '2'

        # Execute validações de modelo antes de salvar para evitar inconsistências
        # (por exemplo, exigir inscrição estadual para contribuintes)
        self.full_clean()

        # Gera código sequencial por empresa se não existir
        if not self.codigo:
            prefix = 'CLI'
            # Use empresa_id to avoid accessing related object which may be missing
            empresa_id = getattr(self, 'empresa_id', None)
            if empresa_id:
                last = Cliente.objects.filter(empresa_id=empresa_id).order_by('-id').first()
                if last and last.codigo and last.codigo.startswith(prefix):
                    try:
                        num = int(last.codigo.split('-')[-1])
                    except Exception:
                        num = Cliente.objects.filter(empresa_id=empresa_id).count()
                else:
                    num = Cliente.objects.filter(empresa_id=empresa_id).count()
            else:
                # Fallback to global count if no empresa present
                last = Cliente.objects.order_by('-id').first()
                if last and last.codigo and last.codigo.startswith(prefix):
                    try:
                        num = int(last.codigo.split('-')[-1])
                    except Exception:
                        num = Cliente.objects.count()
                else:
                    num = Cliente.objects.count()
            self.codigo = f"{prefix}-{(num+1):05d}"

        super().save(*args, **kwargs)

    def get_cnpj_cpf_formatado(self):
        """Formata CNPJ/CPF do cliente para exibição"""
        import re
        if not self.cnpj_cpf:
            return ''
        doc = re.sub(r'\D', '', (self.cnpj_cpf or ''))
        if len(doc) == 14:  # CNPJ
            return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        elif len(doc) == 11:  # CPF
            return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
        return self.cnpj_cpf or ''


class Moeda(models.Model):
    """Lista de moedas que podem ser gerenciadas via admin."""
    codigo = models.CharField(
        'Código', 
        max_length=4, 
        unique=True, 
        help_text='Ex: BRL, USD, EUR'
    )
    nome = models.CharField(
        'Nome', 
        max_length=50, 
        help_text='Nome completo da moeda'
    )
    simbolo = models.CharField(
        'Símbolo',
        max_length=5,
        blank=True,
        help_text='Ex: R$, $, €, £, ¥'
    )
    pais = models.CharField(
        'País',
        max_length=100,
        blank=True,
        help_text='País ou região de origem'
    )
    taxa_cambio = models.DecimalField(
        'Taxa de Câmbio (em BRL)',
        max_digits=10,
        decimal_places=4,
        default=1,
        help_text='Conversão para Real Brasileiro (1 unidade = X BRL)'
    )
    ativo = models.BooleanField(
        'Ativo',
        default=True,
        help_text='Moeda disponível para usar'
    )
    data_criacao = models.DateTimeField(
        'Data de Criação',
        null=True,
        blank=True
    )
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Moeda'
        verbose_name_plural = 'Moedas'
        ordering = ['codigo']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['ativo']),
        ]

    def __str__(self):
        simbolo_str = f" {self.simbolo}" if self.simbolo else ""
        return f"{self.nome} ({self.codigo}){simbolo_str}"
    
    def converter_para_brl(self, valor):
        """Converte valor da moeda para BRL"""
        from decimal import Decimal
        if isinstance(valor, (int, float)):
            valor = Decimal(str(valor))
        return valor * self.taxa_cambio
    
    def converter_de_brl(self, valor_brl):
        """Converte valor em BRL para esta moeda"""
        from decimal import Decimal
        if self.taxa_cambio == 0:
            return Decimal('0')
        if isinstance(valor_brl, (int, float)):
            valor_brl = Decimal(str(valor_brl))
        return valor_brl / self.taxa_cambio


class NCM(models.Model):
    """Nomenclatura Comum do Mercosul (NCM) usada para emissão de NF-e

    Este modelo funciona como fonte mestre (templates). Empresas terão cópias
    individuais no modelo `EmpresaNCM` para permitir customizações por empresa
    sem afetar outras empresas (SaaS multi-tenant behavior).
    """
    codigo = models.CharField('Código NCM', max_length=8, unique=True, help_text='8 dígitos numéricos')
    nome = models.CharField('Descrição', max_length=500)
    descricao = models.TextField('Observações', blank=True)
    cest = models.CharField('CEST', max_length=10, blank=True, help_text='CEST (se aplicável)')
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Data de criação', auto_now_add=True)
    atualizado_em = models.DateTimeField('Última atualização', auto_now=True)

    class Meta:
        verbose_name = 'NCM'
        verbose_name_plural = 'NCMs'
        ordering = ['codigo']
        indexes = [models.Index(fields=['codigo'])]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"

    def clean(self):
        # Normaliza e valida código
        self.codigo = re.sub(r'\D','', (self.codigo or ''))
        if len(self.codigo) != 8:
            raise ValidationError({'codigo': 'Código NCM inválido. Deve conter 8 dígitos.'})


class EmpresaNCM(models.Model):
    """NCM específico de cada empresa. Cópia da tabela mestre para customização por empresa."""
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='ncms')
    codigo = models.CharField('Código NCM', max_length=8, help_text='8 dígitos numéricos')
    nome = models.CharField('Descrição', max_length=255)
    descricao = models.TextField('Observações', blank=True)
    cest = models.CharField('CEST', max_length=10, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    template = models.ForeignKey(NCM, on_delete=models.SET_NULL, null=True, blank=True, help_text='Referência ao template global (opcional)')
    criado_em = models.DateTimeField('Data de criação', auto_now_add=True)
    atualizado_em = models.DateTimeField('Última atualização', auto_now=True)

    class Meta:
        verbose_name = 'NCM da Empresa'
        verbose_name_plural = 'NCMs das Empresas'
        ordering = ['codigo']
        constraints = [
            models.UniqueConstraint(fields=['empresa','codigo'], name='unique_ncm_per_empresa')
        ]
        indexes = [models.Index(fields=['empresa','codigo'])]

    def __str__(self):
        return f"{self.codigo} - {self.nome} ({self.empresa})"

    def clean(self):
        self.codigo = re.sub(r'\D','', (self.codigo or ''))
        if len(self.codigo) != 8:
            raise ValidationError({'codigo': 'Código NCM inválido. Deve conter 8 dígitos.'})


class CFOP(models.Model):
    """CFOP - Código Fiscal de Operações e Prestações"""
    codigo = models.CharField('Código CFOP', max_length=4, unique=True, help_text='Código CFOP (p. ex. 5102)')
    nome = models.CharField('Descrição', max_length=255)
    descricao = models.TextField('Observações', blank=True)
    natureza_operacao = models.ForeignKey('produtos.NaturezaOperacao', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Natureza da Operação', help_text='Natureza da Operação vinculada a este CFOP')
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField('Data de criação', auto_now_add=True)
    atualizado_em = models.DateTimeField('Última atualização', auto_now=True)

    class Meta:
        verbose_name = 'CFOP'
        verbose_name_plural = 'CFOPs'
        ordering = ['codigo']
        indexes = [models.Index(fields=['codigo'])]

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class EmpresaCFOP(models.Model):
    """CFOP específico de cada empresa. Cópia da tabela mestre para customização por empresa."""
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='cfops')
    codigo = models.CharField('Código CFOP', max_length=4, help_text='Código CFOP (p. ex. 5102)')
    nome = models.CharField('Descrição', max_length=255)
    descricao = models.TextField('Observações', blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    template = models.ForeignKey(CFOP, on_delete=models.SET_NULL, null=True, blank=True, help_text='Referência ao template global (opcional)')
    criado_em = models.DateTimeField('Data de criação', auto_now_add=True)
    atualizado_em = models.DateTimeField('Última atualização', auto_now=True)

    class Meta:
        verbose_name = 'CFOP da Empresa'
        verbose_name_plural = 'CFOPs das Empresas'
        ordering = ['codigo']
        constraints = [
            models.UniqueConstraint(fields=['empresa','codigo'], name='unique_cfop_per_empresa')
        ]
        indexes = [models.Index(fields=['empresa','codigo'])]

    def __str__(self):
        return f"{self.codigo} - {self.nome} ({self.empresa})"

    def clean(self):
        self.codigo = re.sub(r'\D','', (self.codigo or ''))
        if not (2 <= len(self.codigo) <= 4):
            raise ValidationError({'codigo': 'Código CFOP inválido. Deve conter 2 a 4 dígitos.'})


class EnderecoCliente(models.Model):
    TIPO_ENDERECO = [
        ('PRINCIPAL','Principal'),('FATURAMENTO','Faturamento'),('COBRANCA','Cobrança'),('ENTREGA','Entrega'),('NOTIFY','Notify')
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='enderecos')
    tipo = models.CharField('Tipo Endereço', max_length=20, choices=TIPO_ENDERECO, default='PRINCIPAL')
    cep = models.CharField('CEP', max_length=10)
    logradouro = models.CharField('Logradouro', max_length=200)
    numero = models.CharField('Número', max_length=20, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    uf = models.CharField('UF', max_length=2)
    pais = models.CharField('País', max_length=100, default='Brasil')
    recebedor_notify = models.CharField('Recebedor Notify', max_length=150, blank=True)
    padrao = models.BooleanField('Endereço Padrão', default=False)

    class Meta:
        verbose_name = 'Endereço do Cliente'
        verbose_name_plural = 'Endereços dos Clientes'
        ordering = ['-padrao']

    def save(self, *args, **kwargs):
        if self.padrao:
            EnderecoCliente.objects.filter(cliente=self.cliente, padrao=True).exclude(pk=self.pk).update(padrao=False)
        # recebedor_notify só se tipo=NOTIFY
        if self.tipo != 'NOTIFY':
            self.recebedor_notify = ''
        super().save(*args, **kwargs)

    def get_endereco_completo(self):
        """Retorna endereço formatado para exibição em listas e detalhes"""
        numero = self.numero or 'S/N'
        complemento = f", {self.complemento}" if self.complemento else ""
        return (
            f"{self.logradouro}, {numero}{complemento} - "
            f"{self.bairro}, {self.cidade}/{self.uf} - CEP: {self.cep}"
        )

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cidade}/{self.uf}"


class ContatoCliente(models.Model):
    """Contatos do Cliente (múltiplos). Replica campos do Fornecedor para consistência."""

    TIPO_CONTATO = [
        ('PRINCIPAL', 'Contato Principal'),
        ('FINANCEIRO', 'Financeiro'),
        ('OPERACIONAL', 'Operacional'),
        ('TECNICO', 'Técnico'),
        ('EMERGENCIA', 'Emergência'),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contatos')
    tipo = models.CharField('Tipo de Contato', max_length=20, choices=TIPO_CONTATO, default='PRINCIPAL')
    nome = models.CharField('Nome', max_length=150)
    cargo = models.CharField('Cargo', max_length=100, blank=True)
    telefone = models.CharField('Telefone', max_length=30, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=30, blank=True)
    email = models.EmailField('Email', blank=True)

    whatsapp = models.BooleanField('WhatsApp', default=False)
    preferencial = models.BooleanField('Contato Preferencial', default=False)

    observacoes = models.TextField('Observações', blank=True)

    class Meta:
        verbose_name = 'Contato do Cliente'
        verbose_name_plural = 'Contatos dos Clientes'
        ordering = ['-preferencial', 'tipo', 'nome']

    def save(self, *args, **kwargs):
        if self.preferencial:
            ContatoCliente.objects.filter(cliente=self.cliente, preferencial=True).exclude(pk=self.pk).update(preferencial=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} - {self.cliente}"

class ContaBancariaCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contas_bancarias')
    banco = models.CharField('Banco', max_length=100)
    codigo_banco = models.CharField('Código do Banco', max_length=4, blank=True)
    agencia = models.CharField('Agência', max_length=20, blank=True)
    agencia_digito = models.CharField('Dígito Agência', max_length=5, blank=True)
    conta = models.CharField('Conta', max_length=20, blank=True)
    conta_digito = models.CharField('Dígito', max_length=5, blank=True)

    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Conta Poupança'),
        ('SALARIO', 'Conta Salário'),
    ]
    tipo_conta = models.CharField('Tipo de Conta', max_length=20, choices=TIPO_CONTA, blank=True)

    pix_habilitado = models.BooleanField('PIX Habilitado', default=False)
    TIPO_PIX = [
        ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('EMAIL', 'E-mail'), ('TELEFONE', 'Telefone'), ('CHAVE_ALEATORIA', 'Chave Aleatória')
    ]
    tipo_chave_pix = models.CharField('Tipo de Chave PIX', max_length=20, choices=TIPO_PIX, blank=True)
    chave_pix = models.CharField('Chave PIX', max_length=100, blank=True)

    swift = models.CharField('SWIFT', max_length=20, blank=True)
    iban = models.CharField('IBAN', max_length=34, blank=True)
    dados_adicionais = models.TextField('Dados Adicionais', blank=True)

    conta_principal = models.BooleanField('Conta Principal', default=False)
    ativa = models.BooleanField('Conta Ativa', default=True)

    class Meta:
        verbose_name = 'Conta Bancária do Cliente'
        verbose_name_plural = 'Contas Bancárias dos Clientes'
        ordering = ['-conta_principal']

    def save(self, *args, **kwargs):
        if self.conta_principal:
            ContaBancariaCliente.objects.filter(cliente=self.cliente, conta_principal=True).exclude(pk=self.pk).update(conta_principal=False)
        super().save(*args, **kwargs)

class PrazoPagamentoPadrao(models.Model):
    """Presets de prazos de pagamento por empresa. `termos` armazena coma-separado, ex: '30,60,90'"""
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='prazos_pagamento')
    nome = models.CharField('Nome', max_length=100)
    termos = models.CharField('Termos (dias)', max_length=200, help_text="Valores separados por vírgula, ex: '30,60,90'")
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Prazo de Pagamento Padrão'
        verbose_name_plural = 'Prazos de Pagamento Padrões'
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} - {self.termos}"

    def get_termos_list(self):
        """Retorna lista de inteiros dos termos"""
        return [int(x) for x in self.termos.split(',') if x.strip().isdigit()]


class DocumentoCliente(models.Model):
    TIPO_DOCUMENTO = DocumentoFazenda.TIPO_DOCUMENTO

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField('Tipo de Documento', max_length=30, choices=TIPO_DOCUMENTO)
    titulo = models.CharField('Título/Descrição', max_length=200)
    numero_documento = models.CharField('Número do Documento', max_length=100, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='clientes/documentos/%Y/%m/', validators=[FileExtensionValidator(allowed_extensions=['pdf','jpg','jpeg','png','doc','docx','xls','xlsx'])])
    data_emissao = models.DateField('Data de Emissão', blank=True, null=True)
    data_validade = models.DateField('Data de Validade', blank=True, null=True)

    gerar_alerta_vencimento = models.BooleanField('Gerar Alerta de Vencimento', default=True)
    dias_antecedencia_alerta = models.IntegerField('Dias de Antecedência', default=30)

    observacoes = models.TextField('Observações', blank=True)
    data_upload = models.DateTimeField('Data do Upload', auto_now_add=True)
    enviado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_cliente_enviados')

    class Meta:
        verbose_name = 'Documento do Cliente'
        verbose_name_plural = 'Documentos dos Clientes'
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"

    def esta_vencido(self):
        """Verifica se documento está vencido"""
        if self.data_validade:
            return timezone.now().date() > self.data_validade
        return False

    def dias_para_vencimento(self):
        """Retorna dias restantes até vencimento"""
        if self.data_validade:
            return (self.data_validade - timezone.now().date()).days
        return None

    def precisa_alerta(self):
        """Verifica se deve gerar alerta"""
        if not self.gerar_alerta_vencimento or not self.data_validade:
            return False
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= self.dias_antecedencia_alerta
        return False

    def get_nome_arquivo(self):
        """Retorna apenas o nome do arquivo sem o caminho"""
        return os.path.basename(self.arquivo.name)


class FuncaoFuncionario(models.Model):
    """
    Funções/Cargos dos funcionários
    Ex: Tratorista, Colhedor, Supervisor, etc.
    """
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='funcoes_funcionarios',
        verbose_name='Empresa'
    )
    
    nome = models.CharField(
        'Nome da Função',
        max_length=100,
        help_text='Ex: Tratorista, Colhedor, Supervisor'
    )
    
    descricao = models.TextField(
        'Descrição',
        blank=True,
        help_text='Descrição das atividades da função'
    )
    
    salario_base = models.DecimalField(
        'Salário Base (R$)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Salário base sugerido para a função'
    )
    
    ativa = models.BooleanField(
        'Função Ativa',
        default=True
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Função de Funcionário'
        verbose_name_plural = 'Funções de Funcionários'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome'],
                name='unique_funcao_por_empresa'
            )
        ]
    
    def __str__(self):
        return self.nome
    
    def get_total_funcionarios(self):
        """Retorna total de funcionários nesta função"""
        return self.funcionarios.filter(ativo=True).count()

class Funcionario(models.Model):
    def get_qtd_suspensoes(self):
        """Retorna o número de suspensões registradas para o funcionário"""
        return self.afastamentos.filter(tipo_afastamento='SUSPENSAO').count() + self.historicos.filter(tipo_evento='SUSPENSAO').count()
    """
    Cadastro de Funcionários da fazenda
    """
    
    TIPO_CONTRATO = [
        ('CLT', 'CLT'),
        ('TEMPORARIO', 'Temporário'),
        ('DIARISTA', 'Diarista'),
        ('AUTONOMO', 'Autônomo'),
        ('TERCEIRIZADO', 'Terceirizado'),
    ]
    
    ESTADO_CIVIL = [
        ('SOLTEIRO', 'Solteiro(a)'),
        ('CASADO', 'Casado(a)'),
        ('DIVORCIADO', 'Divorciado(a)'),
        ('VIUVO', 'Viúvo(a)'),
        ('UNIAO_ESTAVEL', 'União Estável'),
    ]
    
    GENERO = [
        ('M', 'Masculino'),
        ('F', 'Feminino'),
        ('OUTRO', 'Outro'),
    ]
    
    ESCOLARIDADE = [
        ('ANALFABETO', 'Analfabeto'),
        ('FUNDAMENTAL_INCOMPLETO', 'Fundamental Incompleto'),
        ('FUNDAMENTAL_COMPLETO', 'Fundamental Completo'),
        ('MEDIO_INCOMPLETO', 'Ensino Médio Incompleto'),
        ('MEDIO_COMPLETO', 'Ensino Médio Completo'),
        ('TECNICO', 'Ensino Técnico'),
        ('SUPERIOR_INCOMPLETO', 'Superior Incompleto'),
        ('SUPERIOR_COMPLETO', 'Superior Completo'),
        ('POS_GRADUACAO', 'Pós-Graduação'),
    ]
    
    # Empresa e Fazenda
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='funcionarios',
        verbose_name='Empresa'
    )
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionarios',
        verbose_name='Fazenda',
        help_text='Fazenda principal onde trabalha'
    )
    
    # Dados Pessoais
    nome_completo = models.CharField(
        'Nome Completo',
        max_length=200
    )
    
    cpf = models.CharField(
        'CPF',
        max_length=14,
        unique=True,
        help_text='Formato: 000.000.000-00'
    )
    
    rg = models.CharField(
        'RG',
        max_length=20,
        blank=True
    )
    
    data_nascimento = models.DateField(
        'Data de Nascimento',
        blank=True,
        null=True
    )
    
    genero = models.CharField(
        'Gênero',
        max_length=10,
        choices=GENERO,
        blank=True
    )
    
    estado_civil = models.CharField(
        'Estado Civil',
        max_length=20,
        choices=ESTADO_CIVIL,
        blank=True
    )
    
    # Contato
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True
    )
    
    celular = models.CharField(
        'Celular',
        max_length=20,
        blank=True
    )
    
    email = models.EmailField(
        'E-mail',
        blank=True
    )
    
    # Endereço
    cep = models.CharField(
        'CEP',
        max_length=9,
        blank=True
    )
    
    endereco = models.CharField(
        'Endereço',
        max_length=200,
        blank=True
    )
    
    numero = models.CharField(
        'Número',
        max_length=10,
        blank=True
    )
    
    complemento = models.CharField(
        'Complemento',
        max_length=100,
        blank=True
    )
    
    bairro = models.CharField(
        'Bairro',
        max_length=100,
        blank=True
    )
    
    cidade = models.CharField(
        'Cidade',
        max_length=100,
        blank=True
    )
    
    uf = models.CharField(
        'UF',
        max_length=2,
        blank=True
    )
    
    # Dados Profissionais
    funcao = models.ForeignKey(
        FuncaoFuncionario,
        on_delete=models.PROTECT,
        related_name='funcionarios',
        verbose_name='Função/Cargo'
    )
    
    tipo_contrato = models.CharField(
        'Tipo de Contrato',
        max_length=20,
        choices=TIPO_CONTRATO,
        default='CLT'
    )
    
    data_admissao = models.DateField(
        'Data de Admissão',
        blank=True,
        null=True
        
    )
    
    data_demissao = models.DateField(
        'Data de Demissão',
        blank=True,
        null=True
    )
    
    salario = models.DecimalField(
        'Salário (R$)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Documentos Trabalhistas
    ctps = models.CharField(
        'CTPS',
        max_length=20,
        blank=True,
        help_text='Carteira de Trabalho'
    )
    
    pis = models.CharField(
        'PIS/PASEP',
        max_length=20,
        blank=True
    )

    # Habilitação (CNH)
    cnh = models.CharField('CNH', max_length=20, blank=True)
    cnh_validade = models.DateField('Validade CNH', null=True, blank=True)

    # Educação e Profissionais
    escolaridade = models.CharField(
        'Escolaridade',
        max_length=30,
        choices=ESCOLARIDADE,
        blank=True,
        help_text='Nível de escolaridade do funcionário'
    )
    
    numero_crea = models.CharField(
        'Número CREA',
        max_length=50,
        blank=True,
        help_text='Número de registro no Conselho Regional de Engenharia e Agronomia'
    )

    # Dados Bancários
    banco = models.CharField(
        'Banco',
        max_length=100,
        blank=True
    )
    
    agencia = models.CharField(
        'Agência',
        max_length=10,
        blank=True
    )
    
    conta = models.CharField(
        'Conta',
        max_length=20,
        blank=True
    )

    # PIX
    pix_habilitado = models.BooleanField('PIX Habilitado', default=False)
    TIPO_PIX = [
        ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('EMAIL', 'E-mail'), ('TELEFONE', 'Telefone'), ('CHAVE_ALEATORIA', 'Chave Aleatória')
    ]
    tipo_chave_pix = models.CharField('Tipo de Chave PIX', max_length=20, choices=TIPO_PIX, blank=True)
    chave_pix = models.CharField('Chave PIX', max_length=100, blank=True)

    # Tipo de conta bancária (adicionado para cadastro de funcionário)
    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Conta Poupança'),
        ('SALARIO', 'Conta Salário'),
    ]
    tipo_conta = models.CharField(
        'Tipo de Conta',
        max_length=20,
        choices=TIPO_CONTA,
        blank=True
    )
    
    # Contato de Emergência
    contato_emergencia_nome = models.CharField(
        'Nome Contato Emergência',
        max_length=200,
        blank=True
    )
    
    contato_emergencia_telefone = models.CharField(
        'Telefone Emergência',
        max_length=20,
        blank=True
    )
    
    contato_emergencia_parentesco = models.CharField(
        'Parentesco',
        max_length=50,
        blank=True,
        help_text='Ex: Mãe, Pai, Esposo(a), Irmão(ã)'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Foto
    foto = models.ImageField(
        'Foto',
        upload_to='funcionarios/fotos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Foto do funcionário'
    )
    
    # Status
    ativo = models.BooleanField(
        'Funcionário Ativo',
        default=True
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
        related_name='funcionarios_cadastrados',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Funcionário'
        verbose_name_plural = 'Funcionários'
        ordering = ['nome_completo']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['cpf']),
            models.Index(fields=['fazenda']),
        ]
    
    def __str__(self):
        return f"{self.nome_completo} - {self.funcao}"
    
    def get_cpf_formatado(self):
        """Retorna CPF formatado"""
        import re
        cpf = re.sub(r'\D', '', self.cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return self.cpf
    
    def get_idade(self):
        """Calcula idade do funcionário"""
        if self.data_nascimento:
            from datetime import date
            hoje = date.today()
            idade = hoje.year - self.data_nascimento.year
            if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
                idade -= 1
            return idade
        return None
    
    def get_tempo_servico(self):
        """Calcula tempo de serviço"""
        from datetime import date
        if self.data_admissao:
            data_final = self.data_demissao or date.today()
            dias = (data_final - self.data_admissao).days
            anos = dias // 365
            meses = (dias % 365) // 30
            return f"{anos} ano(s) e {meses} mês(es)"
        return None
    
    def clean(self):
        """Validações"""
        from django.core.exceptions import ValidationError
        
        # Valida CPF
        import re
        cpf_limpo = re.sub(r'\D', '', self.cpf)
        if len(cpf_limpo) != 11:
            raise ValidationError({'cpf': 'CPF deve ter 11 dígitos'})
        
        # Valida data de demissão
        if self.data_demissao and self.data_admissao:
            if self.data_demissao < self.data_admissao:
                raise ValidationError({
                    'data_demissao': 'Data de demissão não pode ser anterior à admissão'
                })


# ============================================================================
# DOCUMENTOS DO FUNCIONÁRIO
# ============================================================================

class DocumentoFuncionario(models.Model):
    """
    Documentos anexados ao funcionário
    Contratação, certificados, CREA, diplomas, etc.
    """
    
    TIPO_DOCUMENTO = [
        ('CONTRATACAO', 'Contratação'),
        ('RESCISAO', 'Rescisão'),
        ('CREA', 'Registro CREA'),
        ('CERTIFICADO', 'Certificado/Treinamento'),
        ('DIPLOMA', 'Diploma/Formação'),
        ('CNH', 'CNH'),
        ('CTPS', 'CTPS'),
        ('COMPROVANTE_ENDERECO', 'Comprovante de Endereço'),
        ('COMPROVANTE_BANCARIO', 'Comprovante Bancário'),
        ('DECLARACAO_IMPOSTO_RENDA', 'Declaração de Imposto de Renda'),
        ('CONTRATO_EMERGENCIA', 'Contato de Emergência'),
        ('ASSINATURA', 'Termo de Assinatura'),
        ('OUTROS', 'Outros'),
    ]
    
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Funcionário'
    )
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='documentos_funcionario',
        verbose_name='Empresa'
    )
    
    tipo = models.CharField(
        'Tipo de Documento',
        max_length=30,
        choices=TIPO_DOCUMENTO,
        help_text='Tipo de documento'
    )
    
    titulo = models.CharField(
        'Título/Descrição',
        max_length=200,
        help_text='Descrição do documento'
    )
    
    numero_documento = models.CharField(
        'Número do Documento',
        max_length=100,
        blank=True,
        help_text='Número de registro, protocolo, CREA, etc.'
    )
    
    arquivo = models.FileField(
        'Arquivo',
        upload_to='funcionarios/documentos/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            )
        ],
        help_text='Formatos permitidos: PDF, JPG, PNG, DOC, DOCX, XLS, XLSX'
    )
    
    # Datas
    data_emissao = models.DateField(
        'Data de Emissão',
        blank=True,
        null=True
    )
    
    data_validade = models.DateField(
        'Data de Validade',
        blank=True,
        null=True,
        help_text='Deixe em branco se não houver validade'
    )
    
    # Controle de alertas de vencimento
    gerar_alerta_vencimento = models.BooleanField(
        'Gerar Alerta de Vencimento',
        default=True,
        help_text='Notificar quando próximo do vencimento'
    )
    
    dias_antecedencia_alerta = models.IntegerField(
        'Dias de Antecedência para Alerta',
        default=30,
        help_text='Quantos dias antes do vencimento alertar'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    data_upload = models.DateTimeField(
        'Data do Upload',
        auto_now_add=True
    )
    
    enviado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_funcionario_enviados',
        verbose_name='Enviado por'
    )
    
    class Meta:
        verbose_name = 'Documento do Funcionário'
        verbose_name_plural = 'Documentos dos Funcionários'
        ordering = ['-data_upload']
        indexes = [
            models.Index(fields=['funcionario', '-data_upload']),
            models.Index(fields=['empresa', 'tipo']),
        ]
    
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_display()}: {self.titulo}"
    
    def esta_vencido(self):
        """Verifica se documento está vencido"""
        if self.data_validade:
            return timezone.now().date() > self.data_validade
        return False
    
    def dias_para_vencimento(self):
        """Retorna dias restantes até vencimento"""
        if self.data_validade:
            dias = (self.data_validade - timezone.now().date()).days
            return dias
        return None
    
    def precisa_alerta(self):
        """Verifica se deve gerar alerta de vencimento"""
        if not self.gerar_alerta_vencimento or not self.data_validade:
            return False
        
        dias_restantes = self.dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= self.dias_antecedencia_alerta
        
        return False
    
    def get_nome_arquivo(self):
        """Retorna apenas o nome do arquivo sem o caminho"""
        return os.path.basename(self.arquivo.name)


# ============================================================================
# CONTROLE DE RH - FÉRIAS, AFASTAMENTOS E RESCISÕES
# ============================================================================

class FeriasFuncionario(models.Model):
    """
    Controle de férias dos funcionários
    """
    
    STATUS_FERIAS = [
        ('AGENDADA', 'Agendada'),
        ('EM_GOZO', 'Em Gozo'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPO_FERIAS = [
        ('INTEGRAL', 'Férias Integrais (30 dias)'),
        ('FRACIONADA', 'Férias Fracionadas'),
        ('COLETIVA', 'Férias Coletivas'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='ferias_funcionarios',
        verbose_name='Empresa'
    )
    
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='ferias',
        verbose_name='Funcionário'
    )
    
    # Período Aquisitivo
    periodo_aquisitivo_inicio = models.DateField(
        'Início do Período Aquisitivo',
        help_text='Data de início do período que dá direito às férias'
    )
    
    periodo_aquisitivo_fim = models.DateField(
        'Fim do Período Aquisitivo',
        help_text='Data de fim do período aquisitivo (12 meses após início)'
    )
    
    # Período de Gozo
    data_inicio = models.DateField(
        'Data de Início das Férias'
    )
    
    data_fim = models.DateField(
        'Data de Fim das Férias'
    )
    
    dias_ferias = models.PositiveIntegerField(
        'Quantidade de Dias',
        default=30,
        help_text='Dias de férias (máximo 30)'
    )
    
    tipo_ferias = models.CharField(
        'Tipo de Férias',
        max_length=20,
        choices=TIPO_FERIAS,
        default='INTEGRAL'
    )
    
    # Abono Pecuniário (venda de férias)
    abono_pecuniario = models.BooleanField(
        'Abono Pecuniário (Venda de 10 dias)',
        default=False,
        help_text='Funcionário optou por vender 10 dias de férias'
    )
    
    dias_abono = models.PositiveIntegerField(
        'Dias de Abono',
        default=0,
        help_text='Quantidade de dias vendidos (máximo 10)'
    )
    
    # Valores
    valor_ferias = models.DecimalField(
        'Valor das Férias (R$)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Valor total pago nas férias (salário + 1/3)'
    )
    
    valor_abono = models.DecimalField(
        'Valor do Abono (R$)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Valor pago pelos dias vendidos'
    )
    
    # Status e Controle
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_FERIAS,
        default='AGENDADA'
    )
    
    data_pagamento = models.DateField(
        'Data de Pagamento',
        null=True,
        blank=True,
        help_text='Data do pagamento das férias (deve ser até 2 dias antes do início)'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Documentos
    recibo_ferias = models.FileField(
        'Recibo de Férias',
        upload_to='rh/ferias/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Auditoria
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='ferias_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Férias de Funcionário'
        verbose_name_plural = 'Férias de Funcionários'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario', 'status']),
            models.Index(fields=['data_inicio', 'data_fim']),
        ]
    
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.data_inicio} a {self.data_fim}"
    
    def get_dias_corridos(self):
        """Retorna quantidade de dias corridos de férias"""
        return (self.data_fim - self.data_inicio).days + 1
    
    def clean(self):
        """Validações"""
        from django.core.exceptions import ValidationError
        
        if self.data_fim < self.data_inicio:
            raise ValidationError({
                'data_fim': 'Data de fim não pode ser anterior à data de início'
            })
        
        if self.dias_ferias > 30:
            raise ValidationError({
                'dias_ferias': 'Máximo de 30 dias de férias'
            })
        
        if self.abono_pecuniario and self.dias_abono > 10:
            raise ValidationError({
                'dias_abono': 'Máximo de 10 dias de abono pecuniário'
            })
        
        if self.periodo_aquisitivo_fim < self.periodo_aquisitivo_inicio:
            raise ValidationError({
                'periodo_aquisitivo_fim': 'Período aquisitivo inválido'
            })


class AfastamentoFuncionario(models.Model):
    """
    Controle de afastamentos de funcionários
    (Atestados médicos, acidentes de trabalho, licenças)
    """
    
    TIPO_AFASTAMENTO = [
        ('ATESTADO_MEDICO', 'Atestado Médico'),
        ('ACIDENTE_TRABALHO', 'Acidente de Trabalho'),
        ('LICENCA_MATERNIDADE', 'Licença Maternidade'),
        ('LICENCA_PATERNIDADE', 'Licença Paternidade'),
        ('LICENCA_SAUDE', 'Licença Saúde (INSS)'),
        ('SUSPENSAO', 'Suspensão'),
        ('OUTROS', 'Outros'),
    ]
    
    STATUS_AFASTAMENTO = [
        ('ATIVO', 'Ativo/Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='afastamentos_funcionarios',
        verbose_name='Empresa'
    )
    
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='afastamentos',
        verbose_name='Funcionário'
    )
    
    tipo_afastamento = models.CharField(
        'Tipo de Afastamento',
        max_length=30,
        choices=TIPO_AFASTAMENTO
    )
    
    # Datas
    data_inicio = models.DateField(
        'Data de Início do Afastamento'
    )
    
    data_prevista_retorno = models.DateField(
        'Data Prevista de Retorno'
    )
    
    data_retorno_efetivo = models.DateField(
        'Data de Retorno Efetivo',
        null=True,
        blank=True,
        help_text='Data real que o funcionário retornou'
    )
    
    dias_afastamento = models.PositiveIntegerField(
        'Dias de Afastamento',
        default=1
    )
    
    # Detalhes
    motivo = models.TextField(
        'Motivo/Descrição',
        help_text='Descreva o motivo do afastamento'
    )
    
    cid = models.CharField(
        'CID (Código Internacional de Doenças)',
        max_length=10,
        blank=True,
        help_text='CID informado no atestado médico'
    )
    
    # Documentação
    numero_atestado = models.CharField(
        'Número do Atestado/Documento',
        max_length=50,
        blank=True
    )
    
    medico_responsavel = models.CharField(
        'Médico Responsável',
        max_length=200,
        blank=True
    )
    
    crm_medico = models.CharField(
        'CRM do Médico',
        max_length=20,
        blank=True
    )
    
    arquivo_atestado = models.FileField(
        'Arquivo do Atestado/Documento',
        upload_to='rh/afastamentos/%Y/%m/',
        null=True,
        blank=True,
        help_text='PDF ou imagem do atestado'
    )
    
    # Acidente de Trabalho
    e_acidente_trabalho = models.BooleanField(
        'É Acidente de Trabalho?',
        default=False
    )
    
    cat_emitida = models.BooleanField(
        'CAT Emitida?',
        default=False,
        help_text='Comunicação de Acidente de Trabalho'
    )
    
    numero_cat = models.CharField(
        'Número da CAT',
        max_length=50,
        blank=True
    )
    
    arquivo_cat = models.FileField(
        'Arquivo da CAT',
        upload_to='rh/cat/%Y/%m/',
        null=True,
        blank=True
    )
    
    # INSS
    requer_inss = models.BooleanField(
        'Requer Auxílio INSS?',
        default=False,
        help_text='Afastamento superior a 15 dias'
    )
    
    numero_beneficio_inss = models.CharField(
        'Número do Benefício INSS',
        max_length=50,
        blank=True
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_AFASTAMENTO,
        default='ATIVO'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='afastamentos_cadastrados',
        verbose_name='Cadastrado por'
    )
    
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Afastamento de Funcionário'
        verbose_name_plural = 'Afastamentos de Funcionários'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario', 'status']),
            models.Index(fields=['tipo_afastamento']),
            models.Index(fields=['data_inicio', 'data_prevista_retorno']),
        ]
    
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_afastamento_display()} ({self.data_inicio})"
    
    def get_dias_corridos(self):
        """Retorna quantidade de dias corridos de afastamento"""
        data_final = self.data_retorno_efetivo or self.data_prevista_retorno
        return (data_final - self.data_inicio).days + 1
    
    def clean(self):
        """Validações"""
        from django.core.exceptions import ValidationError
        
        if self.data_prevista_retorno < self.data_inicio:
            raise ValidationError({
                'data_prevista_retorno': 'Data de retorno não pode ser anterior à data de início'
            })
        
        if self.data_retorno_efetivo and self.data_retorno_efetivo < self.data_inicio:
            raise ValidationError({
                'data_retorno_efetivo': 'Data de retorno efetivo não pode ser anterior à data de início'
            })
        
        # Se acidente de trabalho, CAT é obrigatória
        if self.e_acidente_trabalho and not self.cat_emitida:
            raise ValidationError({
                'cat_emitida': 'CAT deve ser emitida para acidentes de trabalho'
            })


class RescisaoContrato(models.Model):
    """
    Controle de rescisões/desligamentos de funcionários
    """
    
    TIPO_RESCISAO = [
        ('DEMISSAO_SEM_JUSTA_CAUSA', 'Demissão Sem Justa Causa'),
        ('DEMISSAO_COM_JUSTA_CAUSA', 'Demissão Com Justa Causa'),
        ('PEDIDO_DEMISSAO', 'Pedido de Demissão'),
        ('ACORDO_TRABALHISTA', 'Acordo Trabalhista'),
        ('TERMINO_CONTRATO', 'Término de Contrato (Temporário)'),
        ('APOSENTADORIA', 'Aposentadoria'),
        ('FALECIMENTO', 'Falecimento'),
    ]
    
    STATUS_RESCISAO = [
        ('EM_PROCESSO', 'Em Processo'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='rescisoes',
        verbose_name='Empresa'
    )
    
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name='rescisoes',
        verbose_name='Funcionário'
    )
    
    tipo_rescisao = models.CharField(
        'Tipo de Rescisão',
        max_length=40,
        choices=TIPO_RESCISAO
    )
    
    # Datas
    data_aviso = models.DateField(
        'Data do Aviso',
        help_text='Data em que o aviso prévio foi dado'
    )
    
    data_desligamento = models.DateField(
        'Data do Desligamento',
        help_text='Último dia de trabalho'
    )
    
    trabalhou_aviso_previo = models.BooleanField(
        'Trabalhou o Aviso Prévio?',
        default=True
    )
    
    dias_aviso_previo = models.PositiveIntegerField(
        'Dias de Aviso Prévio',
        default=30,
        help_text='Quantidade de dias de aviso prévio'
    )
    
    # Motivo
    motivo_detalhado = models.TextField(
        'Motivo Detalhado da Rescisão',
        help_text='Descreva o motivo do desligamento'
    )
    
    # Valores da Rescisão
    saldo_salario = models.DecimalField(
        'Saldo de Salário (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    ferias_vencidas = models.DecimalField(
        'Férias Vencidas (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    ferias_proporcionais = models.DecimalField(
        'Férias Proporcionais (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    decimo_terceiro_proporcional = models.DecimalField(
        '13º Proporcional (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    aviso_previo_indenizado = models.DecimalField(
        'Aviso Prévio Indenizado (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    multa_fgts = models.DecimalField(
        'Multa FGTS 40% (R$)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Multa de 40% sobre FGTS (apenas em demissão sem justa causa)'
    )
    
    outros_valores = models.DecimalField(
        'Outros Valores (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    descontos = models.DecimalField(
        'Descontos (R$)',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Faltas, adiantamentos, etc.'
    )
    
    valor_liquido = models.DecimalField(
        'Valor Líquido a Pagar (R$)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Direitos
    tem_direito_seguro_desemprego = models.BooleanField(
        'Tem Direito a Seguro Desemprego?',
        default=False
    )
    
    liberar_fgts = models.BooleanField(
        'Liberar Saque FGTS?',
        default=False
    )
    
    # Exames e Documentos
    exame_demissional_realizado = models.BooleanField(
        'Exame Demissional Realizado?',
        default=False
    )
    
    data_exame_demissional = models.DateField(
        'Data do Exame Demissional',
        null=True,
        blank=True
    )
    
    trct_emitido = models.BooleanField(
        'TRCT Emitido?',
        default=False,
        help_text='Termo de Rescisão do Contrato de Trabalho'
    )
    
    chave_conectividade_social = models.CharField(
        'Chave Conectividade Social',
        max_length=50,
        blank=True
    )
    
    # Arquivos
    arquivo_trct = models.FileField(
        'Arquivo TRCT',
        upload_to='rh/rescisoes/%Y/%m/',
        null=True,
        blank=True
    )
    
    arquivo_exame = models.FileField(
        'Arquivo Exame Demissional',
        upload_to='rh/rescisoes/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Homologação
    data_homologacao = models.DateField(
        'Data da Homologação',
        null=True,
        blank=True,
        help_text='Data de homologação no sindicato (se aplicável)'
    )
    
    local_homologacao = models.CharField(
        'Local da Homologação',
        max_length=200,
        blank=True
    )
    
    # Pagamento
    data_pagamento = models.DateField(
        'Data do Pagamento',
        null=True,
        blank=True
    )
    
    forma_pagamento = models.CharField(
        'Forma de Pagamento',
        max_length=50,
        blank=True,
        help_text='Dinheiro, Transferência, Cheque, etc.'
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_RESCISAO,
        default='EM_PROCESSO'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='rescisoes_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Rescisão de Contrato'
        verbose_name_plural = 'Rescisões de Contratos'
        ordering = ['-data_desligamento']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['funcionario']),
            models.Index(fields=['tipo_rescisao']),
            models.Index(fields=['data_desligamento']),
        ]
    
    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_rescisao_display()} ({self.data_desligamento})"
    
    def calcular_valor_liquido(self):
        """Calcula valor líquido da rescisão"""
        total = (
            self.saldo_salario +
            self.ferias_vencidas +
            self.ferias_proporcionais +
            self.decimo_terceiro_proporcional +
            self.aviso_previo_indenizado +
            self.multa_fgts +
            self.outros_valores -
            self.descontos
        )
        return total
    
    def clean(self):
        """Validações"""
        from django.core.exceptions import ValidationError
        
        if self.data_desligamento < self.data_aviso:
            raise ValidationError({
                'data_desligamento': 'Data de desligamento não pode ser anterior ao aviso'
            })
        
        # Valida multa FGTS apenas para demissão sem justa causa
        if self.tipo_rescisao != 'DEMISSAO_SEM_JUSTA_CAUSA' and self.multa_fgts > 0:
            raise ValidationError({
                'multa_fgts': 'Multa FGTS apenas para demissão sem justa causa'
            })


# CULTURA

"""
ADICIONE ESTE CÓDIGO NO FINAL DO ARQUIVO cadastros/models.py
(Após o modelo DocumentoFazenda)
"""


class Cultura(models.Model):
    """
    Cadastro de Culturas/Produtos Agrícolas
    Melão, Melancia, Milho, Abóbora, etc
    """
    
    TIPO_CULTURA = [
        ('FRUTA', 'Fruta'),
        ('HORTALICA', 'Hortaliça'),
        ('GRAOS', 'Grãos'),
        ('TUBEROSAS', 'Tuberosas'),
        ('OLEAGINOSAS', 'Oleaginosas'),
        ('OUTROS', 'Outros'),
    ]
    
    CICLO_CULTURA = [
        ('CURTO', 'Curto (até 90 dias)'),
        ('MEDIO', 'Médio (90 a 180 dias)'),
        ('LONGO', 'Longo (mais de 180 dias)'),
    ]
    
    UNIDADE_MEDIDA = [
        ('KG', 'Quilograma (kg)'),
        ('TON', 'Tonelada (ton)'),
        ('UNIDADE', 'Unidade'),
        ('CAIXA', 'Caixa'),
        ('SACO', 'Saco'),
        ('DÚZIA', 'Dúzia'),
    ]
    
    # Vinculação multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='culturas',
        verbose_name='Empresa'
    )
    
    # Dados básicos
    nome = models.CharField(
        'Nome da Cultura',
        max_length=100,
        help_text='Ex: Melão, Melancia, Milho'
    )
    
    nome_cientifico = models.CharField(
        'Nome Científico',
        max_length=150,
        blank=True,
        help_text='Nome científico da espécie'
    )
    
    tipo = models.CharField(
        'Tipo de Cultura',
        max_length=20,
        choices=TIPO_CULTURA,
        default='FRUTA'
    )
    
    # Variedades
    variedade = models.CharField(
        'Variedade',
        max_length=100,
        blank=True,
        help_text='Ex: Amarelo, Pele de Sapo, Gália'
    )
    
    codigo_interno = models.CharField(
        'Código Interno',
        max_length=20,
        blank=True,
        help_text='Código de identificação interno'
    )
    
    # Características de plantio
    ciclo_cultivo = models.CharField(
        'Ciclo de Cultivo',
        max_length=10,
        choices=CICLO_CULTURA,
        default='MEDIO',
        help_text='Tempo médio até colheita'
    )
    
    dias_colheita = models.IntegerField(
        'Dias até Colheita',
        default=90,
        validators=[MinValueValidator(1)],
        help_text='Dias do plantio até colheita'
    )
    
    espacamento_linhas = models.DecimalField(
        'Espaçamento entre Linhas (m)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Distância entre linhas em metros'
    )
    
    espacamento_plantas = models.DecimalField(
        'Espaçamento entre Plantas (m)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Distância entre plantas em metros'
    )
    
    densidade_plantio = models.IntegerField(
        'Densidade de Plantio (plantas/ha)',
        blank=True,
        null=True,
        validators=[MinValueValidator(1)],
        help_text='Quantidade de plantas por hectare'
    )
    
    # Características climáticas
    temperatura_ideal_min = models.DecimalField(
        'Temperatura Ideal Mínima (°C)',
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        help_text='Temperatura mínima ideal'
    )
    
    temperatura_ideal_max = models.DecimalField(
        'Temperatura Ideal Máxima (°C)',
        max_digits=4,
        decimal_places=1,
        blank=True,
        null=True,
        help_text='Temperatura máxima ideal'
    )
    
    necessidade_agua = models.CharField(
        'Necessidade de Água',
        max_length=50,
        blank=True,
        help_text='Ex: 400-600mm, Alta, Média'
    )
    
    # Produtividade
    unidade_medida = models.CharField(
        'Unidade de Medida',
        max_length=10,
        choices=UNIDADE_MEDIDA,
        default='TON'
    )
    
    produtividade_esperada = models.DecimalField(
        'Produtividade Esperada (por hectare)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Produção média por hectare'
    )
    
    # Características comerciais
    preco_medio = models.DecimalField(
        'Preço Médio de Venda',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Preço médio no mercado'
    )
    
    mercado_destino = models.CharField(
        'Mercado de Destino',
        max_length=100,
        blank=True,
        help_text='Ex: Interno, Exportação, Ambos'
    )
    
    # Manejo
    irrigacao_necessaria = models.BooleanField(
        'Irrigação Necessária',
        default=True
    )
    
    tipo_irrigacao = models.CharField(
        'Tipo de Irrigação',
        max_length=100,
        blank=True,
        help_text='Ex: Gotejamento, Aspersão, Pivô Central'
    )
    
    adubacao_recomendada = models.TextField(
        'Adubação Recomendada',
        blank=True,
        help_text='Descrição da adubação recomendada'
    )
    
    controle_pragas = models.TextField(
        'Controle de Pragas e Doenças',
        blank=True,
        help_text='Principais pragas e métodos de controle'
    )
    
    # Certificações
    certificacao_organica = models.BooleanField(
        'Certificação Orgânica',
        default=False
    )
    
    certificacao_exportacao = models.BooleanField(
        'Certificação para Exportação',
        default=False
    )
    
    # Imagem
    imagem = models.ImageField(
        'Imagem da Cultura',
        upload_to='culturas/imagens/%Y/%m/',
        blank=True,
        null=True,
        help_text='Foto da cultura/fruto'
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Informações adicionais sobre a cultura'
    )
    
    # Colheita
    max_etapas_colheita = models.PositiveSmallIntegerField(
        'Máx. Etapas de Colheita',
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Número máximo de colheitas por ciclo (1 para grãos, 2-3 para frutas/melão)'
    )

    # Status
    ativa = models.BooleanField(
        'Cultura Ativa',
        default=True,
        help_text='Define se a cultura está sendo cultivada'
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
        related_name='culturas_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Cultura'
        verbose_name_plural = 'Culturas'
        ordering = ['nome', 'variedade']
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['tipo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome', 'variedade'],
                name='unique_cultura_variedade_empresa'
            )
        ]
    
    def __str__(self):
        if self.variedade:
            return f"{self.nome} - {self.variedade}"
        return self.nome
    
    def clean(self):
        """Validações customizadas"""
        from django.core.exceptions import ValidationError
        
        # Valida temperaturas
        if (self.temperatura_ideal_min and self.temperatura_ideal_max and 
            self.temperatura_ideal_min > self.temperatura_ideal_max):
            raise ValidationError({
                'temperatura_ideal_max': 'Temperatura máxima deve ser maior que mínima'
            })
        
        # Valida limite de culturas do plano (se houver) - APENAS se empresa já estiver definida
        if not self.pk and self.empresa_id:
            try:
                total_culturas = Cultura.objects.filter(
                    empresa_id=self.empresa_id,
                    ativa=True
                ).count()
                
                # Busca a empresa para verificar limite
                from empresas.models import Empresa
                empresa = Empresa.objects.get(pk=self.empresa_id)
                
                if hasattr(empresa, 'limite_produtos') and empresa.limite_produtos < 999:
                    if total_culturas >= empresa.limite_produtos:
                        raise ValidationError(
                            f'Limite de culturas atingido! Seu plano permite apenas '
                            f'{empresa.limite_produtos} cultura(s) ativa(s).'
                        )
            except:  # noqa: E722
                pass  # Se houver erro na validação, deixa passar
    
    def get_ciclo_display_dias(self):
        """Retorna ciclo em dias formatado"""
        return f"{self.dias_colheita} dias"
    
    def get_densidade_calculada(self):
        """Calcula densidade baseada em espaçamento"""
        if self.espacamento_linhas and self.espacamento_plantas:
            # Área por planta em m²
            area_por_planta = float(self.espacamento_linhas) * float(self.espacamento_plantas)
            # Plantas por hectare (10.000 m²)
            densidade = 10000 / area_por_planta
            return int(densidade)
        return self.densidade_plantio
    
    def get_receita_estimada_ha(self):
        """Calcula receita estimada por hectare"""
        if self.produtividade_esperada and self.preco_medio:
            return self.produtividade_esperada * self.preco_medio
        return None
    
    def get_total_plantios(self):
        """Retorna total de plantios desta cultura"""
        # Será implementado quando criar o módulo de Plantio
        return 0


class Praga(models.Model):
    """
    Cadastro de Pragas Agrícolas
    Insetos, fungos, doenças que afetam as culturas
    """
    
    # Vinculação multi-tenant
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='pragas',
        verbose_name='Empresa'
    )
    
    # Dados básicos
    TIPO_PRAGA_CHOICES = [
        ('INSETO', 'Inseto'),
        ('ACARO', 'Ácaro'),
        ('NEMATOIDE', 'Nematoide'),
        ('FUNGO', 'Fungo'),
        ('BACTERIA', 'Bactéria'),
        ('VIRUS', 'Vírus'),
        ('MOLUSCO', 'Molusco'),
        ('OUTRO', 'Outro'),
    ]

    nome_comum = models.CharField(
        'Nome Comum',
        max_length=150,
        help_text='Ex: Lagarta-do-cartucho, Mosca-branca, Ferrugem'
    )

    tipo_praga = models.CharField(
        'Tipo de Praga',
        max_length=20,
        choices=TIPO_PRAGA_CHOICES,
        default='OUTRO',
        help_text='Classificacao da natureza da praga'
    )
    
    nome_cientifico = models.CharField(
        'Nome Científico',
        max_length=200,
        blank=True,
        help_text='Nome científico da praga/doença'
    )
    
    # Foto
    foto = models.ImageField(
        'Foto da Praga',
        upload_to='pragas/%Y/%m/',
        blank=True,
        null=True,
        help_text='Foto ou imagem identificativa da praga (JPG, PNG)'
    )
    
    # Status
    ativa = models.BooleanField(
        'Praga Ativa',
        default=True,
        help_text='Define se a praga está ativa para cadastro'
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
        related_name='pragas_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    class Meta:
        verbose_name = 'Praga'
        verbose_name_plural = 'Pragas'
        ordering = ['nome_comum']
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['nome_comum']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'nome_comum'],
                name='unique_praga_empresa'
            )
        ]
    
    def __str__(self):
        if self.nome_cientifico:
            return f"{self.nome_comum} ({self.nome_cientifico})"
        return self.nome_comum


# ============================================
# MÓDULO: MONITORAMENTO MIP (Manejo Integrado de Pragas)
# ============================================

class EstagioDesenvolvimento(models.Model):
    """
    Estágios do ciclo de vida de uma praga
    Ex: Lagarta-do-cartucho tem: Ovo → Larva → Pupa → Adulto
    Cada praga pode ter múltiplos estágios
    """
    
    TIPO_ESTAGIO_CHOICES = [
        ('OVO', 'Ovo'),
        ('NINFA', 'Ninfa'),
        ('LARVA', 'Larva'),
        ('PUPA', 'Pupa'),
        ('ADULTO', 'Adulto'),
        ('ESPORO', 'Esporo (Fungo)'),
        ('LESAO', 'Lesão (Doença)'),
        ('OUTRO', 'Outro'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='estagios_desenvolvimento',
        verbose_name='Empresa',
        null=True,
        blank=True,
        help_text='Deixar em branco para criar um template padrão'
    )
    
    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.CASCADE,
        related_name='estagios',
        verbose_name='Praga'
    )
    
    tipo_estagio = models.CharField(
        'Tipo de Estágio',
        max_length=20,
        choices=TIPO_ESTAGIO_CHOICES,
        help_text='Ex: Ovo, Larva, Adulto, etc'
    )
    
    descricao = models.CharField(
        'Descrição',
        max_length=200,
        blank=True,
        help_text='Ex: "Larva de 3º ínstar" ou "Ninfa 4 (pseudopupa)"'
    )
    
    duracao_minima_dias = models.IntegerField(
        'Duração Mínima (dias)',
        null=True,
        blank=True,
        help_text='Duração mínima deste estágio'
    )
    
    duracao_maxima_dias = models.IntegerField(
        'Duração Máxima (dias)',
        null=True,
        blank=True,
        help_text='Duração máxima deste estágio'
    )
    
    ordem_ciclo = models.IntegerField(
        'Ordem no Ciclo',
        default=1,
        help_text='1=Ovo, 2=Larva1, 3=Larva2, etc'
    )
    
    eh_fase_critica = models.BooleanField(
        'É Fase Crítica?',
        default=False,
        help_text='Marcar se é a fase mais sensível/danosa'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Notas sobre este estágio'
    )
    
    ativo = models.BooleanField('Ativo', default=True)
    
    # Template de estágios padrão
    eh_template = models.BooleanField(
        'É Estágio Template?',
        default=False,
        help_text='Marcar para estágios padrão que serão copiados para novas empresas'
    )
    
    template_original = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='copias',
        verbose_name='Template Original',
        help_text='Se preenchido, este estágio foi copiado de um template'
    )
    
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Estágio de Desenvolvimento'
        verbose_name_plural = 'Estágios de Desenvolvimento'
        ordering = ['praga', 'ordem_ciclo']
        indexes = [
            models.Index(fields=['empresa', 'praga']),
            models.Index(fields=['tipo_estagio']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'praga', 'tipo_estagio', 'ordem_ciclo'],
                name='unique_estagio_praga_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.praga.nome_comum} - {self.get_tipo_estagio_display()}"


class MonitoramentoMIP(models.Model):
    """
    Monitoramento MIP (Manejo Integrado de Pragas)
    Representa UMA VISITA ao talhão para avaliação de pragas
    Pode registrar múltiplas pragas na mesma visita
    """
    
    TIPO_MONITORAMENTO_CHOICES = [
        ('REGULAR', 'Monitoramento Regular'),
        ('PREVENTIVO', 'Monitoramento Preventivo'),
        ('EMERGENCIAL', 'Monitoramento Emergencial'),
    ]
    
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('COMPLETO', 'Monitoramento Completo'),
        ('ANALISADO', 'Analisado e Avaliado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='monitoramentos_mip',
        verbose_name='Empresa'
    )
    
    numero = models.CharField(
        'Número',
        max_length=20,
        unique=True,
        help_text='Auto-gerado: MIP-YYYY-NNNNN'
    )
    
    # Contexto agrícola
    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='monitoramentos_mip',
        verbose_name='Talhão'
    )
    
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='monitoramentos_mip',
        verbose_name='Safra',
        help_text='Selecione a safra ativa em que o monitoramento foi realizado'
    )
    
    cultura = models.ForeignKey(
        'cadastros.Cultura',
        on_delete=models.PROTECT,
        related_name='monitoramentos_mip',
        verbose_name='Cultura',
        help_text='Auto-preenchida do talhão'
    )
    
    # Identificação da visita
    data_monitoramento = models.DateField(
        'Data do Monitoramento',
        help_text='Data da visita ao talhão'
    )
    
    tipo_monitoramento = models.CharField(
        'Tipo de Monitoramento',
        max_length=20,
        choices=TIPO_MONITORAMENTO_CHOICES,
        default='REGULAR'
    )
    
    responsavel = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitoramentos_mip_realizados',
        verbose_name='Responsável (Pragueiro)'
    )
    
    # Amostragem
    quantidade_pontos = models.IntegerField(
        'Quantidade de Pontos',
        default=20,
        help_text='Padrão: 20 pontos por monitoramento'
    )

    CONDICOES_TEMPO_CHOICES = [
        ('ENSOLARADO', 'Ensolarado'),
        ('PARCIALMENTE_NUBLADO', 'Parcialmente Nublado'),
        ('NUBLADO', 'Nublado'),
        ('CHUVA_LEVE', 'Chuva Leve'),
        ('CHUVA_MODERADA', 'Chuva Moderada'),
        ('CHUVA_FORTE', 'Chuva Forte'),
        ('GAROA', 'Garoa'),
        ('VENTO_FRACO', 'Vento Fraco'),
        ('VENTO_MODERADO', 'Vento Moderado'),
        ('VENTO_FORTE', 'Vento Forte'),
        ('NEBLINA', 'Neblina'),
        ('ORVALHO', 'Orvalho'),
        ('SECO', 'Seco'),
        ('UMIDO', 'Umido'),
        ('OUTRO', 'Outro'),
    ]
    
    # Condições climáticas no momento da visita
    condicoes_tempo = models.CharField(
        'Condições do Tempo',
        max_length=100,
        blank=True,
        choices=CONDICOES_TEMPO_CHOICES,
        help_text='Selecione a condição observada no momento da visita'
    )
    
    temperatura_media = models.DecimalField(
        'Temperatura Média (°C)',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )
    
    umidade_media = models.IntegerField(
        'Umidade Média (%)',
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100)
        ]
    )
    
    velocidade_vento_media = models.DecimalField(
        'Velocidade do Vento Média (km/h)',
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Evidências
    foto_area_geral = models.ImageField(
        'Foto da Área Geral',
        upload_to='monitoramento_mip/%Y/%m/',
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
    
    observacoes_gerais = models.TextField(
        'Observações Gerais',
        blank=True,
        help_text='Notas gerais sobre a visita'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='monitoramentos_mip_criados',
        verbose_name='Criado Por'
    )
    
    class Meta:
        verbose_name = 'Monitoramento MIP'
        verbose_name_plural = 'Monitoramentos MIP'
        ordering = ['-data_monitoramento']
        indexes = [
            models.Index(fields=['empresa', 'data_monitoramento']),
            models.Index(fields=['talhao', 'data_monitoramento']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['talhao', 'data_monitoramento'],
                name='unique_monitoramento_talhao_data',
                condition=models.Q(status__in=['COMPLETO', 'ANALISADO'])
            )
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.talhao.nome} ({self.data_monitoramento})"
    
    def save(self, *args, **kwargs):
        """Auto-gera número se não tiver"""
        if not self.numero:
            from datetime import datetime
            from django.utils import timezone
            ano = timezone.now().year
            ultima = MonitoramentoMIP.objects.filter(
                numero__startswith=f'MIP-{ano}'
            ).order_by('numero').last()
            
            if ultima:
                numero_seq = int(ultima.numero.split('-')[-1]) + 1
            else:
                numero_seq = 1
            
            self.numero = f'MIP-{ano}-{numero_seq:05d}'
        
        # Auto-carrega cultura do talhão se não tiver
        if self.talhao and not self.cultura:
            self.cultura = self.talhao.cultura_atual
        
        super().save(*args, **kwargs)


class PragaNoMonitoramento(models.Model):
    """
    Customized M2M: Liga Praga ao Monitoramento MIP
    Um monitoramento pode ter N pragas
    Cada praga tem seus próprios dados de incidência, estágio, etc
    """
    
    RESULTADO_ACAO_CHOICES = [
        ('SEM_ACAO', 'Sem Ação Necessária'),
        ('MONITORAR', 'Continuar Monitorando'),
        ('RECOMENDA_DEFENSIVO', 'Recomenda Defensivo'),
    ]
    
    SEVERIDADE_CHOICES = [
        (1, 'Muito Baixa'),
        (2, 'Baixa'),
        (3, 'Média'),
        (4, 'Alta'),
        (5, 'Muito Alta'),
    ]
    
    monitoramento = models.ForeignKey(
        'cadastros.MonitoramentoMIP',
        on_delete=models.CASCADE,
        related_name='pragas_detectadas',
        verbose_name='Monitoramento MIP'
    )
    
    praga = models.ForeignKey(
        'cadastros.Praga',
        on_delete=models.PROTECT,
        related_name='monitoramentos',
        verbose_name='Praga/Doença'
    )
    
    # AMOSTRAGEM
    quantidade_pontos_com_praga = models.IntegerField(
        'Quantidade de Pontos com Praga',
        help_text='Quantos dos 20 pontos tinham esta praga'
    )
    
    incidencia_percentual = models.DecimalField(
        'Incidência (%)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        default=0,
        help_text='Calculado automaticamente: (qty_pontos/20)*100'
    )
    
    # ESTÁGIOS ENCONTRADOS
    estagio_principal = models.ForeignKey(
        'cadastros.EstagioDesenvolvimento',
        on_delete=models.PROTECT,
        related_name='praga_monitoramento_estagio_principal',
        verbose_name='Estágio Principal',
        help_text='Estágio mais crítico encontrado'
    )
    
    detalhes_estagios = models.JSONField(
        'Detalhes por Estágio',
        default=dict,
        blank=True,
        help_text='Ex: {"L3": 5, "L4": 3, "Adulto": 2}'
    )
    
    # INDICADORES
    severidade = models.IntegerField(
        'Severidade (1-5)',
        choices=SEVERIDADE_CHOICES,
        default=3,
        help_text='1=Muito Baixa, 5=Muito Alta'
    )
    
    quantidade_total_pragas = models.IntegerField(
        'Quantidade Total de Pragas Encontradas',
        null=True,
        blank=True,
        help_text='Soma de todos os insetos/lesões encontradas'
    )
    
    # COMPARAÇÃO COM NED
    ned_valor = models.DecimalField(
        'Nível Econômico de Dano (%)',
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text='NED recomendado para esta praga+cultura+estágio'
    )
    
    ned_atingido = models.BooleanField(
        'NED Atingido?',
        help_text='Incidência >= NED?'
    )
    
    # RESULTADO
    resultado_acao = models.CharField(
        'Resultado da Ação',
        max_length=20,
        choices=RESULTADO_ACAO_CHOICES,
        default='MONITORAR'
    )
    
    # EVIDÊNCIAS
    fotos = models.JSONField(
        'Fotos da Praga',
        default=list,
        blank=True,
        help_text='URLs das fotos tiradas desta praga'
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Notas específicas sobre esta praga'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Praga no Monitoramento'
        verbose_name_plural = 'Pragas no Monitoramento'
        ordering = ['monitoramento', 'resultado_acao', '-incidencia_percentual']
        indexes = [
            models.Index(fields=['monitoramento', 'ned_atingido']),
            models.Index(fields=['resultado_acao']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['monitoramento', 'praga'],
                name='unique_praga_por_monitoramento'
            )
        ]
    
    def __str__(self):
        return f"{self.monitoramento.numero} - {self.praga.nome_comum} ({self.incidencia_percentual}%)"
    
    def save(self, *args, **kwargs):
        """Auto-calcula incidência e outras informações"""
        if not self.incidencia_percentual:
            self.incidencia_percentual = (
                (self.quantidade_pontos_com_praga / 
                 self.monitoramento.quantidade_pontos) * 100
            )
        
        # Auto-determina se NED foi atingido
        if self.ned_valor is not None:
            self.ned_atingido = self.incidencia_percentual >= self.ned_valor
            
            # Define resultado com base no NED
            if self.ned_atingido:
                self.resultado_acao = 'RECOMENDA_DEFENSIVO'
            elif self.incidencia_percentual > 0 and self.incidencia_percentual < self.ned_valor:
                self.resultado_acao = 'MONITORAR'
            else:
                self.resultado_acao = 'SEM_ACAO'
        
        super().save(*args, **kwargs)


class PontoMonitoramento(models.Model):
    """
    Detalhe de cada um dos 20 pontos no monitoramento de uma praga
    Registra qual praga foi encontrada em qual ponto
    """
    
    praga_monitoramento = models.ForeignKey(
        'cadastros.PragaNoMonitoramento',
        on_delete=models.CASCADE,
        related_name='pontos',
        verbose_name='Praga no Monitoramento'
    )
    
    numero_ponto = models.IntegerField(
        'Número do Ponto',
        validators=[
            MinValueValidator(1),
            MaxValueValidator(20)
        ],
        help_text='Qual dos 20 pontos (1-20)'
    )
    
    # Localização (opcional - para talhões grandes)
    latitude = models.DecimalField(
        'Latitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Coordenada GPS do ponto'
    )
    
    longitude = models.DecimalField(
        'Longitude',
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Coordenada GPS do ponto'
    )
    
    # Avaliação do ponto
    praga_presente = models.BooleanField(
        'Praga Presente?',
        default=False,
        help_text='Foi encontrada praga neste ponto?'
    )
    
    quantidade = models.IntegerField(
        'Quantidade',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Quantos insetos/lesões encontrados neste ponto'
    )
    
    estagio = models.ForeignKey(
        'cadastros.EstagioDesenvolvimento',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name='Estágio Encontrado'
    )
    
    severidade = models.IntegerField(
        'Severidade Neste Ponto',
        choices=[
            (0, 'Nenhuma'),
            (1, 'Muito Leve'),
            (2, 'Leve'),
            (3, 'Média'),
            (4, 'Severa'),
            (5, 'Muito Severa'),
        ],
        default=0
    )
    
    # Evidência fotográfica
    foto = models.ImageField(
        'Foto do Ponto',
        upload_to='monitoramento_pontos/%Y/%m/',
        null=True,
        blank=True
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Notas sobre este ponto específico'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Ponto de Monitoramento'
        verbose_name_plural = 'Pontos de Monitoramento'
        ordering = ['praga_monitoramento', 'numero_ponto']
        indexes = [
            models.Index(fields=['praga_monitoramento', 'numero_ponto']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['praga_monitoramento', 'numero_ponto'],
                name='unique_ponto_por_praga_monitoramento'
            )
        ]
    
    def __str__(self):
        return f"Ponto {self.numero_ponto} - {self.praga_monitoramento}"


# ============================================
# MÓDULO: ÁREAS E TALHÕES
# ============================================

class Area(models.Model):
    """
    Áreas agricultáveis dentro de uma Fazenda
    Uma fazenda pode ter múltiplas áreas (seções/setores)
    """
    # ✅ ADICIONE ESTA LINHA LOGO APÓS AS CHOICES
    objects = AreaManager()  # 🔥 LINHA CRÍTICA - ATIVA O MANAGER CUSTOMIZADO
    
    TIPO_AREA_CHOICES = [
        ('AGRICOLA', 'Área Agrícola'),
        ('PASTAGEM', 'Pastagem'),
        ('RESERVA', 'Reserva Legal'),
        ('APP', 'APP - Área de Preservação Permanente'),
        ('INFRAESTRUTURA', 'Infraestrutura'),
        ('OUTROS', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('EM_USO', 'Em Uso'),
        ('DESCANSO', 'Em Descanso'),
        ('PREPARACAO', 'Em Preparação'),
        ('INATIVA', 'Inativa'),
    ]
    
    # Identificação
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='areas',
        verbose_name='Fazenda'
    )
    
    nome = models.CharField(
        'Nome da Área',
        max_length=100,
        help_text='Ex: Setor A, Área Norte, etc.'
    )
    
    codigo_interno = models.CharField(
        'Código Interno',
        max_length=20,
        blank=True,
        help_text='Código de identificação interno'
    )
    
    tipo_area = models.CharField(
        'Tipo de Área',
        max_length=20,
        choices=TIPO_AREA_CHOICES,
        default='AGRICOLA'
    )
    
    # Medidas
    area_total = models.DecimalField(
        'Área Total (ha)',
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text='Área total em hectares'
    )
    
    area_plantavel = models.DecimalField(
        'Área Plantável (ha)',
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Área efetivamente disponível para plantio'
    )
    
    area_reserva = models.DecimalField(
        'Área de Reserva (ha)',
        max_digits=10,
        decimal_places=4,
        blank=True,
        null=True,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Área reservada (estradas, infraestrutura, proteção ambiental, etc.)'
    )
    
    # Geolocalização
    latitude = models.DecimalField(
        'Latitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text='Coordenada geográfica'
    )
    
    longitude = models.DecimalField(
        'Longitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True,
        help_text='Coordenada geográfica'
    )
    
    # Características do solo
    tipo_solo = models.CharField(
        'Tipo de Solo',
        max_length=100,
        blank=True,
        help_text='Ex: Arenoso, Argiloso, etc.'
    )
    
    ph_solo = models.DecimalField(
        'pH do Solo',
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('14'))]
    )
    
    topografia = models.CharField(
        'Topografia',
        max_length=50,
        blank=True,
        choices=[
            ('PLANA', 'Plana'),
            ('ONDULADA', 'Ondulada'),
            ('MONTANHOSA', 'Montanhosa'),
        ],
        help_text='Relevo da área'
    )
    
    # Sistema de irrigação
    possui_irrigacao = models.BooleanField(
        'Possui Irrigação',
        default=False
    )
    
    tipo_irrigacao = models.CharField(
        'Tipo de Irrigação',
        max_length=50,
        blank=True,
        choices=[
            ('GOTEJAMENTO', 'Gotejamento'),
            ('ASPERSAO', 'Aspersão'),
            ('PIVO', 'Pivô Central'),
            ('SULCO', 'Sulco'),
            ('MICROASPERSAO', 'Microaspersão'),
        ]
    )
    
    # Status e controle
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='DISPONIVEL'
    )
    
    ativa = models.BooleanField(
        'Área Ativa',
        default=True
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='areas',
        verbose_name='Empresa'
    )
    
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='areas_cadastradas',
        verbose_name='Cadastrado por'
    )
    
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = "Área"
        verbose_name_plural = "Áreas"
        ordering = ['fazenda__nome', 'nome']
        unique_together = [['fazenda', 'codigo_interno']]
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['fazenda', 'status']),
        ]
    
    def __str__(self):
        return f"{self.fazenda.nome} - {self.nome}"
    
    def clean(self):
        """Validações customizadas"""
        # Valida área plantável
        if self.area_plantavel and self.area_plantavel > self.area_total:
            raise ValidationError({
                'area_plantavel': 'Área plantável não pode ser maior que área total'
            })
        
        # Valida irrigação
        if self.tipo_irrigacao and not self.possui_irrigacao:
            raise ValidationError({
                'tipo_irrigacao': 'Defina "Possui Irrigação" como Sim antes de informar o tipo'
            })
    
    def get_area_disponivel(self):
        """Retorna área disponível para novos talhões (descontando reserva)"""
        # Calcula área para plantio (total - reserva)
        area_para_plantio = self.area_total - (self.area_reserva or Decimal('0'))
        
        # Calcula área ocupada por talhões ativos
        area_ocupada = self.talhoes.filter(
            ativo=True
        ).aggregate(
            total=models.Sum('area_hac')
        )['total'] or Decimal('0')
        
        return area_para_plantio - area_ocupada
    
    def get_percentual_uso(self):
        """Retorna percentual de uso da área (considerando reserva)"""
        # Calcula área para plantio
        area_para_plantio = self.area_total - (self.area_reserva or Decimal('0'))
        
        # Calcula área ocupada
        area_ocupada = self.talhoes.filter(
            ativo=True
        ).aggregate(
            total=models.Sum('area_hac')
        )['total'] or Decimal('0')
        
        if area_para_plantio > 0:
            return (area_ocupada / area_para_plantio) * 100
        return 0


class Talhao(models.Model):
    """
    Talhões - divisões de uma Área para plantio
    Unidade básica de cultivo e rastreabilidade
    """
    objects = TalhaoManager()
    
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível para Plantio'),
        ('PREPARACAO', 'Em Preparação'),
        ('PLANTADO', 'Plantado'),
        ('COLHEITA', 'Em Colheita'),
        ('DESCANSO', 'Em Descanso/Pousio'),
        ('MANUTENCAO', 'Em Manutenção'),
    ]
    
    # Relacionamentos
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name='talhoes',
        verbose_name='Área'
    )
    
    fazenda = models.ForeignKey(
        Fazenda,
        on_delete=models.CASCADE,
        related_name='talhoes',
        verbose_name='Fazenda',
        help_text='Preenchido automaticamente pela área'
    )
    
    # Identificação
    nome = models.CharField(
        'Nome do Talhão',
        max_length=100,
        help_text='Ex: Talhão 01, Quadra A1, etc.'
    )
    
    codigo = models.CharField(
        'Código',
        max_length=20,
        help_text='Código único de identificação'
    )
    
    # Medidas
    area_hac = models.DecimalField(
        'Área (ha)',
        max_digits=10,
        decimal_places=4,
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text='Área em hectares'
    )
    
    # Geolocalização (centro do talhão)
    latitude = models.DecimalField(
        'Latitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )
    
    longitude = models.DecimalField(
        'Longitude',
        max_digits=10,
        decimal_places=7,
        blank=True,
        null=True
    )
    
    # Cultura atual (se houver)
    cultura_atual = models.ForeignKey(
        Cultura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='talhoes_ocupados',
        verbose_name='Cultura Atual',
        help_text='Cultura atualmente plantada neste talhão'
    )
    
    data_plantio_atual = models.DateField(
        'Data do Plantio Atual',
        blank=True,
        null=True,
        help_text='Data do plantio da cultura atual'
    )
    
    previsao_colheita = models.DateField(
        'Previsão de Colheita',
        blank=True,
        null=True,
        help_text='Previsão de colheita da safra atual'
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='DISPONIVEL'
    )
    
    ativo = models.BooleanField(
        'Talhão Ativo',
        default=True,
        help_text='Define se o talhão está disponível para uso'
    )
    
    pronto_para_plantio = models.BooleanField(
        'Pronto para Plantio',
        default=False,
        help_text='Define se a preparação do solo está concluída'
    )
    
    # Características
    declividade = models.CharField(
        'Declividade',
        max_length=50,
        blank=True,
        choices=[
            ('BAIXA', 'Baixa (0-5%)'),
            ('MEDIA', 'Média (5-15%)'),
            ('ALTA', 'Alta (>15%)'),
        ]
    )
    
    exposicao_solar = models.CharField(
        'Exposição Solar',
        max_length=50,
        blank=True,
        choices=[
            ('PLENA', 'Sol Pleno'),
            ('PARCIAL', 'Parcial'),
            ('SOMBRA', 'Sombreado'),
        ]
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    # Auditoria
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='talhoes',
        verbose_name='Empresa'
    )
    
    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='talhoes_cadastrados',
        verbose_name='Cadastrado por'
    )
    
    data_cadastro = models.DateTimeField(
        'Data de Cadastro',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        verbose_name = "Talhão"
        verbose_name_plural = "Talhões"
        ordering = ['fazenda__nome', 'area__nome', 'codigo']
        unique_together = [['fazenda', 'codigo']]
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['fazenda', 'status']),
            models.Index(fields=['area', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.area.nome} - {self.nome}"
    
    def save(self, *args, **kwargs):
        """Preenche fazenda automaticamente pela área"""
        if self.area and not self.fazenda_id:
            self.fazenda = self.area.fazenda
        
        # Preenche empresa
        if self.fazenda and not self.empresa_id:
            self.empresa = self.fazenda.empresa
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validações customizadas"""
        # Valida se área pertence à fazenda
        if self.area and self.fazenda:
            if self.area.fazenda != self.fazenda:
                raise ValidationError({
                    'area': 'A área selecionada não pertence a esta fazenda'
                })
        
        # Valida se código é único na fazenda
        if self.codigo:
            qs = Talhao.objects.filter(
                fazenda=self.fazenda,
                codigo=self.codigo
            ).exclude(pk=self.pk)
            
            if qs.exists():
                raise ValidationError({
                    'codigo': f'Já existe um talhão com código "{self.codigo}" nesta fazenda'
                })
    
    def pode_plantar(self):
        """Verifica se talhão está disponível para plantio"""
        return (
            self.ativo and 
            self.pronto_para_plantio and 
            self.status in ['DISPONIVEL', 'DESCANSO']
        )
    
    def iniciar_cultivo(self, cultura, data_plantio):
        """Registra início de cultivo no talhão"""
        self.cultura_atual = cultura
        self.data_plantio_atual = data_plantio
        self.status = 'PLANTADO'
        self.pronto_para_plantio = False
        
        # Calcula previsão de colheita se cultura tiver ciclo
        if cultura.dias_colheita:
            from datetime import timedelta
            self.previsao_colheita = data_plantio + timedelta(days=cultura.dias_colheita)
        
        self.save()
    
    def finalizar_cultivo(self):
        """Finaliza cultivo e libera talhão"""
        self.cultura_atual = None
        self.data_plantio_atual = None
        self.previsao_colheita = None
        self.status = 'DESCANSO'
        self.pronto_para_plantio = False
        self.save()
    
    def get_dias_cultivo(self):
        """Retorna dias desde o plantio"""
        if self.data_plantio_atual:
            from datetime import date
            return (date.today() - self.data_plantio_atual).days
        return None
    
    def get_dias_para_colheita(self):
        """Retorna dias para colheita prevista"""
        if self.previsao_colheita:
            from datetime import date
            dias = (self.previsao_colheita - date.today()).days
            return dias
        return None


class HistoricoTalhao(models.Model):
    """
    Histórico de cultivos em um talhão
    Rastreabilidade completa por safra
    """
    
    talhao = models.ForeignKey(
        Talhao,
        on_delete=models.CASCADE,
        related_name='historico',
        verbose_name='Talhão'
    )
    
    cultura = models.ForeignKey(
        Cultura,
        on_delete=models.PROTECT,
        related_name='historico_cultivos',
        verbose_name='Cultura'
    )
    
    variedade = models.CharField(
        'Variedade',
        max_length=100,
        blank=True,
        help_text='Variedade específica plantada'
    )
    
    # Datas
    data_plantio = models.DateField(
        'Data de Plantio',
        db_index=True
    )
    
    data_colheita = models.DateField(
        'Data de Colheita',
        blank=True,
        null=True
    )
    
    # Produção
    producao_estimada = models.DecimalField(
        'Produção Estimada (kg)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    producao_real = models.DecimalField(
        'Produção Real (kg)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Quantidade efetivamente colhida'
    )
    
    produtividade = models.DecimalField(
        'Produtividade (kg/ha)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Calculado automaticamente'
    )
    
    # Custos
    custo_total = models.DecimalField(
        'Custo Total (R$)',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Soma de todos os custos da safra'
    )
    
    custo_por_hectare = models.DecimalField(
        'Custo por Hectare (R$/ha)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Observações
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Anotações sobre a safra'
    )
    
    problemas_enfrentados = models.TextField(
        'Problemas Enfrentados',
        blank=True,
        help_text='Pragas, doenças, clima, etc.'
    )
    
    # Auditoria
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='historico_talhoes',
        verbose_name='Empresa'
    )
    
    registrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Registrado por'
    )
    
    data_registro = models.DateTimeField(
        'Data de Registro',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = "Histórico de Talhão"
        verbose_name_plural = "Históricos de Talhões"
        ordering = ['-data_plantio']
        indexes = [
            models.Index(fields=['talhao', '-data_plantio']),
            models.Index(fields=['empresa', '-data_plantio']),
        ]
    
    def __str__(self):
        return f"{self.talhao.nome} - {self.cultura.nome} ({self.data_plantio:%d/%m/%Y})"
    
    def save(self, *args, **kwargs):
        """Calcula automaticamente produtividade e custos"""
        # Calcula produtividade
        if self.producao_real and self.talhao.area_hac:
            self.produtividade = self.producao_real / self.talhao.area_hac
        
        # Calcula custo por hectare
        if self.custo_total and self.talhao.area_hac:
            self.custo_por_hectare = self.custo_total / self.talhao.area_hac
        
        # Preenche empresa
        if not self.empresa_id and self.talhao:
            self.empresa = self.talhao.empresa
        
        super().save(*args, **kwargs)
    
    def get_duracao_ciclo(self):
        """Retorna duração do ciclo em dias"""
        if self.data_colheita:
            return (self.data_colheita - self.data_plantio).days
        return None
    
    def get_eficiencia(self):
        """Compara produção real vs estimada"""
        if self.producao_real and self.producao_estimada and self.producao_estimada > 0:
            return (self.producao_real / self.producao_estimada) * 100
        return None


class Safra(models.Model):
    """Safra agrícola por fazenda e cultura"""
    STATUS = [
        ('PLANEJADA', 'Planejada'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('FINALIZADA', 'Finalizada'),
    ]

    nome = models.CharField('Nome da Safra', max_length=200, blank=True)
    fazenda = models.ForeignKey(Fazenda, on_delete=models.CASCADE, related_name='safras')
    cultura = models.ForeignKey(Cultura, on_delete=models.PROTECT, related_name='safras')
    ano = models.IntegerField('Ano', null=True, blank=True)
    periodo_inicio = models.DateField('Início', null=True, blank=True)
    periodo_fim = models.DateField('Fim', null=True, blank=True)
    talhoes = models.ManyToManyField(Talhao, related_name='safras', blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS, default='PLANEJADA')

    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Safra'
        verbose_name_plural = 'Safras'
        ordering = ['-ano', 'nome']

    def __str__(self):
        return self.nome or f"Safra {self.ano} - {self.fazenda.nome} - {self.cultura.nome}"

    def planned_production(self):
        try:
            return self.plano.planned_production
        except Exception:
            return None

    def real_production(self):
        from django.db.models import Sum
        total = SafraReal.objects.filter(safra=self).aggregate(Sum('production'))['production__sum']
        return total or Decimal('0')

    def production_variation_percent(self):
        planned = self.planned_production()
        real = self.real_production()
        if planned and planned > 0:
            return ((real - planned) / planned) * 100
        return None


class SafraPlan(models.Model):
    """Valores planejados para uma `Safra`"""
    safra = models.OneToOneField(Safra, on_delete=models.CASCADE, related_name='plano')
    planned_area = models.DecimalField('Área Planejada (ha)', max_digits=10, decimal_places=4, null=True, blank=True)
    planned_plantio = models.DateField('Plantio Previsto', null=True, blank=True)
    planned_colheita = models.DateField('Colheita Prevista', null=True, blank=True)
    planned_production = models.DecimalField('Produção Planejada (ton)', max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = 'Planejamento de Safra'
        verbose_name_plural = 'Planejamentos de Safra'

    def __str__(self):
        return f"Planejamento {self.safra}"


class SafraReal(models.Model):
    """Valores reais observados por `Safra` (opcional por `Talhao`)"""
    SOURCE_CHOICES = [
        ('AUTOMATIC', 'Automático'),
        ('MANUAL', 'Manual'),
        ('IMPORT', 'Importado'),
    ]

    safra = models.ForeignKey(Safra, on_delete=models.CASCADE, related_name='reais')
    talhao = models.ForeignKey(Talhao, on_delete=models.SET_NULL, null=True, blank=True, related_name='reais')
    actual_area = models.DecimalField('Área Real (ha)', max_digits=10, decimal_places=4, null=True, blank=True)
    plantio_real = models.DateField('Plantio Real', null=True, blank=True)
    colheita_real = models.DateField('Colheita Real', null=True, blank=True)
    production = models.DecimalField('Produção (ton)', max_digits=12, decimal_places=2, null=True, blank=True)
    source = models.CharField('Origem', max_length=20, choices=SOURCE_CHOICES, default='MANUAL')
    registrado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    data_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Valor Real de Safra'
        verbose_name_plural = 'Valores Reais de Safra'

    def __str__(self):
        if self.talhao:
            return f"Real {self.safra} - {self.talhao}"
        return f"Real {self.safra}"


class Requisicao(models.Model):
    """Requisicao base para consumo interno e safra"""

    TIPO_CHOICES = [
        ('INSUMO_SAFRA', 'Insumo Safra'),
        ('EPI', 'EPI'),
        ('ABASTECIMENTO', 'Abastecimento'),
        ('EXPEDIENTE', 'Material de Expediente'),
        ('EMPRESTIMO', 'Emprestimo de Material'),
    ]

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADA', 'Aprovada'),
        ('ATENDIDA', 'Atendida'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='requisicoes',
        verbose_name='Empresa'
    )
    numero = models.CharField('Numero', max_length=20, unique=True)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='INSUMO_SAFRA')
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='PENDENTE')

    # Vinculos agricolas
    safra = models.ForeignKey('cadastros.Safra', on_delete=models.SET_NULL, null=True, blank=True)
    fazenda = models.ForeignKey('cadastros.Fazenda', on_delete=models.SET_NULL, null=True, blank=True)
    talhao = models.ForeignKey('cadastros.Talhao', on_delete=models.SET_NULL, null=True, blank=True)

    # Campos opcionais para tipos especificos (podem ser refinados em detalhes futuros)
    funcionario_destino = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_destino',
        verbose_name='Funcionario Destino'
    )
    parceiro = models.ForeignKey(
        'cadastros.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_emprestimo',
        verbose_name='Parceiro'
    )
    veiculo = models.ForeignKey(
        'cadastros.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_abastecimento',
        verbose_name='Veiculo'
    )
    horimetro = models.DecimalField('Horimetro', max_digits=10, decimal_places=2, null=True, blank=True)
    odometro = models.DecimalField('Odometro', max_digits=10, decimal_places=2, null=True, blank=True)

    # Centro de custo (opcional enquanto modulo nao existe)
    centro_custo_nome = models.CharField('Centro de Custo', max_length=120, blank=True)

    solicitante = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_solicitadas',
        verbose_name='Solicitante'
    )
    aprovador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requisicoes_aprovadas',
        verbose_name='Aprovador'
    )
    data_requisicao = models.DateTimeField('Data da Requisicao', auto_now_add=True)
    data_aprovacao = models.DateTimeField('Data de Aprovacao', null=True, blank=True)
    observacoes = models.TextField('Observacoes', blank=True)

    class Meta:
        verbose_name = 'Requisicao'
        verbose_name_plural = 'Requisicoes'
        ordering = ['-data_requisicao']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'tipo']),
        ]

    def __str__(self):
        return f"{self.numero} - {self.get_tipo_display()}"


class RequisicaoItem(models.Model):
    """Itens da requisicao"""

    requisicao = models.ForeignKey(
        'cadastros.Requisicao',
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Requisicao'
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='requisicoes_itens',
        verbose_name='Produto'
    )
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        related_name='requisicoes_itens',
        verbose_name='Unidade'
    )
    quantidade_solicitada = models.DecimalField('Quantidade Solicitada', max_digits=15, decimal_places=3)
    quantidade_atendida = models.DecimalField('Quantidade Atendida', max_digits=15, decimal_places=3, default=0)
    custo_estimado = models.DecimalField('Custo Estimado', max_digits=15, decimal_places=2, null=True, blank=True)
    observacoes = models.TextField('Observacoes', blank=True)

    class Meta:
        verbose_name = 'Item de Requisicao'
        verbose_name_plural = 'Itens de Requisicao'
        indexes = [
            models.Index(fields=['produto']),
        ]

    def __str__(self):
        return f"{self.requisicao.numero} - {self.produto.nome}"



"""
ADICIONAR ESTE CÓDIGO AO FINAL DO ARQUIVO: cadastros/models.py

Copie todo o código abaixo e cole no final do seu arquivo models.py existente
"""




"""
SUBSTITUA TODO O CONTEÚDO que você colou anteriormente NO FINAL do arquivo cadastros/models.py
por este código completo e corrigido.

CORREÇÕES APLICADAS:
✅ Removida validação restritiva de telefone (telefone_validator)
✅ Adicionado método tem_passaporte_valido()
✅ Todos os outros métodos mantidos

COMO USAR:
1. Abra: cadastros/models.py
2. Apague TODO o código de Vendedor que você colou antes
3. Cole este código completo no FINAL do arquivo
4. Salve
5. Reinicie o servidor
"""


# ========================================================================
# VENDEDORES - GESTÃO DE VENDEDORES (MERCADO INTERNO E EXPORTAÇÃO)
# ========================================================================

class VendedorQuerySet(models.QuerySet):
    """QuerySet customizado para filtrar vendedores por empresa"""
    
    def da_empresa(self, empresa):
        """Filtra vendedores da empresa especificada"""
        if empresa:
            return self.filter(empresa=empresa)
        return self.none()
    
    def ativos(self):
        """Retorna apenas vendedores ativos"""
        return self.filter(status='ATIVO')
    
    def inativos(self):
        """Retorna vendedores inativos"""
        return self.filter(status='INATIVO')
    
    def mercado_interno(self):
        """Vendedores que atuam no mercado interno"""
        return self.filter(tipo_mercado__in=['INTERNO', 'AMBOS'])
    
    def mercado_externo(self):
        """Vendedores que atuam em exportação"""
        return self.filter(tipo_mercado__in=['EXTERNO', 'AMBOS'])


class VendedorManager(models.Manager):
    """Manager customizado para Vendedor"""
    
    def get_queryset(self):
        return VendedorQuerySet(self.model, using=self._db)
    
    def da_empresa(self, empresa):
        return self.get_queryset().da_empresa(empresa)
    
    def ativos(self):
        return self.get_queryset().ativos()
    
    def mercado_interno(self):
        return self.get_queryset().mercado_interno()
    
    def mercado_externo(self):
        return self.get_queryset().mercado_externo()


class Vendedor(models.Model):
    """
    Modelo de Vendedor para mercado interno e exportação
    Sistema multi-tenant - cada empresa tem seus próprios vendedores
    Preparado para futura integração com Portal do Vendedor
    """
    
    # Tipos de mercado
    TIPO_MERCADO = [
        ('INTERNO', 'Mercado Interno'),
        ('EXTERNO', 'Exportação'),
        ('AMBOS', 'Interno + Exportação'),
    ]
    
    # Tipos de vínculo
    TIPO_VINCULO = [
        ('CLT', 'CLT'),
        ('AUTONOMO', 'Autônomo/Comissionado'),
        ('PJ', 'Pessoa Jurídica (Representante)'),
    ]
    
    # Status
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('FERIAS', 'Férias'),
        ('AFASTADO', 'Afastado'),
    ]
    
    # Tipo de conta bancária
    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Conta Poupança'),
    ]
    
    # Forma de pagamento de comissão
    FORMA_PAGAMENTO_COMISSAO = [
        ('MENSAL', 'Mensal'),
        ('QUINZENAL', 'Quinzenal'),
        ('POR_VENDA', 'Por Venda Realizada'),
        ('TRIMESTRAL', 'Trimestral'),
    ]
    
    # Moeda padrão
    MOEDA_CHOICES = [
        ('BRL', 'Real (BRL)'),
        ('USD', 'Dólar (USD)'),
        ('EUR', 'Euro (EUR)'),
    ]
    
    # Nível de autonomia
    NIVEL_AUTONOMIA = [
        ('ILIMITADO', 'Sem Limite (Aprovação Automática)'),
        ('ATE_50K', 'Até R$ 50.000'),
        ('ATE_100K', 'Até R$ 100.000'),
        ('PRECISA_APROVACAO', 'Precisa Aprovação Gerencial'),
    ]
    
    # ===== RELACIONAMENTOS MULTI-TENANT =====
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='vendedores',
        verbose_name='Empresa',
        help_text='Empresa à qual o vendedor pertence'
    )
    
    # Preparado para futura integração com usuário
    usuario = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendedor_profile',
        verbose_name='Usuário do Sistema',
        help_text='Vincular quando vendedor tiver acesso ao Portal do Vendedor'
    )
    
    # ===== IDENTIFICAÇÃO BÁSICA =====
    nome_completo = models.CharField(
        'Nome Completo',
        max_length=200,
        help_text='Nome completo do vendedor'
    )
    
    cpf_validator = RegexValidator(
        regex=r'^\d{11}$',
        message="CPF deve conter 11 dígitos (apenas números)"
    )
    cpf = models.CharField(
        'CPF',
        max_length=14,
        validators=[cpf_validator],
        help_text='Formato: apenas números (será formatado automaticamente)'
    )
    
    rg = models.CharField(
        'RG',
        max_length=20,
        blank=True,
        null=True,
        help_text='Registro Geral'
    )
    
    data_nascimento = models.DateField(
        'Data de Nascimento',
        blank=True,
        null=True
    )
    
    foto = models.ImageField(
        'Foto',
        upload_to='vendedores/fotos/',
        blank=True,
        null=True,
        help_text='Foto do vendedor'
    )
    
    # ===== TIPO DE VENDEDOR =====
    tipo_mercado = models.CharField(
        'Tipo de Mercado',
        max_length=10,
        choices=TIPO_MERCADO,
        default='INTERNO',
        help_text='Mercado de atuação do vendedor'
    )
    
    tipo_vinculo = models.CharField(
        'Tipo de Vínculo',
        max_length=10,
        choices=TIPO_VINCULO,
        default='CLT',
        help_text='Tipo de relação trabalhista'
    )
    
    # ===== CONTATO (SEM VALIDAÇÃO RESTRITIVA) =====
    telefone_principal = models.CharField(
        'Telefone Principal',
        max_length=20,
        help_text='Telefone principal de contato'
    )
    
    telefone_secundario = models.CharField(
        'Telefone Secundário',
        max_length=20,
        blank=True,
        null=True
    )
    
    email_corporativo = models.EmailField(
        'E-mail Corporativo',
        help_text='E-mail institucional da empresa'
    )
    
    email_pessoal = models.EmailField(
        'E-mail Pessoal',
        blank=True,
        null=True,
        help_text='E-mail pessoal do vendedor'
    )
    
    whatsapp = models.CharField(
        'WhatsApp Business',
        max_length=20,
        blank=True,
        null=True,
        help_text='Link direto: https://wa.me/5584999999999'
    )
    
    # ===== ENDEREÇO =====
    cep = models.CharField(
        'CEP',
        max_length=10,
        blank=True,
        null=True
    )
    
    logradouro = models.CharField(
        'Logradouro',
        max_length=200,
        blank=True,
        null=True
    )
    
    numero = models.CharField(
        'Número',
        max_length=10,
        blank=True,
        null=True
    )
    
    complemento = models.CharField(
        'Complemento',
        max_length=100,
        blank=True,
        null=True
    )
    
    bairro = models.CharField(
        'Bairro',
        max_length=100,
        blank=True,
        null=True
    )
    
    cidade = models.CharField(
        'Cidade',
        max_length=100,
        blank=True,
        null=True
    )
    
    uf = models.CharField(
        'UF',
        max_length=2,
        blank=True,
        null=True,
        help_text='Sigla do estado'
    )
    
    pais = models.CharField(
        'País',
        max_length=100,
        default='Brasil',
        help_text='Importante para vendedores internacionais'
    )
    
    # ===== DADOS COMERCIAIS =====
    comissao_mercado_interno = models.DecimalField(
        'Comissão Mercado Interno (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Percentual padrão de comissão sobre vendas internas'
    )
    
    comissao_exportacao = models.DecimalField(
        'Comissão Exportação (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Percentual padrão de comissão sobre exportações'
    )
    
    comissao_fixa_mensal = models.DecimalField(
        'Comissão Fixa Mensal (R$)',
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor fixo mensal (se aplicável)'
    )
    
    meta_mensal = models.DecimalField(
        'Meta Mensal',
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Meta de vendas do mês (em R$ ou US$ conforme moeda padrão)'
    )
    
    moeda_padrao = models.CharField(
        'Moeda Padrão de Trabalho',
        max_length=3,
        choices=MOEDA_CHOICES,
        default='BRL',
        help_text='Moeda padrão para metas e comissões'
    )
    
    forma_pagamento_comissao = models.CharField(
        'Forma de Pagamento Comissão',
        max_length=15,
        choices=FORMA_PAGAMENTO_COMISSAO,
        default='MENSAL',
        help_text='Periodicidade de pagamento da comissão'
    )
    
    regioes_atuacao = models.TextField(
        'Regiões de Atuação',
        blank=True,
        help_text='Ex: Norte, Sul, Nordeste, etc. (separar por vírgula)'
    )
    
    paises_atuacao = models.TextField(
        'Países de Atuação',
        blank=True,
        help_text='Para exportação: USA, Europa, Ásia, etc. (separar por vírgula)'
    )
    
    # ===== DADOS BANCÁRIOS =====
   
    banco = models.CharField('Banco', max_length=100, blank=True)
    agencia = models.CharField('Agência', max_length=10, blank=True)
    conta_bancaria = models.CharField('Conta', max_length=20, blank=True)
    tipo_conta_bancaria = models.CharField(
    'Tipo de Conta',
    max_length=10,
    choices=TIPO_CONTA,  # já existe no modelo
    blank=True
    )
    pix = models.CharField('PIX', max_length=100, blank=True)
    
    pix = models.CharField(
        'Chave PIX',
        max_length=100,
        blank=True,
        null=True,
        help_text='CPF, E-mail, Telefone ou Chave Aleatória'
    )
    
    # ===== DOCUMENTAÇÃO (ESPECIAL PARA EXPORTAÇÃO) =====
    passaporte_numero = models.CharField(
        'Número do Passaporte',
        max_length=20,
        blank=True,
        null=True
    )
    
    passaporte_validade = models.DateField(
        'Validade do Passaporte',
        blank=True,
        null=True
    )
    
    visto_trabalho = models.CharField(
        'Visto de Trabalho',
        max_length=100,
        blank=True,
        null=True,
        help_text='Se aplicável para viagens internacionais'
    )
    
    cnh = models.CharField(
        'CNH',
        max_length=20,
        blank=True,
        null=True,
        help_text='Carteira Nacional de Habilitação'
    )
    
    certificacoes = models.TextField(
        'Certificações',
        blank=True,
        help_text='SISCOMEX, Comércio Exterior, etc.'
    )
    
    # ===== HIERARQUIA E GESTÃO =====
    supervisor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinados',
        verbose_name='Supervisor/Gerente',
        help_text='Gerente de vendas responsável'
    )
    
    nivel_autonomia = models.CharField(
        'Nível de Autonomia',
        max_length=20,
        choices=NIVEL_AUTONOMIA,
        default='PRECISA_APROVACAO',
        help_text='Define limite de aprovação de vendas'
    )
    
    acesso_crm = models.BooleanField(
        'Acesso ao CRM Completo',
        default=False,
        help_text='Pode visualizar todas as negociações da empresa'
    )
    
    # ===== CONTROLE ADMINISTRATIVO =====
    data_admissao = models.DateField(
        'Data de Admissão',
        help_text='Data de entrada na empresa'
    )
    
    data_desligamento = models.DateField(
        'Data de Desligamento',
        blank=True,
        null=True,
        help_text='Data de saída da empresa (se aplicável)'
    )
    
    status = models.CharField(
        'Status',
        max_length=10,
        choices=STATUS_CHOICES,
        default='ATIVO',
        help_text='Situação atual do vendedor'
    )
    
    # ===== OBSERVAÇÕES E IDIOMAS =====
    observacoes = models.TextField(
        'Observações Gerais',
        blank=True,
        help_text='Informações adicionais sobre o vendedor'
    )
    
    idiomas = models.TextField(
        'Idiomas',
        blank=True,
        help_text='Ex: Português, Inglês (fluente), Espanhol (intermediário)'
    )
    
    experiencia_anos = models.IntegerField(
        'Experiência (anos)',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Anos de experiência em vendas'
    )
    
    # ===== AUDITORIA =====
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendedores_criados',
        verbose_name='Criado por'
    )
    
    # Manager customizado
    objects = VendedorManager()
    
    class Meta:
        verbose_name = "Vendedor"
        verbose_name_plural = "Vendedores"
        ordering = ['empresa__nome', 'nome_completo']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['empresa', 'tipo_mercado']),
            models.Index(fields=['cpf']),
            models.Index(fields=['email_corporativo']),
        ]
        unique_together = [
            ['empresa', 'cpf'],
            ['empresa', 'email_corporativo'],
        ]
    
    def __str__(self):
        return f"{self.nome_completo} - {self.empresa.nome}"
    
    def clean(self):
        """Validações customizadas"""
        if self.cpf:
            self.cpf = re.sub(r'\D', '', self.cpf)
            if len(self.cpf) != 11:
                raise ValidationError({'cpf': 'CPF deve ter 11 dígitos'})
        
        if self.data_desligamento and self.data_admissao:
            if self.data_desligamento < self.data_admissao:
                raise ValidationError({
                    'data_desligamento': 'Data de desligamento não pode ser anterior à admissão'
                })
    
    def save(self, *args, **kwargs):
        if self.cpf:
            self.cpf = re.sub(r'\D', '', self.cpf)
        
        if self.data_desligamento and self.status != 'INATIVO':
            self.status = 'INATIVO'
        
        super().save(*args, **kwargs)
    
    def get_cpf_formatado(self):
        """Retorna CPF formatado: 000.000.000-00"""
        if self.cpf and len(self.cpf) == 11:
            return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"
        return self.cpf
    
    def get_nome_curto(self):
        """Retorna primeiro e último nome"""
        partes = self.nome_completo.split()
        if len(partes) > 1:
            return f"{partes[0]} {partes[-1]}"
        return self.nome_completo
    
    def get_total_subordinados(self):
        """Retorna número de vendedores sob supervisão"""
        return self.subordinados.filter(status='ATIVO').count()
    
    def is_gerente(self):
        """Verifica se é gerente de vendas"""
        return self.subordinados.exists()
    
    def pode_aprovar_venda(self, valor):
        """Verifica se vendedor pode aprovar venda de determinado valor"""
        if self.nivel_autonomia == 'ILIMITADO':
            return True
        elif self.nivel_autonomia == 'ATE_50K':
            return valor <= 50000
        elif self.nivel_autonomia == 'ATE_100K':
            return valor <= 100000
        else:
            return False
    
    def tem_passaporte_valido(self):
        """
        ✅ MÉTODO ADICIONADO - CORREÇÃO DO PASSAPORTE
        Verifica se o passaporte está válido (não vencido)
        """
        if not self.passaporte_validade:
            return False
        
        from django.utils import timezone
        hoje = timezone.now().date()
        
        return self.passaporte_validade >= hoje


class ComissaoVendedor(models.Model):
    """
    Histórico de comissões pagas aos vendedores
    Será totalmente implementado quando houver módulo financeiro
    """
    
    STATUS_COMISSAO = [
        ('PENDENTE', 'Pendente'),
        ('PAGA', 'Paga'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    vendedor = models.ForeignKey(
        Vendedor,
        on_delete=models.CASCADE,
        related_name='comissoes',
        verbose_name='Vendedor'
    )
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='comissoes_vendedores',
        verbose_name='Empresa'
    )
    
    referencia_mes = models.DateField(
        'Mês de Referência',
        help_text='Mês ao qual a comissão se refere'
    )
    
    valor_base = models.DecimalField(
        'Valor Base (Vendas)',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Total de vendas que geraram a comissão'
    )
    
    percentual = models.DecimalField(
        'Percentual (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    valor_comissao = models.DecimalField(
        'Valor da Comissão',
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Valor calculado da comissão'
    )
    
    status = models.CharField(
        'Status',
        max_length=15,
        choices=STATUS_COMISSAO,
        default='PENDENTE'
    )
    
    data_pagamento = models.DateField(
        'Data de Pagamento',
        blank=True,
        null=True
    )
    
    observacoes = models.TextField(
        'Observações',
        blank=True
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = "Comissão de Vendedor"
        verbose_name_plural = "Comissões de Vendedores"
        ordering = ['-referencia_mes', 'vendedor__nome_completo']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['vendedor', 'referencia_mes']),
        ]
    
    def __str__(self):
        return f"{self.vendedor.nome_completo} - {self.referencia_mes:%m/%Y} - R$ {self.valor_comissao}"
    
    def save(self, *args, **kwargs):
        if self.valor_base and self.percentual:
            self.valor_comissao = (self.valor_base * self.percentual) / 100
        
        if not self.empresa_id and self.vendedor_id:
            self.empresa = self.vendedor.empresa
        
        super().save(*args, **kwargs)



"""
=============================================================================
📝 MODELOS DE FORNECEDOR - SCAFFOLD
=============================================================================

Modelos de Fornecedor (nacional e internacional) com endereços múltiplos
prontos para serem usados pelo módulo de Fornecedores e pelo futuro Portal
do Fornecedor. Inclui: `Fornecedor` e `FornecedorEndereco`.

Notas de design:
- Multi-tenant via campo `empresa` (mesmo padrão dos outros modelos)
- Identificador fiscal por empresa é único (constraint)
- Endereços são mantidos em tabela separada (múltiplos tipos: billing/shipping)
- Campos de portal (portal_enabled, portal_user, portal_token) para futura integração

"""


class Fornecedor(models.Model):
    """
    Fornecedores (Nacional / Internacional)
    Preparado para integração com Portal do Fornecedor
    """

    TIPO_PESSOA = [
        ('PF', 'Pessoa Física'),
        ('PJ', 'Pessoa Jurídica'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='fornecedores',
        verbose_name='Empresa'
    )

    nome = models.CharField('Nome/Razão Social', max_length=200)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=200, blank=True)

    tipo_pessoa = models.CharField('Tipo de Pessoa', max_length=2, choices=TIPO_PESSOA, default='PJ')

    cnpj_cpf = models.CharField('CNPJ/CPF', max_length=18, help_text='Formato: 00.000.000/0000-00 ou 000.000.000-00', blank=True)
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=50, blank=True)

    # Campos de contato básicos
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20, blank=True, 
                               help_text='Formato: (00) 00000-0000 - Usado para envio de pedidos via WhatsApp')
    email = models.EmailField('E-mail', blank=True)

    # Campos de endereço espelhados (conveniência) — dados primários do fornecedor
    cep = models.CharField('CEP', max_length=10, blank=True)
    endereco = models.CharField('Endereço', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')

    # Comercial / exportação
    is_exportador = models.BooleanField('Exportador', default=False)
    moeda_padrao = models.CharField('Moeda Padrão', max_length=3, default='BRL')
    porto_preferencial = models.CharField('Porto Preferencial', max_length=100, blank=True)
    website = models.URLField('Website', blank=True)

    # Regime Tributário (adicionado para documentos e formulário)
    REGIME_TRIBUTARIO = [
        ('SIMPLES', 'Simples Nacional'),
        ('PRESUMIDO', 'Lucro Presumido'),
        ('REAL', 'Lucro Real'),
        ('MEI', 'Microempreendedor Individual'),
        ('PRODUTOR_RURAL', 'Produtor Rural (Pessoa Física)'),
    ]
    regime_tributario = models.CharField('Regime Tributário', max_length=20, choices=REGIME_TRIBUTARIO, default='PRODUTOR_RURAL')

    # Portal readiness
    portal_enabled = models.BooleanField('Portal Habilitado', default=False)
    portal_user = models.OneToOneField(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fornecedor_profile',
        verbose_name='Usuário Portal'
    )
    portal_token = models.CharField('Token Portal/API', max_length=200, blank=True, null=True, help_text='Token temporário para integração API/Portal')

    ativa = models.BooleanField('Fornecedor Ativo', default=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fornecedores_criados',
        verbose_name='Criado por'
    )

    objects = models.Manager()

    class Meta:
        verbose_name = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['cnpj_cpf']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'cnpj_cpf'], name='unique_fornecedor_por_empresa')
        ]

    def __str__(self):
        return self.nome

    def get_nome_exibicao(self):
        """Retorna nome de exibição: prefere `nome_fantasia` se disponível"""
        return self.nome_fantasia or self.nome

    def get_cnpj_cpf_formatado(self):
        """Formata CNPJ/CPF como na `Fazenda`"""
        import re
        doc = re.sub(r'\D', '', (self.cnpj_cpf or ''))
        if len(doc) == 14:  # CNPJ
            return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        elif len(doc) == 11:  # CPF
            return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
        return self.cnpj_cpf or ''

    def get_primary_address(self):
        """Retorna o endereço principal: preferencialmente o endereço espelhado no fornecedor,
        senão busca o endereço padrão em `FornecedorEndereco` (padrao=True)."""
        if self.endereco or self.cep:
            return {
                'cep': self.cep or '',
                'logradouro': self.endereco or '',
                'numero': self.numero or '',
                'complemento': self.complemento or '',
                'bairro': self.bairro or '',
                'cidade': self.cidade or '',
                'uf': self.uf or '',
                'pais': self.pais or ''
            }
        fe = self.enderecos.filter(padrao=True).first()
        if fe:
            return fe.to_dict()
        return None

    def save(self, *args, **kwargs):
        """Ao salvar o Fornecedor, se houver alterações nos campos de endereço espelhados,
        cria/atualiza o `FornecedorEndereco` padrão para manter os dados consistentes.

        Observações sobre sincronização (bidirecional):
        - `Fornecedor.save()` cria/atualiza o `FornecedorEndereco` com `padrao=True` quando os campos
          espelhados (`cep`, `endereco`, `numero`, etc.) mudam — isso garante que o endereço padrão
          esteja sempre alinhado ao registro principal do fornecedor.
        - Sinais (`cadastros.signals`) escutam `post_save` e `post_delete` em `FornecedorEndereco`:
          quando um endereço com `padrao=True` é salvo/alterado, os campos espelhados no `Fornecedor`
          são atualizados automaticamente; quando o endereço padrão é deletado, promovemos outro
          endereço ou limpamos os campos espelhados.

        Esse mecanismo evita divergência de dados entre `Fornecedor` e `FornecedorEndereco` e mantém
        comportamento previsível ao criar, editar ou remover endereços."""
        address_fields = ['cep', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'uf', 'pais']
        old = None
        if self.pk:
            try:
                old = Fornecedor.objects.get(pk=self.pk)
            except Fornecedor.DoesNotExist:
                old = None

        if old:
            changed = any(((getattr(old, f) or '').strip()) != ((getattr(self, f) or '').strip()) for f in address_fields)
        else:
            # Nova instância: se houver qualquer campo de endereço preenchido, considera alteração
            changed = any((getattr(self, f) or '').strip() for f in address_fields)

        super().save(*args, **kwargs)

        if changed:
            defaults = {
                'cep': self.cep or '',
                'logradouro': self.endereco or '',
                'numero': self.numero or '',
                'complemento': self.complemento or '',
                'bairro': self.bairro or '',
                'cidade': self.cidade or '',
                'uf': self.uf or '',
                'pais': self.pais or ''
            }
            # Import dentro do método para evitar problemas de import circular em tempo de carregamento
            from .models import FornecedorEndereco
            FornecedorEndereco.objects.update_or_create(fornecedor=self, padrao=True, defaults=defaults)

    # Novos campos para as classificações e categorias do fornecedor
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=20, blank=True)
    eori = models.CharField('Código EORI', max_length=20, blank=True, help_text='Economic Operators Registration and Identification (para exportação)')
    categorias = models.ManyToManyField('CategoriaFornecedor', blank=True, related_name='fornecedores')
    subcategorias = models.ManyToManyField('SubcategoriaFornecedor', blank=True, related_name='fornecedores' )
    classificacao_risco = models.CharField('Classificação de Risco', max_length=10, choices=[('BAIXO','Baixo'), ('MEDIO','Médio'), ('ALTO','Alto')], blank=True)
    data_homologacao = models.DateField('Data de Homologação', null=True, blank=True)
    validade_homologacao = models.DateField('Validade da Homologação', null=True, blank=True)
    limite_credito = models.DecimalField('Limite de Crédito Aprovado', max_digits=14, decimal_places=2, default=0, blank=True, null=True)
    prazo_pagamento_padrao = models.IntegerField('Prazo de Pagamento Padrão (dias)', null=True, blank=True)
    prazo_entrega_medio = models.IntegerField('Prazo de Entrega Médio (dias)', null=True, blank=True)
    observacoes = models.TextField('Observações Gerais', blank=True)

    @property
    def status(self):
        """Status legível usado pelas templates (mantém compatibilidade com verificações existentes)"""
        return 'ATIVO' if self.ativa else 'INATIVO'


class CategoriaFornecedor(models.Model):
    """Categorias para classificar fornecedores (ex: Insumos, Máquinas, Serviços)"""
    nome = models.CharField('Nome', max_length=100)
    icone = models.CharField('Ícone', max_length=50, blank=True, help_text='Emoji ou classe de ícone')
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, null=True, blank=True, related_name='categorias_fornecedor', verbose_name='Empresa')
    ativa = models.BooleanField('Categoria Ativa', default=True)

    class Meta:
        verbose_name = 'Categoria de Fornecedor'
        verbose_name_plural = 'Categorias de Fornecedores'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Armador(models.Model):
    """Cadastro de Armadores (Shipping Companies) - RF-028, RF-308, RF-805, RF-808"""
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='armadores',
        verbose_name='Empresa'
    )
    
    # Identidade
    codigo = models.CharField(
        'Código',
        max_length=20,
        help_text='Código único do armador por empresa'
    )
    nome = models.CharField('Nome da Armadora', max_length=200)
    nome_fantasia = models.CharField(
        'Nome Fantasia',
        max_length=200,
        blank=True
    )
    cnpj = models.CharField(
        'CNPJ',
        max_length=20,
        blank=True,
        help_text='CNPJ (opcional para armadores estrangeiros)'
    )
    
    # Localização
    pais = models.CharField('País de Origem', max_length=100, default='Brasil')
    website = models.URLField('Website', blank=True)
    
    # Endereço Principal (espelhado para conveniência)
    cep = models.CharField('CEP', max_length=10, blank=True)
    endereco = models.CharField('Endereço', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True, choices=UF_CHOICES, default='')
    
    # Contato Principal (espelhado para conveniência)
    email = models.EmailField('Email', blank=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20, blank=True)
    
    # Operacional
    tipos_navio = models.ManyToManyField(
        'cadastros.TipoNavio',
        related_name='armadores',
        blank=True,
        verbose_name='Tipos de Navio'
    )
    
    # Indicadores (RF-808: Indicadores por armador)
    confiabilidade_percentual = models.FloatField(
        'Confiabilidade (%)',
        default=100.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentual de confiabilidade do armador'
    )
    percentual_rolagem_historico = models.FloatField(
        'Percentual de Rolagem Histórico (%)',
        default=0.0,
        validators=[MinValueValidator(0)],
        help_text='Percentual histórico de rolagens de containers'
    )
    custo_medio_rolagem = models.DecimalField(
        'Custo Médio por Rolagem (USD)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Status
    ativo = models.BooleanField('Ativo', default=True)
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    criado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='armadores_criados',
        verbose_name='Criado por'
    )
    
    class Meta:
        verbose_name = 'Armador'
        verbose_name_plural = 'Armadores'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'codigo']),
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['cnpj']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                name='unique_armador_por_empresa'
            ),
            models.UniqueConstraint(
                fields=['empresa', 'cnpj'],
                condition=models.Q(cnpj__gt=''),
                name='unique_cnpj_armador_por_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"
    
    def get_nome_exibicao(self):
        """Retorna nome de exibição: prefere `nome_fantasia` se disponível"""
        return self.nome_fantasia or self.nome
    
    def get_cnpj_formatado(self):
        """Formata CNPJ como XX.XXX.XXX/XXXX-XX"""
        import re
        doc = re.sub(r'\D', '', (self.cnpj or ''))
        if len(doc) == 14:
            return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
        return self.cnpj or ''


class Navio(models.Model):
    """Cadastro de Navios - RF-028"""
    
    TIPO_CHOICES = [
        ('CONTAINER', 'Container'),
        ('REEFER', 'Refrigerado'),
        ('BREAKBULK', 'Break Bulk'),
        ('MULTIPURPOSE', 'Multipropósito'),
        ('GENERAL', 'Carga Geral'),
        ('TANKER', 'Tanque'),
        ('RoRo', 'Roll On Roll Off'),
    ]
    
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
        ('MANUTENCAO', 'Em Manutenção'),
        ('DESCARTE', 'Para Descarte'),
    ]
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='navios',
        verbose_name='Empresa'
    )
    
    armador = models.ForeignKey(
        'cadastros.Armador',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='navios',
        verbose_name='Armador'
    )
    
    # Identidade
    codigo = models.CharField(
        'Código/Nome do Navio',
        max_length=50,
        help_text='Nome ou código único do navio'
    )
    nome = models.CharField('Nome do Navio', max_length=200)
    imo = models.CharField(
        'IMO (International Maritime Organization)',
        max_length=10,
        blank=True,
        help_text='Número IMO do navio'
    )
    bandeira = models.CharField(
        'País de Bandeira',
        max_length=100,
        help_text='País de registro da embarcação'
    )
    
    # Características
    tipo = models.CharField(
        'Tipo de Navio',
        max_length=20,
        choices=TIPO_CHOICES,
        default='CONTAINER'
    )
    capacidade_containers = models.IntegerField(
        'Capacidade (TEUs)',
        blank=True,
        null=True,
        help_text='Capacidade em Twenty-foot Equivalent Units'
    )
    capacidade_toneladas = models.DecimalField(
        'Capacidade (Toneladas)',
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )
    ano_construcao = models.IntegerField(
        'Ano de Construção',
        blank=True,
        null=True
    )
    comprimento_metros = models.DecimalField(
        'Comprimento (metros)',
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True
    )
    
    # Operacional
    velocidade_media_nós = models.DecimalField(
        'Velocidade Média (nós)',
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True
    )
    portos_operacao = models.ManyToManyField(
        'cadastros.Porto',
        related_name='navios_operacao',
        blank=True,
        verbose_name='Portos de Operação'
    )
    
    # Status
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS_CHOICES,
        default='ATIVO'
    )
    ativo = models.BooleanField('Ativo', default=True)
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Navio'
        verbose_name_plural = 'Navios'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'codigo']),
            models.Index(fields=['empresa', 'armador']),
            models.Index(fields=['empresa', 'ativo']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                name='unique_navio_por_empresa'
            )
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class ArmadorEndereco(models.Model):
    """Endereços múltiplos para Armador (matriz, filial, operacional)"""

    TIPO_ENDERECO = [
        ('MATRIZ', 'Matriz'),
        ('FILIAL', 'Filial'),
        ('OPERACIONAL', 'Operacional'),
        ('FATURAMENTO', 'Faturamento'),
        ('ENTREGA', 'Entrega'),
    ]

    armador = models.ForeignKey(
        'cadastros.Armador',
        on_delete=models.CASCADE,
        related_name='enderecos',
        verbose_name='Armador'
    )

    tipo = models.CharField(
        'Tipo',
        max_length=20,
        choices=TIPO_ENDERECO,
        default='OPERACIONAL'
    )

    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField('Logradouro', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')

    padrao = models.BooleanField('Endereço Padrão', default=False)
    preenchido_via_api = models.BooleanField('Preenchido via API (ViaCEP)', default=False)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Endereço do Armador'
        verbose_name_plural = 'Endereços do Armador'
        ordering = ['-padrao', 'cidade', 'tipo']
        indexes = [
            models.Index(fields=['armador', 'padrao']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cidade}/{self.uf} - {self.armador.nome}"

    def save(self, *args, **kwargs):
        """Garante apenas um endereço padrão por armador"""
        if self.padrao:
            ArmadorEndereco.objects.filter(armador=self.armador, padrao=True).update(padrao=False)
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'cep': self.cep or '',
            'logradouro': self.logradouro or '',
            'numero': self.numero or '',
            'complemento': self.complemento or '',
            'bairro': self.bairro or '',
            'cidade': self.cidade or '',
            'uf': self.uf or '',
            'pais': self.pais or ''
        }


class ArmadorContato(models.Model):
    """Contatos múltiplos para Armador"""

    TIPO_CONTATO = [
        ('PRINCIPAL', 'Contato Principal'),
        ('FINANCEIRO', 'Financeiro'),
        ('OPERACIONAL', 'Operacional'),
        ('COMERCIAL', 'Comercial'),
        ('TÉCNICO', 'Técnico'),
        ('EMERGÊNCIA', 'Emergência'),
    ]

    armador = models.ForeignKey(
        'cadastros.Armador',
        on_delete=models.CASCADE,
        related_name='contatos',
        verbose_name='Armador'
    )

    tipo = models.CharField(
        'Tipo de Contato',
        max_length=20,
        choices=TIPO_CONTATO,
        default='PRINCIPAL'
    )

    nome = models.CharField('Nome Completo', max_length=150)
    cargo = models.CharField('Cargo/Função', max_length=100, blank=True)

    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)

    whatsapp = models.BooleanField('WhatsApp', default=False)
    preferencial = models.BooleanField('Contato Preferencial', default=False)

    observacoes = models.TextField('Observações', blank=True)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Contato do Armador'
        verbose_name_plural = 'Contatos do Armador'
        ordering = ['-preferencial', 'tipo', 'nome']

    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"


class ArmadorDadoBancario(models.Model):
    """Contas bancárias do Armador"""

    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('SALARIO', 'Conta Salário'),
    ]

    TIPO_PIX = [
        ('CPF', 'CPF'),
        ('CNPJ', 'CNPJ'),
        ('EMAIL', 'E-mail'),
        ('TELEFONE', 'Telefone'),
        ('CHAVE_ALEATORIA', 'Chave Aleatória'),
    ]

    armador = models.ForeignKey(
        'cadastros.Armador',
        on_delete=models.CASCADE,
        related_name='dados_bancarios',
        verbose_name='Armador'
    )

    # Banco
    codigo_banco = models.CharField(
        'Código do Banco',
        max_length=10,
        help_text='Ex: 001 (BB), 033 (Santander)'
    )
    nome_banco = models.CharField('Nome do Banco', max_length=100)
    agencia = models.CharField('Agência', max_length=20)
    agencia_dv = models.CharField('DV Agência', max_length=2, blank=True)
    conta = models.CharField('Conta', max_length=20)
    conta_dv = models.CharField('DV Conta', max_length=2, blank=True)
    
    tipo_conta = models.CharField(
        'Tipo de Conta',
        max_length=20,
        choices=TIPO_CONTA,
        default='CORRENTE'
    )

    # PIX
    tem_pix = models.BooleanField('Tem PIX', default=False)
    tipo_pix = models.CharField(
        'Tipo de Chave PIX',
        max_length=20,
        choices=TIPO_PIX,
        blank=True
    )
    chave_pix = models.CharField('Chave PIX', max_length=255, blank=True)

    # Complemento
    nome_titular = models.CharField('Nome do Titular', max_length=150)
    cpf_cnpj_titular = models.CharField(
        'CPF/CNPJ do Titular',
        max_length=20,
        blank=True
    )
    
    padrao = models.BooleanField('Dado Bancário Padrão', default=False)
    ativo = models.BooleanField('Ativo', default=True)
    
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Dado Bancário do Armador'
        verbose_name_plural = 'Dados Bancários do Armador'
        ordering = ['-padrao', 'nome_banco']

    def __str__(self):
        return f"{self.nome_banco} - {self.agencia}/{self.conta} - {self.armador.nome}"

    def save(self, *args, **kwargs):
        """Garante apenas um dado bancário padrão por armador"""
        if self.padrao:
            ArmadorDadoBancario.objects.filter(armador=self.armador, padrao=True).update(padrao=False)
        super().save(*args, **kwargs)


class TipoNavio(models.Model):
    """Tipos de Navio - permite que armadores operem múltiplos tipos"""
    
    codigo = models.CharField(
        'Código',
        max_length=20,
        unique=True,
        help_text='Código único do tipo (ex: CONTAINER, REEFER)'
    )
    nome = models.CharField(
        'Nome',
        max_length=100,
        help_text='Nome do tipo de navio'
    )
    descricao = models.TextField(
        'Descrição',
        blank=True,
        help_text='Descrição detalhada do tipo de navio'
    )
    ativo = models.BooleanField('Ativo', default=True)
    
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Navio'
        verbose_name_plural = 'Tipos de Navio'
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class Porto(models.Model):
    """Portos / Pontos de Entrada (Marítimo, Aéreo, Terrestre)"""

    TIPO_CHOICES = [
        ('MARITIMO', 'Marítimo'),
        ('AEREO', 'Aéreo'),
        ('TERRESTRE', 'Terrestre'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='portos',
        verbose_name='Empresa'
    )

    codigo = models.CharField('Código', max_length=10, help_text='Código IATA/UN por empresa')
    nome = models.CharField('Nome', max_length=200)
    pais = models.CharField('País', max_length=100)
    cidade = models.CharField('Cidade', max_length=100)
    tipo = models.CharField('Tipo', max_length=10, choices=TIPO_CHOICES, default='MARITIMO')
    ativo = models.BooleanField('Ativo', default=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Porto'
        verbose_name_plural = 'Portos'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'codigo']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'codigo'], name='unique_porto_por_empresa')
        ]

    def __str__(self):
        return f"{self.nome} ({self.codigo})"


class SubcategoriaFornecedor(models.Model):
    """Subcategorias relacionadas a uma Categoria de Fornecedor"""
    categoria = models.ForeignKey(CategoriaFornecedor, on_delete=models.CASCADE, related_name='subcategorias')
    nome = models.CharField('Nome', max_length=100)
    ativa = models.BooleanField('Subcategoria Ativa', default=True)

    class Meta:
        verbose_name = 'Subcategoria de Fornecedor'
        verbose_name_plural = 'Subcategorias de Fornecedores'
        ordering = ['categoria__nome','nome']

    def __str__(self):
        return f"{self.categoria.nome} / {self.nome}"


class FornecedorEndereco(models.Model):
    """Endereços múltiplos para Fornecedor (billing, shipping, operacional)"""

    TIPO_ENDERECO = [
        ('FATURAMENTO', 'Faturamento'),
        ('ENTREGA', 'Entrega'),
        ('OPERACIONAL', 'Operacional'),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.CASCADE,
        related_name='enderecos',
        verbose_name='Fornecedor'
    )

    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_ENDERECO, default='ENTREGA')

    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField('Logradouro', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')

    padrao = models.BooleanField('Endereço Padrão', default=False)
    preenchido_via_api = models.BooleanField('Preenchido via API', default=False)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Endereço do Fornecedor'
        verbose_name_plural = 'Endereços dos Fornecedores'
        ordering = ['-padrao', 'cidade']
        indexes = [
            models.Index(fields=['fornecedor', 'padrao']),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cidade}/{self.uf} - {self.fornecedor.nome}"

    def save(self, *args, **kwargs):
        """Garante apenas um endereço padrão por fornecedor"""
        if self.padrao:
            FornecedorEndereco.objects.filter(fornecedor=self.fornecedor, padrao=True).update(padrao=False)
        super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'cep': self.cep or '',
            'logradouro': self.logradouro or '',
            'numero': self.numero or '',
            'complemento': self.complemento or '',
            'bairro': self.bairro or '',
            'cidade': self.cidade or '',
            'uf': self.uf or '',
            'pais': self.pais or ''
        }


class FornecedorContato(models.Model):
    """Contatos para Fornecedor (múltiplos)"""

    TIPO_CONTATO = [
        ('PRINCIPAL', 'Contato Principal'),
        ('FINANCEIRO', 'Financeiro'),
        ('OPERACIONAL', 'Operacional'),
        ('TECNICO', 'Técnico'),
        ('EMERGENCIA', 'Emergência'),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.CASCADE,
        related_name='contatos',
        verbose_name='Fornecedor'
    )

    tipo = models.CharField('Tipo de Contato', max_length=20, choices=TIPO_CONTATO, default='PRINCIPAL')

    nome = models.CharField('Nome Completo', max_length=150)
    cargo = models.CharField('Cargo/Função', max_length=100, blank=True)

    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20, blank=True)
    email = models.EmailField('E-mail', blank=True)

    whatsapp = models.BooleanField('WhatsApp', default=False)
    preferencial = models.BooleanField('Contato Preferencial', default=False)

    observacoes = models.TextField('Observações', blank=True)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Contato do Fornecedor'
        verbose_name_plural = 'Contatos dos Fornecedores'
        ordering = ['-preferencial', 'tipo', 'nome']

    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"


class FornecedorDadoBancario(models.Model):
    """Contas bancárias do fornecedor"""

    TIPO_CONTA = [
        ('CORRENTE', 'Conta Corrente'),
        ('POUPANCA', 'Poupança'),
        ('SALARIO', 'Conta Salário'),
    ]

    TIPO_PIX = [
        ('CPF', 'CPF'),
        ('CNPJ', 'CNPJ'),
        ('EMAIL', 'E-mail'),
        ('TELEFONE', 'Telefone'),
        ('CHAVE_ALEATORIA', 'Chave Aleatória'),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor,
        on_delete=models.CASCADE,
        related_name='contas_bancarias',
        verbose_name='Fornecedor'
    )

    banco = models.CharField('Banco', max_length=100)
    codigo_banco = models.CharField('Código do Banco', max_length=4, blank=True)
    agencia = models.CharField('Agência', max_length=10, blank=True)
    agencia_digito = models.CharField('Dígito Agência', max_length=2, blank=True)
    conta = models.CharField('Conta', max_length=20, blank=True)
    conta_digito = models.CharField('Dígito Conta', max_length=2, blank=True)
    tipo_conta = models.CharField('Tipo de Conta', max_length=20, choices=TIPO_CONTA, default='CORRENTE')

    pix_habilitado = models.BooleanField('PIX Habilitado', default=False)
    tipo_chave_pix = models.CharField('Tipo de Chave PIX', max_length=20, choices=TIPO_PIX, blank=True)
    chave_pix = models.CharField('Chave PIX', max_length=100, blank=True)

    swift = models.CharField('SWIFT/BIC', max_length=11, blank=True)
    iban = models.CharField('IBAN', max_length=34, blank=True)

    dados_adicionais = models.TextField('Dados Adicionais', blank=True)

    conta_principal = models.BooleanField('Conta Principal', default=False)
    ativa = models.BooleanField('Conta Ativa', default=True)

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Conta Bancária do Fornecedor'
        verbose_name_plural = 'Contas Bancárias dos Fornecedores'
        ordering = ['-conta_principal', 'banco']

    def __str__(self):
        return f"{self.banco} - {self.conta} ({self.fornecedor.nome})"

    def save(self, *args, **kwargs):
        """Garante apenas uma conta principal por fornecedor"""
        if self.conta_principal:
            FornecedorDadoBancario.objects.filter(fornecedor=self.fornecedor, conta_principal=True).update(conta_principal=False)
        super().save(*args, **kwargs)


class Transportadora(models.Model):
    """Transportadoras (Terceiro / Própria) com dados de contato e bancários
    Multi-tenant via campo `empresa` e constraint de unicidade por `empresa+cnpj`.
    """

    TIPO_CHOICES = [
        ('TER', 'Terceiro'),
        ('PRO', 'Própria'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='transportadoras',
        verbose_name='Empresa'
    )

    razao_social = models.CharField('Nome/Razão Social', max_length=200)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=200, blank=True)

    tipo = models.CharField('Tipo de Transportadora', max_length=3, choices=TIPO_CHOICES, default='TER')

    cnpj = models.CharField('CNPJ', max_length=18, blank=True, null=True, help_text='Formato: 00.000.000/0000-00')
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=50, blank=True)

    # RNTC e Indicadores fiscais
    rntc = models.CharField('RNTC', max_length=50, blank=True)
    contribuinte_icms = models.BooleanField('Contribuinte ICMS', default=False)
    indicador_ie = models.CharField('Indicador IE', max_length=1, blank=True, null=True, help_text='1,2 ou 9')

    # Endereço (campos espelhados)
    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField('Logradouro', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')

    # Contato
    contato_principal_nome = models.CharField('Contato Principal', max_length=150, blank=True)
    contato_principal_telefone = models.CharField('Telefone Contato', max_length=50, blank=True)
    contato_principal_email = models.EmailField('E-mail Contato', blank=True)

    # Dados bancários
    banco = models.CharField('Banco', max_length=100, blank=True)
    agencia = models.CharField('Agência', max_length=20, blank=True)
    conta = models.CharField('Conta', max_length=50, blank=True)

    # Tipo de conta (Conta Corrente / Poupança)
    TIPO_CONTA_CHOICES = [
        ('CC', 'Conta Corrente'),
        ('PO', 'Poupança'),
    ]
    tipo_conta = models.CharField('Tipo de Conta', max_length=2, choices=TIPO_CONTA_CHOICES, blank=True)

    # PIX
    PIX_TIPOS = [
        ('CPF', 'CPF'), ('CNPJ', 'CNPJ'), ('EMAIL', 'E-mail'), ('CEL', 'Celular'), ('EVP', 'Chave Aleatória'), ('OUT', 'Outro')
    ]
    tipo_pix = models.CharField('Tipo de Pix', max_length=10, choices=PIX_TIPOS, blank=True)
    pix_key = models.CharField('PIX', max_length=100, blank=True)

    # Valores de frete
    frete_padrao = models.DecimalField('Frete Padrão', max_digits=10, decimal_places=2, null=True, blank=True)
    frete_por_km = models.DecimalField('Frete por km', max_digits=10, decimal_places=4, null=True, blank=True)
    moeda = models.CharField('Moeda', max_length=3, default='BRL')

    ativa = models.BooleanField('Ativa', default=True)

    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Transportadora'
        verbose_name_plural = 'Transportadoras'
        ordering = ['razao_social']
        indexes = [
            models.Index(fields=['empresa', 'ativa']),
            models.Index(fields=['cnpj']),
        ]
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'cnpj'], name='unique_transportadora_por_empresa')
        ]

    def __str__(self):
        return self.nome_fantasia or self.razao_social

    def clean(self):
        """Valida CNPJ quando informado e define indicador IE conforme regras fiscais"""
        import re
        if self.cnpj:
            cnpj_limpo = re.sub(r'\D', '', (self.cnpj or ''))
            if len(cnpj_limpo) != 14:
                raise ValidationError({'cnpj': 'CNPJ deve ter 14 dígitos'})

        # Indicador IE e validação relacionada
        # If contribuinte_icms True -> indicador_ie = '1' and inscricao_estadual required
        if self.contribuinte_icms:
            if not self.inscricao_estadual:
                raise ValidationError({'inscricao_estadual': 'Inscrição Estadual é obrigatória para contribuinte ICMS'})
            self.indicador_ie = '1'
        else:
            # Assume PJ for transportadoras; default indicador_ie = '2' (Isento / Não Contribuinte)
            self.indicador_ie = '2'


class Viagem(models.Model):
    """Registra viagens realizadas pela transportadora"""

    STATUS_CHOICES = [
        ('PLANEJADA', 'Planejada'),
        ('EM_TRANSITO', 'Em Trânsito'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    transportadora = models.ForeignKey(
        Transportadora,
        on_delete=models.CASCADE,
        related_name='viagens',
        verbose_name='Transportadora'
    )

    origem = models.CharField('Origem', max_length=200)
    destino = models.CharField('Destino', max_length=200)
    data = models.DateField('Data da Viagem')
    valor_frete = models.DecimalField('Valor do Frete', max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='PLANEJADA')

    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'Viagem'
        verbose_name_plural = 'Viagens'
        ordering = ['-data']
        indexes = [
            models.Index(fields=['transportadora', 'data']),
        ]

    def __str__(self):
        return f"{self.transportadora} - {self.origem} → {self.destino} ({self.data})"


# ==========================
# MODELOS DE VEÍCULOS / FROTA
# ==========================

VEHICLE_TYPES = [
    ('LEVE', 'Leve'),
    ('MEDIO', 'Médio'),
    ('PESADO', 'Pesado'),
    ('REBOQUE', 'Reboque'),
    ('IMPLEMENTO', 'Implemento'),
]


class Vehicle(models.Model):
    """Cadastro de veículos (próprios ou de terceiros)."""

    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='veiculos', verbose_name='Empresa'
    )
    transportadora = models.ForeignKey(
        'cadastros.Transportadora', on_delete=models.SET_NULL, null=True, blank=True, related_name='veiculos', verbose_name='Transportadora'
    )

    tipo = models.CharField('Tipo', max_length=20, choices=VEHICLE_TYPES, default='LEVE')
    marca = models.CharField('Marca', max_length=100, blank=True)
    modelo = models.CharField('Modelo', max_length=100, blank=True)
    ano_fabricacao = models.IntegerField('Ano Fabricação', null=True, blank=True)
    ano_modelo = models.IntegerField('Ano Modelo', null=True, blank=True)
    capacidade_ton = models.DecimalField('Capacidade (ton)', max_digits=8, decimal_places=2, null=True, blank=True)
    tara_kg = models.IntegerField('Tara (kg)', null=True, blank=True)
    eixos = models.IntegerField('Eixos', null=True, blank=True)
    cor = models.CharField('Cor', max_length=50, blank=True)
    descricao = models.CharField('Nome/Descrição', max_length=150, blank=True, help_text='Ex: Trator Amarelo, Implemento XX, Caminhão Branco')

    foto = models.ImageField(
        'Foto do Veiculo',
        upload_to='veiculos/fotos/%Y/%m/',
        blank=True,
        null=True,
        help_text='Foto do veiculo/implemento'
    )

    # Novos campos opcionais solicitados
    RENAVAM_CHOICES = []  # placeholder if needed in future
    FUEL_CHOICES = [
        ('DIESEL', 'Diesel'),
        ('GASOLINA', 'Gasolina'),
        ('FLEX', 'Flex'),
        ('ELETRICO', 'Elétrico'),
        ('OUTRO', 'Outro')
    ]

    renavam = models.CharField('RENAVAM', max_length=30, blank=True)
    chassis = models.CharField('Chassi', max_length=50, blank=True)
    numero_motor = models.CharField('Número do Motor', max_length=50, blank=True)
    tipo_combustivel = models.CharField('Tipo de Combustível', max_length=20, choices=FUEL_CHOICES, blank=True)
    codigo_patrimonio = models.CharField('Código de Patrimônio', max_length=50, blank=True, help_text='Usado em veículos/implementos sem placa')
    # Consumo pode ser por km (L/km) ou por hora (L/hora - usado para tratores)
    CONSUMO_UNIDADE_CHOICES = [
        ('L_KM', 'L/km'),
        ('L_HORA', 'L/hora')
    ]
    consumo_medio = models.DecimalField('Consumo Médio', max_digits=8, decimal_places=4, null=True, blank=True, help_text='Consumo médio: L/km (padrão) ou L/hora para tratores')
    consumo_unidade = models.CharField('Unidade de Consumo', max_length=10, choices=CONSUMO_UNIDADE_CHOICES, default='L_KM')

    # Capacidade do tanque em litros
    tank_capacity = models.DecimalField('Capacidade do Tanque (L)', max_digits=8, decimal_places=2, null=True, blank=True)

    # Valor e variação de mercado
    valor_atual = models.DecimalField('Valor Atual (R$)', max_digits=12, decimal_places=2, null=True, blank=True)
    percentual_variacao = models.DecimalField('Percentual de Variação (%)', max_digits=5, decimal_places=2, null=True, blank=True)
    TIPO_VARIACAO_CHOICES = [
        ('VAL', 'Valorização'),
        ('DES', 'Desvalorização'),
    ]
    tipo_variacao = models.CharField('Tipo de Variação', max_length=3, choices=TIPO_VARIACAO_CHOICES, blank=True)

    observacoes = models.TextField('Observações', blank=True)

    # Campos de controle
    ativo = models.BooleanField('Ativo', default=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Veículo'
        verbose_name_plural = 'Veículos'
        ordering = ['-data_cadastro']
        indexes = [models.Index(fields=['empresa', 'ativo'])]

    @property
    def estimated_range_km(self):
        """If consumption is L/km, estimate km per full tank. Otherwise return None."""
        from decimal import Decimal, ROUND_HALF_UP
        if not self.tank_capacity or not self.consumo_medio:
            return None
        try:
            if self.consumo_unidade == 'L_HORA':
                return None
            if self.consumo_medio == Decimal('0'):
                return None
            val = (self.tank_capacity / self.consumo_medio)
            return val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return None

    @property
    def estimated_hours_per_tank(self):
        """If consumption is L/hora, estimate hours per full tank."""
        from decimal import Decimal, ROUND_HALF_UP
        if not self.tank_capacity or not self.consumo_medio:
            return None
        try:
            if self.consumo_unidade == 'L_KM':
                return None
            if self.consumo_medio == Decimal('0'):
                return None
            val = (self.tank_capacity / self.consumo_medio)
            return val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            return None

    def __str__(self):
        plate = self.get_current_plate() or ''
        return f"{self.marca} {self.modelo} {plate}".strip()

    def get_current_plate(self):
        p = self.plates.filter(atual=True).first()
        return p.placa if p else None


# Histórico de variações (registrado quando aplicadas)
class VehicleValueHistory(models.Model):
    vehicle = models.ForeignKey('Vehicle', on_delete=models.CASCADE, related_name='value_history')
    previous_value = models.DecimalField('Valor Anterior (R$)', max_digits=12, decimal_places=2)
    new_value = models.DecimalField('Valor Novo (R$)', max_digits=12, decimal_places=2)
    percentual = models.DecimalField('Percentual (%)', max_digits=6, decimal_places=2)
    tipo = models.CharField('Tipo', max_length=3, choices=Vehicle.TIPO_VARIACAO_CHOICES)
    aplicado_por = models.ForeignKey('usuarios.Usuario', null=True, blank=True, on_delete=models.SET_NULL)
    data_aplicacao = models.DateTimeField('Data Aplicação', auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de Valor do Veículo'
        verbose_name_plural = 'Históricos de Valor de Veículos'
        ordering = ['-data_aplicacao']

    def __str__(self):
        return f"{self.vehicle} — {self.tipo} {self.percentual}% em {self.data_aplicacao.date()}"


class VehiclePlate(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='plates')
    placa = models.CharField('Placa', max_length=10)
    vigencia_inicio = models.DateField('Vigência Início')
    vigencia_fim = models.DateField('Vigência Fim', null=True, blank=True)
    atual = models.BooleanField('Placa Atual', default=False)

    class Meta:
        verbose_name = 'Placa do Veículo'
        verbose_name_plural = 'Placas do Veículo'
        ordering = ['-vigencia_inicio']

    def save(self, *args, **kwargs):
        # Se esta placa marcada como atual, desmarca as outras
        if self.atual:
            VehiclePlate.objects.filter(vehicle=self.vehicle, atual=True).exclude(pk=self.pk).update(atual=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.placa} ({self.vehicle})"





class VehicleDocument(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')
    tipo = models.CharField('Tipo', max_length=50)  # CRLV, Seguro, Vistoria
    numero = models.CharField('Número', max_length=100, blank=True)
    data_emissao = models.DateField('Emissão', null=True, blank=True)
    data_validade = models.DateField('Validade', null=True, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='vehicle_docs/', null=True, blank=True)

    class Meta:
        verbose_name = 'Documento do Veículo'
        verbose_name_plural = 'Documentos do Veículo'

    def __str__(self):
        return f"{self.get_tipo_display() if hasattr(self,'get_tipo_display') else self.tipo} - {self.vehicle}"


# Helper: checa se validade < data_inicio
from django.utils import timezone

def validity_is_past(validade_date, compare_dt):
    try:
        return validade_date < compare_dt.date() if hasattr(compare_dt, 'date') else validade_date < compare_dt
    except Exception:
        return False


# ==========================
# MODELO DE MOTORISTA
# ==========================

class Motorista(models.Model):
    """Cadastro de motoristas (próprios, terceirizados ou agregados)"""
    
    TIPO_CHOICES = [
        ('PROPRIO', 'Próprio'),
        ('TERCEIRO', 'Terceirizado'),
        ('AGREGADO', 'Agregado'),
    ]
    
    CATEGORIA_CNH_CHOICES = [
        ('A', 'Categoria A'),
        ('B', 'Categoria B'),
        ('C', 'Categoria C'),
        ('D', 'Categoria D'),
        ('E', 'Categoria E'),
        ('AB', 'Categoria AB'),
        ('AC', 'Categoria AC'),
        ('AD', 'Categoria AD'),
        ('AE', 'Categoria AE'),
        ('BC', 'Categoria BC'),
        ('BD', 'Categoria BD'),
        ('BE', 'Categoria BE'),
        ('CD', 'Categoria CD'),
        ('CE', 'Categoria CE'),
        ('DE', 'Categoria DE'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='motoristas',
        verbose_name='Empresa'
    )
    
    tipo = models.CharField(
        'Tipo de Motorista',
        max_length=10,
        choices=TIPO_CHOICES,
        default='PROPRIO',
        help_text='Selecione se é motorista próprio ou terceirizado'
    )
    
    transportadora = models.ForeignKey(
        'cadastros.Transportadora',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='motoristas',
        verbose_name='Transportadora',
        help_text='Obrigatório para motoristas terceirizados'
    )
    
    # Dados pessoais
    nome = models.CharField('Nome Completo', max_length=200)
    cpf = models.CharField(
        'CPF',
        max_length=14,
        unique=True,
        help_text='Formato: 000.000.000-00'
    )
    data_nascimento = models.DateField('Data de Nascimento', null=True, blank=True)
    foto = models.ImageField(
        'Foto',
        upload_to='motorista_fotos/',
        null=True,
        blank=True,
        help_text='Foto do motorista (opcional, recomendado para motoristas próprios e agregados)'
    )
    
    # Documentação - CNH
    cnh = models.CharField(
        'Número CNH',
        max_length=20,
        unique=True,
        help_text='Número da Carteira Nacional de Habilitação'
    )
    categoria_cnh = models.CharField(
        'Categoria CNH',
        max_length=5,
        choices=CATEGORIA_CNH_CHOICES,
        help_text='Categoria da CNH'
    )
    data_emissao_cnh = models.DateField('Data Emissão CNH', null=True, blank=True)
    data_validade_cnh = models.DateField('Data Validade CNH')
    uf_cnh = models.CharField('UF CNH', max_length=2, blank=True, help_text='Estado emissor da CNH')
    
    # Contatos
    telefone = models.CharField('Telefone', max_length=20, blank=True)
    celular = models.CharField('Celular/WhatsApp', max_length=20)
    email = models.EmailField('Email', blank=True)
    
    # Endereço
    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField('Logradouro', max_length=200, blank=True)
    numero = models.CharField('Número', max_length=10, blank=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True)
    uf = models.CharField('UF', max_length=2, blank=True)
    pais = models.CharField('País', max_length=100, default='Brasil')
    
    # Status
    ativo = models.BooleanField('Ativo', default=True)
    motivo_inativacao = models.TextField('Motivo da Inativação', blank=True)
    data_inativacao = models.DateField('Data Inativação', null=True, blank=True)
    
    # Auditoria
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Motorista'
        verbose_name_plural = 'Motoristas'
        ordering = ['nome']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['cpf']),
            models.Index(fields=['cnh']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(tipo__in=['TERCEIRO', 'AGREGADO']) | models.Q(transportadora__isnull=False),
                name='motorista_terceiro_agregado_requer_transportadora'
            )
        ]

    def __str__(self):
        return f"{self.nome} ({self.cpf})"
    
    def clean(self):
        """Valida lógicas de negócio do motorista"""
        from django.core.exceptions import ValidationError
        
        # Motorista terceirizado e agregado devem ter transportadora
        if self.tipo in ['TERCEIRO', 'AGREGADO'] and not self.transportadora:
            raise ValidationError({
                'transportadora': f'Transportadora é obrigatória para motoristas {self.get_tipo_display().lower()}.'
            })
    
    @property
    def cnh_vencida(self):
        """Retorna True se a CNH está vencida"""
        from django.utils import timezone
        return self.data_validade_cnh < timezone.now().date() if self.data_validade_cnh else False
    
    @property
    def dias_para_vencer_cnh(self):
        """Retorna dias restantes para vencimento da CNH"""
        from django.utils import timezone
        if not self.data_validade_cnh:
            return None
        dias = (self.data_validade_cnh - timezone.now().date()).days
        return dias if dias >= 0 else None


class MotoristadoDocumento(models.Model):
    """Documentos adicionais do motorista (exames, certificados, etc)"""
    
    TIPO_DOCUMENTO_CHOICES = [
        ('EXAME_PSICO', 'Exame Psicotécnico'),
        ('EXAME_MEDICO', 'Exame Médico'),
        ('CERTIFICADO_ETEA', 'Certificado ETEA'),
        ('OUTRO', 'Outro'),
    ]
    
    motorista = models.ForeignKey(
        'cadastros.Motorista',
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Motorista'
    )
    
    tipo = models.CharField(
        'Tipo de Documento',
        max_length=20,
        choices=TIPO_DOCUMENTO_CHOICES
    )
    
    numero = models.CharField('Número', max_length=100, blank=True)
    data_emissao = models.DateField('Data Emissão', null=True, blank=True)
    data_validade = models.DateField('Data Validade', null=True, blank=True)
    arquivo = models.FileField('Arquivo', upload_to='motorista_docs/', null=True, blank=True)
    observacoes = models.TextField('Observações', blank=True)
    
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Documento do Motorista'
        verbose_name_plural = 'Documentos do Motorista'
        ordering = ['-data_emissao']

    def __str__(self):
        return f"{self.motorista.nome} - {self.get_tipo_display()}"


class MotoristaVinculoPlaca(models.Model):
    """Vinculo de motorista a conjunto de placas por periodo"""

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='vinculos_motorista_placa',
        verbose_name='Empresa'
    )
    motorista = models.ForeignKey(
        'cadastros.Motorista',
        on_delete=models.CASCADE,
        related_name='vinculos_placas',
        verbose_name='Motorista'
    )
    placa_principal = models.ForeignKey(
        'cadastros.VehiclePlate',
        on_delete=models.PROTECT,
        related_name='vinculos_principal',
        verbose_name='Placa Principal'
    )
    reboques = models.ManyToManyField(
        'cadastros.VehiclePlate',
        blank=True,
        related_name='vinculos_reboque',
        verbose_name='Placas de Reboque'
    )
    data_inicio = models.DateField('Data Inicio')
    data_fim = models.DateField('Data Fim', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True, help_text='Vinculo ativo ou inativo')
    observacoes = models.TextField('Observacoes', blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Ultima Atualizacao', auto_now=True)

    class Meta:
        verbose_name = 'Vinculo Motorista x Placa'
        verbose_name_plural = 'Vinculos Motorista x Placa'
        ordering = ['-data_inicio']
        indexes = [
            models.Index(fields=['empresa', 'motorista']),
            models.Index(fields=['empresa', 'data_inicio']),
        ]

    def __str__(self):
        return f"{self.motorista} - {self.placa_principal}"

    @property
    def periodo_ativo(self):
        """Verifica se o vinculo esta dentro do periodo valido baseado na data_fim"""
        from datetime import date
        if not self.data_fim:
            return True
        return self.data_fim >= date.today()

    def placas_conjunto(self):
        placas = [self.placa_principal]
        placas.extend(list(self.reboques.all()))
        return placas


"""
📝 VIEWS DE FORNECEDOR - CÓDIGO COMPLETO
=============================================================================

TODAS as views necessárias para o módulo de fornecedores.

INSTRUÇÕES:
1. Abra cadastros/views.py
2. Procure pela view "def fornecedor_list" (que já existe)
3. ADICIONE todo este código LOGO APÓS a view fornecedor_list
4. Salve e teste

Total: 14 novas views (fornecedor_list já existe)
"""


# ============================================================================
# MÓDULO: ORDENS DE SERVIÇO AGRÍCOLAS
# RF-105: Ordens de serviço — plantio, irrigação, aplicação, colheita
# RF-115: Controle de custos por talhão e safra
# ============================================================================

class CustoHoraMaquina(models.Model):
    """
    Configuração do custo/hora de operação de uma máquina (trator, pulverizador, etc.)
    Baseado em: depreciação + combustível + reserva de manutenção
    """

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='custos_hora_maquina',
        verbose_name='Empresa'
    )

    veiculo = models.ForeignKey(
        'cadastros.Vehicle',
        on_delete=models.CASCADE,
        related_name='configuracoes_custo',
        verbose_name='Veículo/Máquina'
    )

    preco_combustivel = models.DecimalField(
        'Preço do Combustível (R$/L)',
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
        help_text='Preço atual do combustível por litro'
    )

    reserva_manutencao_hora = models.DecimalField(
        'Reserva de Manutenção (R$/h)',
        max_digits=8,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Valor reservado por hora para manutenção preventiva/corretiva'
    )

    horas_anuais_trabalho = models.DecimalField(
        'Horas Anuais de Trabalho',
        max_digits=8,
        decimal_places=2,
        default=Decimal('1000.00'),
        validators=[MinValueValidator(Decimal('1.00'))],
        help_text='Estimativa anual de horas de operação (base para cálculo de depreciação/h)'
    )

    ativo = models.BooleanField('Configuração Ativa', default=True)

    data_referencia = models.DateField(
        'Data de Referência',
        help_text='Data de vigência desta configuração de custo'
    )

    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custos_maquina_cadastrados',
        verbose_name='Cadastrado por'
    )

    class Meta:
        verbose_name = 'Custo/Hora de Máquina'
        verbose_name_plural = 'Custos/Hora de Máquinas'
        ordering = ['-data_referencia']
        indexes = [
            models.Index(fields=['empresa', 'ativo']),
            models.Index(fields=['veiculo', '-data_referencia']),
        ]

    def __str__(self):
        return f"{self.veiculo} — R$ {self.custo_hora_calculado:.2f}/h ({self.data_referencia})"

    @property
    def custo_hora_calculado(self):
        """
        Custo total por hora de operação:
        = (depreciação anual / horas anuais) + (consumo L/h × preço combustível) + reserva manutenção
        """
        try:
            patrimonio = self.veiculo.patrimonio  # OneToOne via patrimonio.Patrimonio
            dep_anual = patrimonio.depreciacao_anual() if hasattr(patrimonio, 'depreciacao_anual') else (
                patrimonio.valor_inicial / max(patrimonio.vida_util_anos, 1)
            )
        except Exception:
            dep_anual = Decimal('0')

        dep_hora = dep_anual / self.horas_anuais_trabalho if self.horas_anuais_trabalho else Decimal('0')

        consumo = self.veiculo.consumo_medio or Decimal('0')
        custo_comb = consumo * self.preco_combustivel

        return dep_hora + custo_comb + self.reserva_manutencao_hora


# ============================================================================
# CLASSIFICAÇÃO ESTRUTURADA DE SERVIÇOS AGRÍCOLAS
# Tipo de Serviço → Operação (Subtipo) → Modalidade de Execução
# ============================================================================

class TipoServicoOS(models.Model):
    """
    Tipo macro de serviço agrícola.
    empresa=None indica registro global disponível a todas as empresas.
    Exemplos: Preparo do Solo, Pulverização, Plantio, Colheita
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tipos_servico_os',
        verbose_name='Empresa',
        help_text='Deixe em branco para tipos globais disponíveis a todas as empresas'
    )
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    icone = models.CharField('Ícone Bootstrap', max_length=60, blank=True, default='bi-tools')
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)
    # Mapeamento para o campo tipo legado (compatibilidade com código existente)
    tipo_legado = models.CharField(
        'Tipo Legado',
        max_length=30,
        blank=True,
        help_text='Valor correspondente no campo tipo legado da OS'
    )

    class Meta:
        verbose_name = 'Tipo de Serviço (OS)'
        verbose_name_plural = 'Tipos de Serviço (OS)'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class SubtipoServicoOS(models.Model):
    """
    Operação específica dentro de um tipo de serviço agrícola.
    Responde a QUAL operação foi realizada dentro do tipo.
    Exemplos: Gradagem / Subsolagem (Preparo do Solo); Herbicida / Fungicida (Pulverização)
    """
    tipo_servico = models.ForeignKey(
        TipoServicoOS,
        on_delete=models.CASCADE,
        related_name='subtipos',
        verbose_name='Tipo de Serviço'
    )
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subtipos_servico_os',
        verbose_name='Empresa',
        help_text='Deixe em branco para registros globais'
    )
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Operação de Serviço (OS)'
        verbose_name_plural = 'Operações de Serviço (OS)'
        ordering = ['tipo_servico__ordem', 'ordem', 'nome']

    def __str__(self):
        return f"{self.tipo_servico.nome} / {self.nome}"


class ModalidadeExecucaoOS(models.Model):
    """
    Modalidade de execução — COMO o serviço foi realizado.
    Independente do tipo/subtipo de serviço.
    Exemplos: Tratorizada, Costal, Drone, Manual, Terceirizada
    """
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='modalidades_execucao_os',
        verbose_name='Empresa',
        help_text='Deixe em branco para modalidades globais'
    )
    nome = models.CharField('Nome', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Modalidade de Execução (OS)'
        verbose_name_plural = 'Modalidades de Execução (OS)'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class OrdemServico(models.Model):
    """
    Ordem de Serviço (OS) para atividades agrícolas em talhões
    RN-03: Conclusão exige evidência fotográfica
    """

    TIPO_CHOICES = [
        ('PREPARO_SOLO', 'Preparo de Solo'),
        ('PULV_MECANICA', 'Pulverização Mecânica'),
        ('PULV_COSTAL', 'Pulverização Costal'),
        ('PLANTIO', 'Plantio'),
        ('IRRIGACAO', 'Irrigação'),
        ('ADUBACAO', 'Adubação/Fertirrigação'),
        ('COLHEITA', 'Colheita'),
        ('MANUTENCAO', 'Manutenção de Infraestrutura'),
        ('OUTRO', 'Outro'),
    ]

    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('APROVADA', 'Aprovada'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    UNIDADE_COBRANCA_CHOICES = [
        ('POR_HA', 'Por Hectare (R$/ha)'),
        ('DIARIA', 'Diária'),
        ('FECHADO', 'Valor Fechado'),
    ]

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='ordens_servico',
        verbose_name='Empresa'
    )

    numero = models.CharField(
        'Número',
        max_length=30,
        unique=True,
        blank=True,
        help_text='Auto-gerado: OS-YYYY-NNNNN'
    )

    tipo = models.CharField('Tipo de Serviço', max_length=30, choices=TIPO_CHOICES, blank=True)

    # Classificação estruturada (substituem o campo tipo legado na interface)
    tipo_servico = models.ForeignKey(
        TipoServicoOS,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordens_servico',
        verbose_name='Tipo de Serviço'
    )
    subtipo_servico = models.ForeignKey(
        SubtipoServicoOS,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordens_servico',
        verbose_name='Operação'
    )
    modalidade_execucao = models.ForeignKey(
        ModalidadeExecucaoOS,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordens_servico',
        verbose_name='Modalidade de Execução'
    )

    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='ABERTA')

    # Contexto agrícola
    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='ordens_servico',
        verbose_name='Talhão'
    )

    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordens_servico',
        verbose_name='Safra'
    )

    requisicao = models.ForeignKey(
        'cadastros.Requisicao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordens_servico',
        verbose_name='Requisição de Insumos',
        help_text='Requisição de insumos vinculada a esta OS'
    )

    # Pessoas
    solicitante = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='os_solicitadas',
        verbose_name='Solicitante'
    )

    responsavel = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='os_responsavel',
        verbose_name='Responsável pela Execução'
    )

    aprovador = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='os_aprovadas',
        verbose_name='Aprovador'
    )

    # Datas
    data_prevista = models.DateField('Data Prevista', null=True, blank=True)
    data_inicio = models.DateTimeField('Data/Hora de Início', null=True, blank=True)
    data_fim = models.DateTimeField('Data/Hora de Conclusão', null=True, blank=True)
    data_aprovacao = models.DateTimeField('Data de Aprovação', null=True, blank=True)

    # Execução
    area_executada_ha = models.DecimalField(
        'Área Executada (ha)',
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Área efetivamente trabalhada em hectares'
    )

    # Serviço externo (terceirizado)
    fornecedor_servico = models.ForeignKey(
        'cadastros.Fornecedor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='os_executadas',
        verbose_name='Fornecedor do Serviço',
        help_text='Empresa terceirizada que executou o serviço'
    )

    valor_servico_externo = models.DecimalField(
        'Valor do Serviço Externo (R$)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Valor total cobrado pelo serviço terceirizado'
    )

    unidade_cobranca = models.CharField(
        'Unidade de Cobrança',
        max_length=10,
        choices=UNIDADE_COBRANCA_CHOICES,
        null=True,
        blank=True
    )

    # RN-03: Evidência fotográfica obrigatória para conclusão
    foto_evidencia = models.ImageField(
        'Foto de Evidência (RN-03)',
        upload_to='ordens_servico/%Y/%m/',
        null=True,
        blank=True,
        help_text='Obrigatória para concluir a OS (RN-03)'
    )

    observacoes = models.TextField('Observações', blank=True)

    # Auditoria
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    cadastrado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='os_cadastradas',
        verbose_name='Cadastrado por'
    )

    class Meta:
        verbose_name = 'Ordem de Serviço'
        verbose_name_plural = 'Ordens de Serviço'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['talhao', '-data_cadastro']),
            models.Index(fields=['safra', 'tipo']),
        ]

    def __str__(self):
        return f"{self.numero} — {self.descricao_servico} / {self.talhao.nome}"

    @property
    def descricao_servico(self):
        """Retorna descrição estruturada: Tipo / Operação / Modalidade"""
        parts = []
        if self.tipo_servico_id:
            parts.append(self.tipo_servico.nome)
        else:
            parts.append(self.get_tipo_display() or 'Sem tipo')
        if self.subtipo_servico_id:
            parts.append(self.subtipo_servico.nome)
        if self.modalidade_execucao_id:
            parts.append(self.modalidade_execucao.nome)
        return ' / '.join(parts)

    def save(self, *args, **kwargs):
        if not self.numero:
            ano = timezone.now().year
            ultima = OrdemServico.objects.filter(
                numero__startswith=f'OS-{ano}-'
            ).order_by('numero').last()
            seq = 1
            if ultima:
                try:
                    seq = int(ultima.numero.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    seq = OrdemServico.objects.filter(numero__startswith=f'OS-{ano}-').count() + 1
            self.numero = f'OS-{ano}-{seq:05d}'
        # Sincroniza campo tipo legado a partir de tipo_servico
        if self.tipo_servico_id:
            legado = self.tipo_servico.tipo_legado or ''
            # Pulverização + Costal → PULV_COSTAL para compatibilidade
            if (legado == 'PULV_MECANICA' and self.modalidade_execucao_id
                    and self.modalidade_execucao.nome == 'Costal'):
                self.tipo = 'PULV_COSTAL'
            elif legado:
                self.tipo = legado
        super().save(*args, **kwargs)

    def clean(self):
        # RN-03: foto obrigatória ao concluir
        if self.status == 'CONCLUIDA' and not self.foto_evidencia:
            raise ValidationError({
                'foto_evidencia': 'Evidência fotográfica é obrigatória para concluir a OS (RN-03).'
            })
        # Serviço externo: valor e unidade obrigatórios juntos
        if self.fornecedor_servico and not self.valor_servico_externo:
            raise ValidationError({
                'valor_servico_externo': 'Informe o valor do serviço externo.'
            })
        # Subtipo deve pertencer ao tipo de serviço selecionado
        if self.subtipo_servico_id and self.tipo_servico_id:
            if self.subtipo_servico.tipo_servico_id != self.tipo_servico_id:
                raise ValidationError({
                    'subtipo_servico': 'A operação selecionada não pertence ao tipo de serviço escolhido.'
                })

    @property
    def custo_total(self):
        try:
            return self.custo_talhao.custo_total
        except Exception:
            return Decimal('0')


class OrdemServicoInsumo(models.Model):
    """Insumos lançados diretamente na Ordem de Serviço."""

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='os_insumos',
        verbose_name='Empresa'
    )
    os = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name='insumos_os',
        verbose_name='Ordem de Serviço'
    )
    produto = models.ForeignKey(
        'produtos.Produto',
        on_delete=models.PROTECT,
        related_name='insumos_os',
        verbose_name='Produto'
    )
    unidade_medida = models.ForeignKey(
        'produtos.UnidadeMedida',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='insumos_os',
        verbose_name='Unidade'
    )
    quantidade_planejada = models.DecimalField(
        'Quantidade Planejada',
        max_digits=15,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    quantidade_aplicada = models.DecimalField(
        'Quantidade Aplicada',
        max_digits=15,
        decimal_places=3,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))]
    )
    custo_unitario = models.DecimalField(
        'Custo Unitário (R$)',
        max_digits=15,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    observacoes = models.CharField('Observações', max_length=255, blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Insumo da OS'
        verbose_name_plural = 'Insumos da OS'
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['os']),
            models.Index(fields=['empresa', 'produto']),
        ]

    def __str__(self):
        return f"{self.os.numero} - {self.produto}"

    @property
    def custo_total(self):
        qtd = self.quantidade_aplicada or Decimal('0')
        custo = self.custo_unitario or Decimal('0')
        return (qtd * custo).quantize(Decimal('0.01'))

    def clean(self):
        if self.quantidade_aplicada is not None and self.quantidade_aplicada < 0:
            raise ValidationError({'quantidade_aplicada': 'A quantidade aplicada não pode ser negativa.'})
        if self.custo_unitario is not None and self.custo_unitario < 0:
            raise ValidationError({'custo_unitario': 'O custo unitário não pode ser negativo.'})

    def save(self, *args, **kwargs):
        if not self.unidade_medida_id and getattr(self.produto, 'unidade_medida_id', None):
            self.unidade_medida_id = self.produto.unidade_medida_id
        super().save(*args, **kwargs)


class OSFuncionario(models.Model):
    """
    Funcionário alocado em uma Ordem de Serviço
    Calcula custo de mão de obra: (salário ÷ 220h) × horas_trabalhadas
    """

    os = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name='funcionarios_os',
        verbose_name='Ordem de Serviço'
    )

    funcionario = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.PROTECT,
        related_name='alocacoes_os',
        verbose_name='Funcionário'
    )

    data_execucao = models.DateField('Data de Execução')
    hora_inicio = models.TimeField('Hora de Início')
    hora_fim = models.TimeField('Hora de Término')

    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Funcionário na OS'
        verbose_name_plural = 'Funcionários nas OS'
        ordering = ['data_execucao', 'hora_inicio']
        indexes = [
            models.Index(fields=['os', 'data_execucao']),
        ]

    def __str__(self):
        return f"{self.funcionario.nome_completo} — {self.os.numero} ({self.data_execucao})"

    @property
    def horas_trabalhadas(self):
        """Retorna horas trabalhadas como Decimal"""
        from datetime import datetime, date
        inicio = datetime.combine(date.today(), self.hora_inicio)
        fim = datetime.combine(date.today(), self.hora_fim)
        delta = (fim - inicio).total_seconds()
        if delta <= 0:
            return Decimal('0')
        return Decimal(str(round(delta / 3600, 4)))

    @property
    def custo_calculado(self):
        """Custo de mão de obra: (salário ÷ 220) × horas"""
        try:
            custo_hora = self.funcionario.salario / Decimal('220')
            return (custo_hora * self.horas_trabalhadas).quantize(Decimal('0.01'))
        except Exception:
            return Decimal('0')


class OSMaquina(models.Model):
    """
    Máquina/Veículo utilizado em uma Ordem de Serviço
    Calcula custo de maquinário via CustoHoraMaquina ou cálculo automático
    """

    os = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name='maquinas_os',
        verbose_name='Ordem de Serviço'
    )

    veiculo = models.ForeignKey(
        'cadastros.Vehicle',
        on_delete=models.PROTECT,
        related_name='usos_os',
        verbose_name='Veículo/Máquina'
    )

    operador = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='operacoes_maquina_os',
        verbose_name='Operador'
    )

    data_execucao = models.DateField('Data de Execução')
    horimetro_inicial = models.DecimalField(
        'Horímetro Inicial (h)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    horimetro_final = models.DecimalField(
        'Horímetro Final (h)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )

    custo_hora_config = models.ForeignKey(
        CustoHoraMaquina,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usos_os',
        verbose_name='Configuração de Custo/Hora',
        help_text='Se vazio, usa a configuração ativa mais recente da máquina'
    )

    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Máquina na OS'
        verbose_name_plural = 'Máquinas nas OS'
        ordering = ['data_execucao', 'horimetro_inicial']
        indexes = [
            models.Index(fields=['os', 'data_execucao']),
        ]

    def __str__(self):
        return f"{self.veiculo} — {self.os.numero} ({self.data_execucao})"

    @property
    def horas_trabalhadas(self):
        delta = self.horimetro_final - self.horimetro_inicial
        return max(delta, Decimal('0'))

    @property
    def litros_consumidos(self):
        consumo = self.veiculo.consumo_medio or Decimal('0')
        return (consumo * self.horas_trabalhadas).quantize(Decimal('0.01'))

    @property
    def custo_calculado(self):
        config = self.custo_hora_config
        if not config:
            config = CustoHoraMaquina.objects.filter(
                veiculo=self.veiculo, ativo=True
            ).order_by('-data_referencia').first()
        if config:
            return (config.custo_hora_calculado * self.horas_trabalhadas).quantize(Decimal('0.01'))
        return Decimal('0')

    def clean(self):
        if self.horimetro_final is not None and self.horimetro_inicial is not None:
            if self.horimetro_final < self.horimetro_inicial:
                raise ValidationError({
                    'horimetro_final': 'Horímetro final não pode ser menor que o inicial.'
                })


class CustoTalhao(models.Model):
    """
    Consolidação de custos por OS / Talhão / Safra
    Gerado automaticamente ao concluir uma OS
    """

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='custos_talhao',
        verbose_name='Empresa'
    )

    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='custos',
        verbose_name='Talhão'
    )

    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custos_talhao',
        verbose_name='Safra'
    )

    os = models.OneToOneField(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name='custo_talhao',
        verbose_name='Ordem de Serviço'
    )

    # Componentes de custo
    custo_mao_obra = models.DecimalField(
        'Custo Mão de Obra (R$)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )

    custo_maquinario = models.DecimalField(
        'Custo Maquinário (R$)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )

    custo_insumos = models.DecimalField(
        'Custo Insumos (R$)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )

    custo_servico_externo = models.DecimalField(
        'Custo Serviço Externo (R$)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0')
    )

    area_executada_ha = models.DecimalField(
        'Área Executada (ha)',
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True
    )

    data_registro = models.DateTimeField('Data de Registro', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)

    class Meta:
        verbose_name = 'Custo por Talhão'
        verbose_name_plural = 'Custos por Talhão'
        ordering = ['-data_registro']
        indexes = [
            models.Index(fields=['empresa', 'talhao']),
            models.Index(fields=['safra', 'talhao']),
        ]

    def __str__(self):
        return f"Custo {self.os.numero} — {self.talhao.nome} (R$ {self.custo_total:.2f})"

    @property
    def custo_total(self):
        return (
            self.custo_mao_obra +
            self.custo_maquinario +
            self.custo_insumos +
            self.custo_servico_externo
        )

    @property
    def custo_por_hectare(self):
        if self.area_executada_ha and self.area_executada_ha > 0:
            return (self.custo_total / self.area_executada_ha).quantize(Decimal('0.01'))
        return Decimal('0')

    def recalcular(self):
        """Recalcula todos os componentes de custo com base nos registros da OS"""
        # Mão de obra
        self.custo_mao_obra = sum(
            f.custo_calculado for f in self.os.funcionarios_os.all()
        ) or Decimal('0')

        # Maquinário
        self.custo_maquinario = sum(
            m.custo_calculado for m in self.os.maquinas_os.all()
        ) or Decimal('0')

        # Insumos (prioriza lançamento direto na OS; fallback para requisição)
        insumos_os = self.os.insumos_os.all()
        if insumos_os.exists():
            self.custo_insumos = sum((i.custo_total for i in insumos_os), Decimal('0'))
        elif self.os.requisicao:
            from django.db.models import Sum as DjSum
            total = self.os.requisicao.itens.aggregate(
                t=DjSum(
                    models.F('quantidade_atendida') * models.F('custo_estimado')
                )
            )['t']
            self.custo_insumos = total or Decimal('0')
        else:
            self.custo_insumos = Decimal('0')

        # Serviço externo
        self.custo_servico_externo = self.os.valor_servico_externo or Decimal('0')

        # Área
        self.area_executada_ha = self.os.area_executada_ha
        self.save()


# ============================================================================
# MÓDULO DE COLHEITA — RF-105 Extensão
# ============================================================================

class EtapaColheita(models.Model):
    """
    Representa uma rodada de colheita (1ª, 2ª, 3ª) de uma OS de colheita.
    Cada etapa agrupa a frota (tratores + carroções) e as viagens de pesagem.
    """
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('CONCLUIDA', 'Concluída'),
    ]

    os = models.ForeignKey(
        OrdemServico,
        on_delete=models.CASCADE,
        related_name='etapas_colheita',
        verbose_name='Ordem de Serviço',
        limit_choices_to={'tipo': 'COLHEITA'},
    )
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='etapas_colheita',
        verbose_name='Empresa'
    )
    talhao = models.ForeignKey(
        'cadastros.Talhao',
        on_delete=models.PROTECT,
        related_name='etapas_colheita',
        verbose_name='Talhão'
    )
    safra = models.ForeignKey(
        'cadastros.Safra',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='etapas_colheita',
        verbose_name='Safra'
    )
    numero_etapa = models.PositiveSmallIntegerField(
        'Nº da Etapa',
        help_text='Sequência: 1ª, 2ª, 3ª colheita — gerado automaticamente'
    )
    data_inicio = models.DateTimeField('Data/Hora de Início', null=True, blank=True)
    data_fim = models.DateTimeField('Data/Hora de Encerramento', null=True, blank=True)
    supervisor = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='etapas_supervisionadas',
        verbose_name='Supervisor de Campo'
    )
    status = models.CharField(
        'Status', max_length=10, choices=STATUS_CHOICES, default='ABERTA'
    )
    total_liquido_kg = models.DecimalField(
        'Total Líquido (kg)',
        max_digits=14, decimal_places=2,
        default=Decimal('0'),
        help_text='Soma automática das pesagens líquidas da etapa'
    )
    observacoes = models.TextField('Observações', blank=True)
    data_cadastro = models.DateTimeField('Data de Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Etapa de Colheita'
        verbose_name_plural = 'Etapas de Colheita'
        ordering = ['os', 'numero_etapa']
        unique_together = [('os', 'numero_etapa')]
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['talhao', 'safra', 'numero_etapa']),
        ]

    def __str__(self):
        return f"{self.os.numero} — {self.numero_etapa}ª Colheita / {self.talhao.nome}"

    def recalcular_total(self):
        """Soma todos os pesos finais das viagens da etapa."""
        from django.db.models import Sum as DjSum
        total = ViagemColheita.objects.filter(
            carrocao__frota__etapa=self
        ).aggregate(t=DjSum('peso_final_kg'))['t'] or Decimal('0')
        self.total_liquido_kg = total
        self.save(update_fields=['total_liquido_kg'])

    @classmethod
    def proximo_numero(cls, os_obj):
        """Retorna o próximo número sequencial de etapa para a OS."""
        ultimo = cls.objects.filter(os=os_obj).order_by('-numero_etapa').first()
        return (ultimo.numero_etapa + 1) if ultimo else 1


class FrotaColheita(models.Model):
    """
    Um trator alocado em uma EtapaColheita.
    Pode ter N carroções rebocados.
    """
    etapa = models.ForeignKey(
        EtapaColheita,
        on_delete=models.CASCADE,
        related_name='frotas',
        verbose_name='Etapa de Colheita'
    )
    trator = models.ForeignKey(
        'cadastros.Vehicle',
        on_delete=models.PROTECT,
        related_name='frotas_colheita',
        verbose_name='Trator',
        limit_choices_to={'tipo__in': ['LEVE', 'MEDIO', 'PESADO']},
    )
    operador = models.ForeignKey(
        'cadastros.Funcionario',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operacoes_colheita',
        verbose_name='Operador/Tratorista'
    )
    horimetro_inicial = models.DecimalField(
        'Horímetro Inicial (h)',
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    horimetro_final = models.DecimalField(
        'Horímetro Final (h)',
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    observacoes = models.CharField('Observações', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Trator na Colheita'
        verbose_name_plural = 'Tratores na Colheita'
        ordering = ['etapa', 'trator']

    def __str__(self):
        return f"{self.trator} — {self.etapa}"

    def clean(self):
        if (self.horimetro_final is not None and self.horimetro_inicial is not None
                and self.horimetro_final < self.horimetro_inicial):
            raise ValidationError({
                'horimetro_final': 'Horímetro final não pode ser menor que o inicial.'
            })


class CarrocaoFrota(models.Model):
    """
    Carroção rebocado por um FrotaColheita.
    Capacidade e tara são herdadas do Vehicle cadastrado, mas editáveis por operação.
    """
    frota = models.ForeignKey(
        FrotaColheita,
        on_delete=models.CASCADE,
        related_name='carrocoes',
        verbose_name='Frota (Trator)'
    )
    veiculo = models.ForeignKey(
        'cadastros.Vehicle',
        on_delete=models.PROTECT,
        related_name='usos_colheita',
        verbose_name='Carroção',
        limit_choices_to={'tipo': 'REBOQUE'},
    )
    numero_identificacao = models.CharField(
        'Identificação',
        max_length=50,
        help_text='Auto-preenchido do cadastro. Ex: Carroção 03'
    )
    capacidade_ton = models.DecimalField(
        'Capacidade (ton)',
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    tara_kg = models.IntegerField(
        'Tara (kg)',
        null=True, blank=True,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = 'Carroção na Frota'
        verbose_name_plural = 'Carroções na Frota'
        ordering = ['frota', 'numero_identificacao']

    def __str__(self):
        return f"{self.numero_identificacao} — {self.frota}"

    def clean(self):
        # Impede duplicidade de carroção na mesma etapa
        if self.veiculo_id and self.frota_id:
            etapa = self.frota.etapa
            qs = CarrocaoFrota.objects.filter(
                frota__etapa=etapa,
                veiculo=self.veiculo
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError({
                    'veiculo': f'O carroção "{self.veiculo}" já está alocado em outro trator desta etapa.'
                })


class ViagemColheita(models.Model):
    """
    Uma viagem/carga de um carroção durante a colheita.
    Registra pesagem (bruto / tara / líquido) e desconto por umidade/impureza.
    """
    carrocao = models.ForeignKey(
        CarrocaoFrota,
        on_delete=models.CASCADE,
        related_name='viagens',
        verbose_name='Carroção'
    )
    numero_viagem = models.PositiveSmallIntegerField(
        'Nº da Viagem',
        help_text='Sequencial por carroção — gerado automaticamente'
    )
    hora_saida_campo = models.DateTimeField('Saída do Campo', null=True, blank=True)
    hora_chegada_balanca = models.DateTimeField('Chegada na Balança', null=True, blank=True)
    peso_bruto_kg = models.DecimalField(
        'Peso Bruto (kg)',
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tara_usada_kg = models.DecimalField(
        'Tara (kg)',
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    peso_liquido_kg = models.DecimalField(
        'Peso Líquido (kg)',
        max_digits=10, decimal_places=2,
        default=Decimal('0'),
        help_text='Calculado: Bruto − Tara'
    )
    umidade_pct = models.DecimalField(
        'Umidade (%)',
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    impureza_pct = models.DecimalField(
        'Impureza (%)',
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))]
    )
    desconto_kg = models.DecimalField(
        'Desconto (kg)',
        max_digits=10, decimal_places=2,
        default=Decimal('0'),
        help_text='Desconto por umidade/impureza — calculado automaticamente ou informado'
    )
    peso_final_kg = models.DecimalField(
        'Peso Final (kg)',
        max_digits=10, decimal_places=2,
        default=Decimal('0'),
        help_text='Calculado: Líquido − Desconto'
    )
    foto_romaneio = models.ImageField(
        'Foto do Romaneio/Ticket',
        upload_to='colheita/romaneios/%Y/%m/',
        null=True, blank=True
    )
    observacoes = models.CharField('Observações', max_length=200, blank=True)
    data_registro = models.DateTimeField('Registrado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Viagem de Colheita'
        verbose_name_plural = 'Viagens de Colheita'
        ordering = ['carrocao', 'numero_viagem']
        unique_together = [('carrocao', 'numero_viagem')]
        indexes = [
            models.Index(fields=['carrocao', 'numero_viagem']),
        ]

    def __str__(self):
        return (
            f"{self.carrocao.numero_identificacao} — "
            f"Viagem {self.numero_viagem} ({self.peso_final_kg:.0f} kg)"
        )

    def save(self, *args, **kwargs):
        # Calcula peso líquido
        self.peso_liquido_kg = max(
            self.peso_bruto_kg - self.tara_usada_kg, Decimal('0')
        )
        # Peso final = líquido − desconto informado
        self.peso_final_kg = max(
            self.peso_liquido_kg - self.desconto_kg, Decimal('0')
        )
        super().save(*args, **kwargs)
        # Atualiza total da etapa
        self.carrocao.frota.etapa.recalcular_total()

    def clean(self):
        if (self.peso_bruto_kg is not None and self.tara_usada_kg is not None
                and self.tara_usada_kg > self.peso_bruto_kg):
            raise ValidationError({
                'tara_usada_kg': 'Tara não pode ser maior que o peso bruto.'
            })

    @classmethod
    def proximo_numero(cls, carrocao):
        ultimo = cls.objects.filter(carrocao=carrocao).order_by('-numero_viagem').first()
        return (ultimo.numero_viagem + 1) if ultimo else 1
