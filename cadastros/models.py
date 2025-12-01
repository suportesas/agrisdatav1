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
    
    # Arquivo
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
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_enviados',
        verbose_name='Enviado por'
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



        """
ADICIONE ESTES MODELOS AO FINAL DO ARQUIVO cadastros/models.py
(Após o modelo DocumentoFazenda)
"""

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
        'Data de Admissão'
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
        
        # Valida limite de culturas do plano (se houver)
        if not self.pk and self.empresa:
            total_culturas = Cultura.objects.filter(
                empresa=self.empresa,
                ativa=True
            ).count()
            
            if hasattr(self.empresa, 'limite_produtos'):
                if total_culturas >= self.empresa.limite_produtos:
                    raise ValidationError(
                        f'Limite de culturas atingido! Seu plano permite apenas '
                        f'{self.empresa.limite_produtos} cultura(s) ativa(s).'
                    )
    
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