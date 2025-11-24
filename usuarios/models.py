"""
Modelos do app usuarios
Sistema de autenticação multi-tenant para ERP Agrícola
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator


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


# ============================================
# MODELOS
# ============================================

class Usuario(AbstractUser):
    """
    Modelo de usuário customizado para o sistema
    Cada usuário pertence a uma empresa (multi-tenant)
    Herda de AbstractUser do Django para autenticação completa
    """
    
    TIPO_USUARIO = (
        ('ADMIN', 'Administrador'),
        ('GERENTE', 'Gerente'),
        ('FUNC', 'Funcionário'),
        ('PROD', 'Produtor'),
        ('VENDEDOR', 'Vendedor'),
        ('FINANCEIRO', 'Financeiro'),
    )
    
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
        max_length=15,
        choices=TIPO_USUARIO,
        default='FUNC',
        help_text='Define as permissões e acesso do usuário'
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
    
    def is_admin_empresa(self):
        """Verifica se usuário é admin da empresa"""
        return self.tipo == 'ADMIN' or self.is_superuser
    
    def pode_gerenciar_usuarios(self):
        """Verifica se pode gerenciar outros usuários"""
        return self.tipo in ['ADMIN', 'GERENTE'] or self.is_superuser
    
    def pode_acessar_financeiro(self):
        """Verifica se tem acesso ao financeiro"""
        return self.tipo in ['ADMIN', 'GERENTE', 'FINANCEIRO'] or self.is_superuser
    
    def pode_fazer_vendas(self):
        """Verifica se pode registrar vendas"""
        return self.tipo in ['ADMIN', 'GERENTE', 'VENDEDOR'] or self.is_superuser


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