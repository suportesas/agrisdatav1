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
    """
    Endereços múltiplos da fazenda
    Tipos: Faturamento, Cobrança, Entrega, Notify
    """
    
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
        help_text='Sigla do estado'
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
        return f"{self.fazenda.nome} - {self.area.nome} - {self.nome}"
    
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
    celular = models.CharField('Celular', max_length=20, blank=True)
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
