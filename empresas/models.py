"""
Modelos do app empresas
Sistema Multi-tenant (SaaS) para gestão de empresas e planos
"""

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
import re


class Plano(models.Model):
    """
    Configuração de planos do sistema SaaS
    Define limites e recursos disponíveis para cada tipo de assinatura
    """
    
    CODIGO_CHOICES = [
        ('PEQUENO', 'Pequeno Produtor'),
        ('MEDIO', 'Médio Produtor'),
        ('GRANDE', 'Grande Produtor'),
    ]
    
    # Identificação do plano
    codigo = models.CharField(
        'Código',
        max_length=10,
        unique=True,
        choices=CODIGO_CHOICES,
        help_text='Identificador único do plano'
    )
    
    nome = models.CharField(
        'Nome',
        max_length=100,
        help_text='Nome comercial do plano'
    )
    
    icone = models.CharField(
        'Ícone',
        max_length=10,
        default="🌱",
        help_text='Emoji ou ícone do plano'
    )
    
    # Valores e preços
    valor_mensal = models.DecimalField(
        'Valor Mensal (R$)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Valor da mensalidade'
    )
    
    valor_anual = models.DecimalField(
        'Valor Anual (R$)',
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Deixe em branco para calcular automaticamente'
    )
    
    desconto_anual = models.DecimalField(
        'Desconto Anual (%)',
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text='Percentual de desconto para pagamento anual'
    )
    
    # Limites do plano
    limite_fazendas = models.IntegerField(
        'Limite de Fazendas',
        default=2,
        validators=[MinValueValidator(1)],
        help_text='Número máximo de fazendas (999 = ilimitado)'
    )
    
    limite_usuarios = models.IntegerField(
        'Limite de Usuários',
        default=3,
        validators=[MinValueValidator(1)],
        help_text='Número máximo de usuários ativos'
    )
    
    limite_talhoes = models.IntegerField(
        'Limite de Talhões',
        default=10,
        validators=[MinValueValidator(1)],
        help_text='Número máximo de talhões cadastrados'
    )
    
    limite_produtos = models.IntegerField(
        'Limite de Produtos',
        default=50,
        validators=[MinValueValidator(1)],
        help_text='Número máximo de produtos/culturas'
    )
    
    # Recursos incluídos
    acesso_relatorios_avancados = models.BooleanField(
        'Relatórios Avançados',
        default=False,
        help_text='Permite gerar relatórios gerenciais avançados'
    )
    
    acesso_api = models.BooleanField(
        'Acesso à API',
        default=False,
        help_text='Permite integração via API REST'
    )
    
    acesso_app_mobile = models.BooleanField(
        'App Mobile',
        default=False,
        help_text='Libera acesso ao aplicativo mobile'
    )
    
    acesso_suporte_prioritario = models.BooleanField(
        'Suporte Prioritário',
        default=False,
        help_text='Atendimento com prioridade'
    )
    
    # Controle
    ativo = models.BooleanField(
        'Plano Ativo',
        default=True,
        help_text='Define se o plano está disponível para contratação'
    )
    
    ordem = models.IntegerField(
        'Ordem de Exibição',
        default=0,
        help_text='Ordem de exibição (menor = primeiro)'
    )
    
    descricao = models.TextField(
        'Descrição',
        blank=True,
        help_text='Descrição detalhada do plano'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        ordering = ['ordem', 'codigo']
        verbose_name = "Plano"
        verbose_name_plural = "Planos"
        indexes = [
            models.Index(fields=['codigo', 'ativo']),
            models.Index(fields=['ordem']),
        ]
    
    def __str__(self):
        return f"{self.icone} {self.nome}"
    
    def save(self, *args, **kwargs):
        """Calcula valor anual automaticamente se não informado"""
        if not self.valor_anual and self.valor_mensal:
            # Valor anual = 10 meses (12 - 2 grátis)
            valor_base = self.valor_mensal * 10
            if self.desconto_anual > 0:
                desconto = valor_base * (self.desconto_anual / 100)
                self.valor_anual = valor_base - desconto
            else:
                self.valor_anual = valor_base
        
        super().save(*args, **kwargs)
    
    def get_economia_anual(self):
        """Retorna economia em R$ ao pagar anualmente"""
        if self.valor_anual and self.valor_mensal:
            valor_mensal_12x = self.valor_mensal * 12
            economia = valor_mensal_12x - self.valor_anual
            return max(economia, 0)
        return 0
    
    def get_total_empresas(self):
        """Retorna total de empresas usando este plano"""
        return self.empresas.filter(ativa=True).count()
    
    def clean(self):
        """Validações do Plano - removido validação incorreta"""
        pass


class Empresa(models.Model):
    """
    Modelo central para Multi-tenant (Multiempresa)
    Cada empresa é um tenant isolado no sistema
    """
    
    # Dados básicos
    nome = models.CharField(
        'Nome da Empresa',
        max_length=150,
        unique=True,
        help_text='Razão social ou nome fantasia'
    )
    
    cnpj = models.CharField(
        'CNPJ',
        max_length=18,
        blank=True,
        null=True,
        unique=True,
        help_text='Formato: 00.000.000/0000-00'
    )
    
    telefone = models.CharField(
        'Telefone',
        max_length=20,
        blank=True,
        null=True,
        help_text='Telefone principal'
    )
    
    email = models.EmailField(
        'E-mail',
        blank=True,
        null=True,
        help_text='E-mail institucional'
    )
    
    # Endereço
    endereco = models.CharField(
        'Endereço',
        max_length=200,
        blank=True,
        null=True,
        help_text='Rua, número, complemento'
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
    
    # ✅ CORRIGIDO: Plano agora é ForeignKey correto
    plano = models.ForeignKey(
        Plano,
        on_delete=models.PROTECT,  # Não permite deletar plano se houver empresas
        related_name='empresas',
        verbose_name='Plano Contratado',
        help_text='Plano de assinatura ativo',
        null=True,  # ✅ Permite null temporariamente para migração
        blank=True
    )
    
    # Limites (herdados do plano, mas podem ser customizados)
    limite_fazendas = models.IntegerField(
        'Limite de Fazendas',
        default=2,
        help_text='Herdado do plano, mas pode ser customizado'
    )
    
    limite_usuarios = models.IntegerField(
        'Limite de Usuários',
        default=3
    )
    
    limite_talhoes = models.IntegerField(
        'Limite de Talhões',
        default=10
    )
    
    limite_produtos = models.IntegerField(
        'Limite de Produtos',
        default=50
    )
    
    # Recursos (herdados do plano)
    acesso_relatorios_avancados = models.BooleanField(
        'Acesso a Relatórios Avançados',
        default=False
    )
    
    acesso_api = models.BooleanField(
        'Acesso à API',
        default=False
    )
    
    acesso_app_mobile = models.BooleanField(
        'Acesso ao App Mobile',
        default=False
    )
    
    # Status e controle
    ativa = models.BooleanField(
        'Empresa Ativa',
        default=True,
        help_text='Define se a empresa pode acessar o sistema'
    )
    
    bloqueada = models.BooleanField(
        'Bloqueada Manualmente',
        default=False,
        help_text='Bloqueio manual do administrador'
    )
    
    bloqueada_ate = models.DateTimeField(
        'Bloqueada até',
        blank=True,
        null=True,
        help_text='Data/hora até quando estará bloqueada'
    )
    
    motivo_bloqueio = models.TextField(
        'Motivo do Bloqueio',
        blank=True,
        help_text='Justificativa do bloqueio'
    )
    
    # Financeiro
    data_expiracao = models.DateField(
        'Data de Expiração',
        blank=True,
        null=True,
        help_text='Data de vencimento do plano'
    )
    
    valor_mensalidade = models.DecimalField(
        'Valor da Mensalidade',
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    dia_vencimento = models.IntegerField(
        'Dia do Vencimento',
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text='Dia do mês para vencimento'
    )
    
    # Auditoria
    data_criacao = models.DateTimeField(
        'Data de Criação',
        auto_now_add=True
    )
    
    data_ultima_atualizacao = models.DateTimeField(
        'Última Atualização',
        auto_now=True
    )
    
    class Meta:
        ordering = ['nome']
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        indexes = [
            models.Index(fields=['ativa', 'bloqueada']),
            models.Index(fields=['plano']),
            models.Index(fields=['data_expiracao']),
        ]
    
    def __str__(self):
        return self.nome
    
    def clean(self):
        """Validações customizadas"""
        # Valida CNPJ se informado
        if self.cnpj:
            cnpj_limpo = re.sub(r'\D', '', self.cnpj)
            if len(cnpj_limpo) != 14:
                raise ValidationError({'cnpj': 'CNPJ deve ter 14 dígitos'})
        
        # Valida se plano existe
        if not self.plano:
            raise ValidationError({'plano': 'É obrigatório selecionar um plano'})
    
    def save(self, *args, **kwargs):
        """Aplica limites do plano ao salvar"""
        # Se mudou o plano ou é novo registro
        if self.pk:
            try:
                old_empresa = Empresa.objects.get(pk=self.pk)
                if old_empresa.plano != self.plano:
                    self.aplicar_limites_plano()
            except Empresa.DoesNotExist:
                self.aplicar_limites_plano()
        else:
            self.aplicar_limites_plano()
        
        super().save(*args, **kwargs)
    
    def aplicar_limites_plano(self):
        """Aplica limites e recursos do plano contratado"""
        if self.plano:
            self.limite_fazendas = self.plano.limite_fazendas
            self.limite_usuarios = self.plano.limite_usuarios
            self.limite_talhoes = self.plano.limite_talhoes
            self.limite_produtos = self.plano.limite_produtos
            self.acesso_relatorios_avancados = self.plano.acesso_relatorios_avancados
            self.acesso_api = self.plano.acesso_api
            self.acesso_app_mobile = self.plano.acesso_app_mobile
            self.valor_mensalidade = self.plano.valor_mensal
    
    def is_blocked(self):
        """Verifica se empresa está bloqueada"""
        now = timezone.now()
        
        # Bloqueio manual
        if self.bloqueada:
            return True
        
        # Bloqueio temporário
        if self.bloqueada_ate and self.bloqueada_ate > now:
            return True
        
        # Plano expirado
        if self.data_expiracao and self.data_expiracao < now.date():
            return True
        
        # Empresa inativa
        if not self.ativa:
            return True
        
        return False
    
    def get_status_display(self):
        """Retorna status legível da empresa"""
        if not self.ativa:
            return "Inativa"
        if self.bloqueada:
            return "Bloqueada"
        if self.data_expiracao and self.data_expiracao < timezone.now().date():
            return "Expirada"
        return "Ativa"
    
    def get_dias_para_vencimento(self):
        """Retorna dias restantes até vencimento"""
        if self.data_expiracao:
            dias = (self.data_expiracao - timezone.now().date()).days
            return dias
        return None
    
    def esta_proximo_vencimento(self, dias=7):
        """Verifica se está próximo do vencimento"""
        dias_restantes = self.get_dias_para_vencimento()
        if dias_restantes is not None:
            return 0 <= dias_restantes <= dias
        return False
    
    def get_total_usuarios(self):
        """Retorna total de usuários ativos"""
        return self.usuarios.filter(is_active=True).count()
    
    def pode_adicionar_usuario(self):
        """Verifica se pode adicionar mais usuários"""
        if self.limite_usuarios >= 999:  # Ilimitado
            return True
        return self.get_total_usuarios() < self.limite_usuarios
    
    def get_cnpj_formatado(self):
        """Retorna CNPJ formatado"""
        if self.cnpj:
            cnpj = re.sub(r'\D', '', self.cnpj)
            if len(cnpj) == 14:
                return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return self.cnpj
        