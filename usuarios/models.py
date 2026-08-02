"""
Modelos do app usuarios
Sistema de autenticação multi-tenant para Agrisdata
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.cache import cache
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone


TIPO_CONFIG_CACHE_TTL = 120  # segundos — TipoUsuario muda raramente (configuração de admin)

DEFAULT_TIPOS_USUARIO = [
    {
        'codigo': 'ADMIN',
        'nome': 'Administrador',
        'descricao': 'Administrador da empresa com acesso ampliado.',
        'ordem': 10,
        'protegido': True,
        'administrador_empresa': True,
        'permite_gerenciar_usuarios': True,
        'permite_acessar_financeiro': True,
        'permite_fazer_vendas': True,
    },
    {
        'codigo': 'GERENTE',
        'nome': 'Gerente',
        'descricao': 'Gerencia usuários e acompanha operações da empresa.',
        'ordem': 20,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': True,
        'permite_acessar_financeiro': True,
        'permite_fazer_vendas': True,
    },
    {
        'codigo': 'FUNC',
        'nome': 'Funcionário',
        'descricao': 'Perfil operacional padrão.',
        'ordem': 30,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': False,
        'permite_acessar_financeiro': False,
        'permite_fazer_vendas': False,
    },
    {
        'codigo': 'PROD',
        'nome': 'Produtor',
        'descricao': 'Perfil voltado para operação de produção.',
        'ordem': 40,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': False,
        'permite_acessar_financeiro': False,
        'permite_fazer_vendas': False,
    },
    {
        'codigo': 'VENDEDOR',
        'nome': 'Vendedor',
        'descricao': 'Perfil comercial com acesso a vendas.',
        'ordem': 50,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': False,
        'permite_acessar_financeiro': False,
        'permite_fazer_vendas': True,
    },
    {
        'codigo': 'FINANCEIRO',
        'nome': 'Financeiro',
        'descricao': 'Perfil com acesso financeiro.',
        'ordem': 60,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': False,
        'permite_acessar_financeiro': True,
        'permite_fazer_vendas': False,
    },
    {
        'codigo': 'MOTORISTA',
        'nome': 'Motorista',
        'descricao': 'Login unificado do Portal do Motorista.',
        'ordem': 70,
        'protegido': True,
        'administrador_empresa': False,
        'permite_gerenciar_usuarios': False,
        'permite_acessar_financeiro': False,
        'permite_fazer_vendas': False,
    },
]


def get_codigos_tipos_admin_empresa():
    codigos = list(
        TipoUsuario.objects.filter(administrador_empresa=True, ativo=True)
        .values_list('codigo', flat=True)
    )
    if 'ADMIN' not in codigos:
        codigos.append('ADMIN')
    return codigos


# ============================================
# MANAGERS CUSTOMIZADOS
# ============================================

class EmpresaQuerySet(models.QuerySet):
    """QuerySet customizado para filtrar por empresa"""
    
    def da_empresa(self, empresa):
        """Filtra registros da empresa especificada"""
        if empresa:
            return self.filter(empresa=empresa)
        return self.none()
    
    def ativos(self):
        """Retorna apenas usuários ativos"""
        return self.filter(is_active=True)
    
    def por_tipo(self, tipo):
        """Filtra por tipo de usuário"""
        return self.filter(tipo=tipo)


class UsuarioManager(BaseUserManager):
    """Manager customizado para Usuario - herda de BaseUserManager"""
    
    def get_queryset(self):
        return EmpresaQuerySet(self.model, using=self._db)
    
    def da_empresa(self, empresa):
        """Retorna usuários da empresa"""
        return self.get_queryset().da_empresa(empresa)
    
    def ativos(self):
        """Retorna apenas usuários ativos"""
        return self.get_queryset().ativos()
    
    def por_tipo(self, tipo):
        """Filtra por tipo"""
        return self.get_queryset().por_tipo(tipo)
    
    def get_by_natural_key(self, username):
        """
        Método obrigatório para autenticação do Django
        Permite criar superusuário e fazer login
        """
        return self.get(**{self.model.USERNAME_FIELD: username})
    
    def _create_user(self, username, email, password, **extra_fields):
        """
        Cria e salva um usuário com username, email e senha fornecidos
        """
        if not username:
            raise ValueError('O username deve ser fornecido')
        
        email = self.normalize_email(email) if email else ''
        username = self.model.normalize_username(username)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Cria um usuário normal"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Cria um superusuário"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuário deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuário deve ter is_superuser=True.')
        
        return self._create_user(username, email, password, **extra_fields)


class TipoUsuario(models.Model):
    """Tipos de usuário configuráveis usados pelo campo Usuario.tipo."""

    codigo_validator = RegexValidator(
        regex=r'^[A-Z0-9_]+$',
        message='O código deve conter apenas letras maiúsculas, números e underscore.'
    )

    codigo = models.CharField(
        'Código',
        max_length=30,
        unique=True,
        validators=[codigo_validator],
        help_text='Identificador interno usado nas regras do sistema. Ex.: SUPORTE.'
    )
    nome = models.CharField('Nome', max_length=60)
    descricao = models.TextField('Descrição', blank=True)
    ordem = models.PositiveIntegerField('Ordem', default=100)
    ativo = models.BooleanField('Ativo', default=True)
    protegido = models.BooleanField(
        'Protegido',
        default=False,
        help_text='Tipos protegidos não podem ser excluídos pelo CRUD.'
    )
    administrador_empresa = models.BooleanField(
        'Conta como administrador da empresa',
        default=False,
        help_text='Libera as ações administrativas e permissões equivalentes a admin.'
    )
    permite_gerenciar_usuarios = models.BooleanField(
        'Pode gerenciar usuários',
        default=False
    )
    permite_acessar_financeiro = models.BooleanField(
        'Pode acessar financeiro',
        default=False
    )
    permite_fazer_vendas = models.BooleanField(
        'Pode fazer vendas',
        default=False
    )

    class Meta:
        verbose_name = 'Tipo de Usuário'
        verbose_name_plural = 'Tipos de Usuário'
        ordering = ['ordem', 'nome']
        indexes = [
            models.Index(fields=['ativo', 'ordem']),
            models.Index(fields=['codigo']),
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.codigo = (self.codigo or '').upper().strip()
        super().save(*args, **kwargs)


# ============================================
# MODELOS
# ============================================

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado para o sistema
    Cada usuário pertence a uma empresa (multi-tenant)
    Herda de AbstractUser do Django para autenticação completa
    """
    
    # Relacionamento com empresa (multi-tenant)
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='Empresa',
        help_text='Empresa à qual o usuário pertence'
    )
    
    # Tipo de usuário
    tipo = models.CharField(
        'Tipo de Usuário',
        max_length=30,
        default='FUNC',
        db_index=True,
        help_text='Código do tipo de usuário configurado no cadastro de tipos.'
    )
    
    # Informações de contato
    telefone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Telefone deve estar no formato: '+999999999'. Até 15 dígitos."
    )
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True,
        null=True,
        validators=[telefone_validator],
        help_text='Formato: +55 84 99999-9999'
    )
    
    # Campos adicionais
    cpf = models.CharField(
        'CPF',
        max_length=14,
        blank=True,
        null=True,
        unique=True,
        help_text='Formato: 000.000.000-00'
    )
    
    data_nascimento = models.DateField(
        'Data de Nascimento',
        blank=True,
        null=True
    )
    
    foto = models.ImageField(
        'Foto de Perfil',
        upload_to='usuarios/fotos/',
        blank=True,
        null=True
    )
    
    # Campos específicos para vendedores
    comissao_vendas = models.DecimalField(
        'Comissão de Vendas (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Percentual de comissão sobre vendas'
    )
    
    # Funções/roles da empresa
    roles = models.ManyToManyField(
        'empresas.Role',
        blank=True,
        related_name='usuarios',
        verbose_name='Funções',
        help_text='Funções atribuídas ao usuário (ex.: Proprietário, Almoxarife)'
    )
    
    must_change_password = models.BooleanField(
        'Deve trocar a senha',
        default=False,
        help_text='Força o usuário a alterar a senha provisória no próximo acesso.',
    )

    # Campos de controle
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
    
    observacoes = models.TextField(
        'Observações',
        blank=True,
        help_text='Observações gerais sobre o usuário'
    )
    
    # Manager customizado
    objects = UsuarioManager()
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ['empresa__nome', 'username']
        indexes = [
            models.Index(fields=['empresa', 'tipo']),
            models.Index(fields=['empresa', 'is_active']),
        ]
    
    def __str__(self):
        if self.empresa:
            return f"{self.get_full_name() or self.username} ({self.empresa.nome})"
        return f"{self.get_full_name() or self.username}"
    
    def get_full_name(self):
        """Retorna nome completo do usuário"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def get_tipo_config(self):
        """Retorna a configuração do tipo do usuário, quando existir."""
        if hasattr(self, '_tipo_config_cache'):
            return self._tipo_config_cache

        if not self.tipo:
            self._tipo_config_cache = None
            return self._tipo_config_cache

        cache_key = f'tipo_usuario:{self.tipo}'
        tipo_config = cache.get(cache_key)
        if tipo_config is None:
            tipo_config = TipoUsuario.objects.filter(codigo=self.tipo).first()
            cache.set(cache_key, tipo_config, TIPO_CONFIG_CACHE_TTL)
        self._tipo_config_cache = tipo_config
        return self._tipo_config_cache

    def get_grupos_nomes(self):
        """Nomes dos grupos do usuário, memoizados na instância (1 query por request)."""
        if not hasattr(self, '_grupos_nomes_cache'):
            self._grupos_nomes_cache = list(self.groups.values_list('name', flat=True))
        return self._grupos_nomes_cache

    def get_tipo_display(self):
        """Retorna o nome amigável do tipo mesmo sem choices fixos."""
        tipo_config = self.get_tipo_config()
        if tipo_config:
            return tipo_config.nome

        if not self.tipo:
            return 'Sem tipo'

        return self.tipo.replace('_', ' ').title()

    @property
    def tipo_badge_class(self):
        tipo_config = self.get_tipo_config()
        codigo = (self.tipo or '').upper()

        if codigo == 'ADMIN' or (tipo_config and tipo_config.administrador_empresa):
            return 'bg-danger bg-opacity-10 text-danger border border-danger'
        if codigo == 'GERENTE' or (tipo_config and tipo_config.permite_gerenciar_usuarios):
            return 'bg-warning bg-opacity-10 text-warning border border-warning'
        if codigo == 'VENDEDOR' or (tipo_config and tipo_config.permite_fazer_vendas):
            return 'bg-success bg-opacity-10 text-success border border-success'
        if codigo == 'FINANCEIRO' or (tipo_config and tipo_config.permite_acessar_financeiro):
            return 'bg-info bg-opacity-10 text-info border border-info'
        if codigo == 'PROD':
            return 'bg-secondary bg-opacity-10 text-secondary border border-secondary'
        return 'bg-secondary bg-opacity-10 text-secondary border border-secondary'

    @property
    def tipo_badge_icon(self):
        tipo_config = self.get_tipo_config()
        codigo = (self.tipo or '').upper()

        if codigo == 'ADMIN' or (tipo_config and tipo_config.administrador_empresa):
            return 'bi-shield-fill-check'
        if codigo == 'GERENTE' or (tipo_config and tipo_config.permite_gerenciar_usuarios):
            return 'bi-person-badge'
        if codigo == 'VENDEDOR' or (tipo_config and tipo_config.permite_fazer_vendas):
            return 'bi-cart-check'
        if codigo == 'FINANCEIRO' or (tipo_config and tipo_config.permite_acessar_financeiro):
            return 'bi-cash-coin'
        if codigo == 'PROD':
            return 'bi-gear'
        return 'bi-person'
    
    def is_admin_empresa(self):
        """Verifica se usuário é admin da empresa"""
        tipo_config = self.get_tipo_config()
        return self.is_superuser or bool(tipo_config and tipo_config.administrador_empresa) or self.tipo == 'ADMIN'
    
    def pode_gerenciar_usuarios(self):
        """Verifica se pode gerenciar outros usuários"""
        tipo_config = self.get_tipo_config()
        return (
            self.is_superuser or
            self.is_admin_empresa() or
            bool(tipo_config and tipo_config.permite_gerenciar_usuarios) or
            self.tipo in ['ADMIN', 'GERENTE']
        )
    
    def pode_aprovar_manutencao(self):
        """Verifica se pode aprovar/reprovar solicitações de manutenção de frota feitas pelo motorista"""
        return self.is_superuser or self.is_admin_empresa() or self.tipo == 'GERENTE'

    def pode_acessar_financeiro(self):
        """Verifica se tem acesso ao financeiro"""
        tipo_config = self.get_tipo_config()
        return (
            self.is_superuser or
            self.is_admin_empresa() or
            bool(tipo_config and tipo_config.permite_acessar_financeiro) or
            self.tipo in ['ADMIN', 'GERENTE', 'FINANCEIRO']
        )
    
    def pode_fazer_vendas(self):
        """Verifica se pode registrar vendas"""
        tipo_config = self.get_tipo_config()
        return (
            self.is_superuser or
            self.is_admin_empresa() or
            bool(tipo_config and tipo_config.permite_fazer_vendas) or
            self.tipo in ['ADMIN', 'GERENTE', 'VENDEDOR']
        )


class LoginRegistro(models.Model):
    """
    Registro de auditoria de logins no sistema
    Guarda informações sobre cada acesso para segurança e análise
    """
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='logins',
        verbose_name='Usuário'
    )
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='logins',
        null=True,  # Permite NULL para superusuário sem empresa
        blank=True,
        verbose_name='Empresa',
        help_text='Empresa acessada no login'
    )
    
    data_login = models.DateTimeField(
        'Data/Hora do Login',
        auto_now_add=True,
        db_index=True
    )
    
    ip_address = models.GenericIPAddressField(
        'Endereço IP',
        blank=True,
        null=True,
        help_text='IP de origem do acesso'
    )
    
    user_agent = models.CharField(
        'User Agent',
        max_length=500,
        blank=True,
        help_text='Navegador/dispositivo utilizado'
    )
    
    sucesso = models.BooleanField(
        'Login com Sucesso',
        default=True,
        help_text='Indica se o login foi bem-sucedido'
    )
    
    class Meta:
        verbose_name = "Registro de Login"
        verbose_name_plural = "Registros de Login"
        ordering = ['-data_login']
        indexes = [
            models.Index(fields=['empresa', '-data_login']),
            models.Index(fields=['usuario', '-data_login']),
            models.Index(fields=['-data_login']),
        ]
    
    def __str__(self):
        status = "✓" if self.sucesso else "✗"
        empresa_nome = self.empresa.nome if self.empresa else "Sistema"
        return f"{status} {self.usuario.username} - {empresa_nome} ({self.data_login:%d/%m/%Y %H:%M})"
    
    def get_navegador(self):
        """Extrai nome do navegador do user agent"""
        if not self.user_agent:
            return "Desconhecido"
        
        ua = self.user_agent.lower()
        if 'firefox' in ua:
            return 'Firefox'
        elif 'chrome' in ua and 'edg' not in ua:
            return 'Chrome'
        elif 'safari' in ua and 'chrome' not in ua:
            return 'Safari'
        elif 'edg' in ua:
            return 'Edge'
        elif 'opera' in ua or 'opr' in ua:
            return 'Opera'
        return 'Outro'


class PerfilUsuario(models.Model):
    """
    Perfil estendido do usuário com informações adicionais
    Separado do modelo Usuario para melhor organização
    """
    
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name='Usuário'
    )
    
    cargo = models.CharField(
        'Cargo',
        max_length=100,
        blank=True
    )
    
    departamento = models.CharField(
        'Departamento',
        max_length=100,
        blank=True
    )
    
    endereco = models.CharField(
        'Endereço',
        max_length=200,
        blank=True
    )
    
    cidade = models.CharField(
        'Cidade',
        max_length=100,
        blank=True
    )
    
    estado = models.CharField(
        'Estado',
        max_length=2,
        blank=True,
        help_text='Sigla do estado (ex: RN)'
    )
    
    cep = models.CharField(
        'CEP',
        max_length=10,
        blank=True
    )
    
    # Configurações de notificação
    receber_email_vendas = models.BooleanField(
        'Receber E-mails de Vendas',
        default=True
    )
    
    receber_email_estoque = models.BooleanField(
        'Receber E-mails de Estoque',
        default=False
    )
    
    receber_email_financeiro = models.BooleanField(
        'Receber E-mails Financeiros',
        default=False
    )
    
    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"
    
    def __str__(self):
        return f"Perfil de {self.usuario.username}"


# Importa modelos de sincronização Supabase
try:
    from usuarios.models_supabase import SupabaseUsuarioSync, LoginSupabase
except ImportError:
    pass  # Modelos não disponíveis se supabase não está configurado


class DoisFatoresAutenticacao(models.Model):
    """
    Autenticação de Dois Fatores (2FA) via TOTP (Time-based One-Time Password)
    Aumenta segurança do acesso ao sistema
    """
    
    METODOS = (
        ('TOTP', 'Autenticador (Google Authenticator, Authy, Microsoft Authenticator)'),
        ('SMS', 'SMS (texto)'),
        ('EMAIL', 'E-mail'),
        ('BACKUP', 'Códigos de Backup'),
    )
    
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='autenticacao_dois_fatores',
        verbose_name='Usuário'
    )
    
    ativo = models.BooleanField(
        '2FA Ativo',
        default=False,
        help_text='Se o 2FA está habilitado para este usuário'
    )
    
    metodo_primario = models.CharField(
        'Método Primário',
        max_length=10,
        choices=METODOS,
        default='TOTP'
    )
    
    chave_secreta = models.CharField(
        'Chave Secreta',
        max_length=32,
        blank=True,
        help_text='Chave para gerar códigos TOTP'
    )
    
    codigos_backup = models.JSONField(
        'Códigos de Backup',
        default=list,
        blank=True,
        help_text='Lista de códigos de backup para emergências'
    )
    
    telefone_2fa = models.CharField(
        'Telefone para 2FA',
        max_length=20,
        blank=True,
        help_text='Telefone para receber SMS com código'
    )
    
    data_habilitacao = models.DateTimeField(
        'Data de Habilitação',
        null=True,
        blank=True,
        auto_now_add=True
    )
    
    ultimo_uso = models.DateTimeField(
        'Último Uso',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Autenticação de Dois Fatores"
        verbose_name_plural = "Autenticações de Dois Fatores"
    
    def __str__(self):
        status = "✓ Ativo" if self.ativo else "✗ Inativo"
        return f"2FA {self.usuario.username} - {status}"


class LoginAnomalia(models.Model):
    """
    Detecta e registra anomalias em logins
    Identifica IPs, navegadores ou horários suspeitos
    """
    
    TIPO_ANOMALIA = (
        ('IP_NOVO', 'IP Novo'),
        ('NAVEGADOR_NOVO', 'Navegador Novo'),
        ('LOCALIZACAO_NOVA', 'Localização Nova'),
        ('HORARIO_SUSPEITO', 'Horário Suspeito'),
        ('MULTIPLOS_IPS', 'Múltiplos IPs em Curto Tempo'),
        ('FORCA_BRUTA', 'Tentativa de Força Bruta'),
    )
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='anomalias_login',
        verbose_name='Usuário'
    )
    
    tipo = models.CharField(
        'Tipo de Anomalia',
        max_length=20,
        choices=TIPO_ANOMALIA
    )
    
    ip_address = models.GenericIPAddressField(
        'Endereço IP',
        blank=True,
        null=True
    )
    
    user_agent = models.CharField(
        'User Agent',
        max_length=500,
        blank=True
    )
    
    descricao = models.TextField(
        'Descrição',
        help_text='Detalhes da anomalia detectada'
    )
    
    data_deteccao = models.DateTimeField(
        'Data de Detecção',
        auto_now_add=True,
        db_index=True
    )
    
    confirmada = models.BooleanField(
        'Confirmada como Suspeita',
        default=False
    )
    
    resolucao = models.CharField(
        'Resolução',
        max_length=200,
        blank=True,
        choices=[
            ('aprovada', 'Aprovada pelo usuário'),
            ('bloqueada', 'Bloqueada pelo admin'),
            ('falso_positivo', 'Falso positivo (ignorar)'),
        ]
    )
    
    class Meta:
        verbose_name = "Anomalia de Login"
        verbose_name_plural = "Anomalias de Login"
        ordering = ['-data_deteccao']
        indexes = [
            models.Index(fields=['usuario', '-data_deteccao']),
            models.Index(fields=['confirmada', '-data_deteccao']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_display()} ({self.data_deteccao:%d/%m/%Y %H:%M})"


class AlertaSeguranca(models.Model):
    """
    Alertas de segurança para proprietários e admins
    Notifica sobre eventos suspeitos no sistema
    """
    
    NIVEL = (
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
        ('CRITICO', 'Crítico'),
    )
    
    STATUS = (
        ('NOVO', 'Novo'),
        ('LIDO', 'Lido'),
        ('EM_INVESTIGACAO', 'Em Investigação'),
        ('RESOLVIDO', 'Resolvido'),
    )
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='alertas_seguranca',
        verbose_name='Usuário'
    )
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='alertas_seguranca',
        verbose_name='Empresa'
    )
    
    titulo = models.CharField(
        'Título',
        max_length=200
    )
    
    descricao = models.TextField(
        'Descrição'
    )
    
    nivel = models.CharField(
        'Nível de Severidade',
        max_length=10,
        choices=NIVEL,
        default='MEDIO'
    )
    
    status = models.CharField(
        'Status',
        max_length=20,
        choices=STATUS,
        default='NOVO'
    )
    
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True,
        db_index=True
    )
    
    data_leitura = models.DateTimeField(
        'Data de Leitura',
        null=True,
        blank=True
    )
    
    data_resolucao = models.DateTimeField(
        'Data de Resolução',
        null=True,
        blank=True
    )
    
    enviado_email = models.BooleanField(
        'Email Enviado',
        default=False
    )
    
    dados_adicionais = models.JSONField(
        'Dados Adicionais',
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = "Alerta de Segurança"
        verbose_name_plural = "Alertas de Segurança"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['empresa', '-data_criacao']),
            models.Index(fields=['status', '-data_criacao']),
            models.Index(fields=['nivel', '-data_criacao']),
        ]
    
    def __str__(self):
        return f"[{self.get_nivel_display()}] {self.titulo} - {self.usuario.username}"


class TrocaSenhaEmergencial(models.Model):
    """
    Registra troca emergencial de senha executada por superadmin.
    Permite cancelamento seguro com rollback da hash anterior no Django.
    """

    STATUS = (
        ('ATIVA', 'Ativa'),
        ('CANCELADA', 'Cancelada'),
        ('EXPIRADA', 'Expirada'),
    )

    usuario_alvo = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='trocas_senha_emergenciais_recebidas',
        verbose_name='Usuário Alvo',
    )

    executado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='trocas_senha_emergenciais_executadas',
        verbose_name='Executado Por',
    )

    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='trocas_senha_emergenciais',
        verbose_name='Empresa',
    )

    senha_anterior_hash = models.CharField(
        'Hash da Senha Anterior',
        max_length=128,
        help_text='Hash anterior para rollback seguro no Django.',
    )

    token_cancelamento_hash = models.CharField(
        'Hash do Token de Cancelamento',
        max_length=128,
        unique=True,
        db_index=True,
    )

    motivo = models.TextField('Motivo da Ação', blank=True)

    status = models.CharField(
        'Status',
        max_length=12,
        choices=STATUS,
        default='ATIVA',
        db_index=True,
    )

    data_execucao = models.DateTimeField('Data de Execução', auto_now_add=True, db_index=True)
    expira_em = models.DateTimeField('Expira Em', db_index=True)
    data_cancelamento = models.DateTimeField('Data de Cancelamento', null=True, blank=True)

    ip_execucao = models.GenericIPAddressField('IP da Execução', blank=True, null=True)
    user_agent_execucao = models.CharField('User Agent da Execução', max_length=500, blank=True)
    ip_cancelamento = models.GenericIPAddressField('IP do Cancelamento', blank=True, null=True)
    user_agent_cancelamento = models.CharField('User Agent do Cancelamento', max_length=500, blank=True)

    class Meta:
        verbose_name = 'Troca de Senha Emergencial'
        verbose_name_plural = 'Trocas de Senha Emergenciais'
        ordering = ['-data_execucao']
        indexes = [
            models.Index(fields=['empresa', '-data_execucao']),
            models.Index(fields=['usuario_alvo', '-data_execucao']),
            models.Index(fields=['status', '-data_execucao']),
        ]

    def __str__(self):
        return f"{self.usuario_alvo.username} - {self.status} ({self.data_execucao:%d/%m/%Y %H:%M})"

    def is_expirada(self):
        return timezone.now() > self.expira_em


class GraficoAcesso(models.Model):
    """
    Agregação diária de dados de login para exibir em gráficos
    Otimiza queries para análises de tendências
    """
    
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.CASCADE,
        related_name='graficos_acesso',
        verbose_name='Empresa'
    )
    
    data = models.DateField(
        'Data',
        db_index=True
    )
    
    total_logins = models.IntegerField(
        'Total de Logins',
        default=0
    )
    
    logins_sucesso = models.IntegerField(
        'Logins com Sucesso',
        default=0
    )
    
    logins_falha = models.IntegerField(
        'Logins Falhados',
        default=0
    )
    
    usuarios_unicos = models.IntegerField(
        'Usuários Únicos',
        default=0
    )
    
    ips_unicos = models.IntegerField(
        'IPs Únicos',
        default=0
    )
    
    anomalias_detectadas = models.IntegerField(
        'Anomalias Detectadas',
        default=0
    )
    
    class Meta:
        verbose_name = "Gráfico de Acesso"
        verbose_name_plural = "Gráficos de Acesso"
        ordering = ['-data']
        unique_together = ('empresa', 'data')
        indexes = [
            models.Index(fields=['empresa', '-data']),
        ]
    
    def __str__(self):
        return f"{self.empresa.nome} - {self.data:%d/%m/%Y}"