"""
Modelos para Métricas e Dashboard Executivo do SaaS
"""

from django.db import models
from django.utils import timezone
from empresas.models import Empresa, Plano
from usuarios.models import Usuario


class ConsumoRecurso(models.Model):
    """
    Registro de consumo de recursos por empresa
    Usado para análise de uso e cobranças extras
    """
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='consumo_recursos'
    )
    
    # Consumo atual
    fazendas_usadas = models.IntegerField(default=0)
    usuarios_ativos = models.IntegerField(default=0)
    talhoes_cadastrados = models.IntegerField(default=0)
    produtos_cadastrados = models.IntegerField(default=0)
    
    # Limites do plano (snapshot)
    limite_fazendas = models.IntegerField()
    limite_usuarios = models.IntegerField()
    limite_talhoes = models.IntegerField()
    limite_produtos = models.IntegerField()
    
    # Cálculos de percentual
    percentual_fazendas = models.DecimalField(
        'Uso de Fazendas (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    percentual_usuarios = models.DecimalField(
        'Uso de Usuários (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    percentual_talhoes = models.DecimalField(
        'Uso de Talhões (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    percentual_produtos = models.DecimalField(
        'Uso de Produtos (%)',
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Alertas (se atingiu 80%)
    alerta_fazendas = models.BooleanField(default=False)
    alerta_usuarios = models.BooleanField(default=False)
    alerta_talhoes = models.BooleanField(default=False)
    alerta_produtos = models.BooleanField(default=False)
    
    # Data
    data_calculo = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-data_calculo']
        indexes = [
            models.Index(fields=['empresa', '-data_calculo']),
            models.Index(fields=['alerta_fazendas', '-data_calculo']),
        ]
    
    def __str__(self):
        return f"{self.empresa.nome} - {self.data_calculo.strftime('%d/%m/%Y')}"
    
    def calcular_percentuais(self):
        """Calcula percentuais de uso"""
        if self.limite_fazendas > 0:
            self.percentual_fazendas = (self.fazendas_usadas / self.limite_fazendas * 100) if self.limite_fazendas != 999 else 0
            self.alerta_fazendas = self.percentual_fazendas >= 80
        
        if self.limite_usuarios > 0:
            self.percentual_usuarios = (self.usuarios_ativos / self.limite_usuarios * 100) if self.limite_usuarios != 999 else 0
            self.alerta_usuarios = self.percentual_usuarios >= 80
        
        if self.limite_talhoes > 0:
            self.percentual_talhoes = (self.talhoes_cadastrados / self.limite_talhoes * 100) if self.limite_talhoes != 999 else 0
            self.alerta_talhoes = self.percentual_talhoes >= 80
        
        if self.limite_produtos > 0:
            self.percentual_produtos = (self.produtos_cadastrados / self.limite_produtos * 100) if self.limite_produtos != 999 else 0
            self.alerta_produtos = self.percentual_produtos >= 80


class Alerta(models.Model):
    """
    Alertas automáticos gerados pelo sistema
    """
    
    TIPOS = [
        ('LIMITE_PROXIMO', 'Limite próximo de ser atingido'),
        ('LIMITE_ATINGIDO', 'Limite atingido'),
        ('LIMITE_EXCEDIDO', 'Limite excedido'),
        ('VENCIMENTO', 'Plano vencendo'),
        ('PAGAMENTO_PENDENTE', 'Pagamento pendente'),
        ('ERRO_SISTEMA', 'Erro no sistema'),
        ('PERFORMANCE', 'Problema de performance'),
    ]
    
    SEVERIDADE = [
        ('BAIXA', 'Baixa'),
        ('MÉDIA', 'Média'),
        ('ALTA', 'Alta'),
        ('CRÍTICA', 'Crítica'),
    ]
    
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='alertas',
        null=True,
        blank=True
    )
    
    tipo = models.CharField(max_length=20, choices=TIPOS)
    severidade = models.CharField(max_length=10, choices=SEVERIDADE, default='MÉDIA')
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    
    ativo = models.BooleanField(default=True)
    lido = models.BooleanField(default=False)
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_leitura = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['ativo', '-data_criacao']),
            models.Index(fields=['severidade', '-data_criacao']),
            models.Index(fields=['empresa', 'ativo']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.titulo}"
    
    def marcar_como_lido(self):
        """Marca alerta como lido"""
        if not self.lido:
            self.lido = True
            self.data_leitura = timezone.now()
            self.save()


class MetricaDiaria(models.Model):
    """
    Snapshot diário de métricas do sistema
    Para análise de trends e histórico
    """
    
    data = models.DateField(auto_now_add=True, db_index=True)
    
    # Contadores
    total_empresas = models.IntegerField(default=0)
    total_empresas_ativas = models.IntegerField(default=0)
    total_usuarios = models.IntegerField(default=0)
    total_usuarios_ativos = models.IntegerField(default=0)
    
    # Distribuição por plano
    empresas_pequeno = models.IntegerField(default=0)
    empresas_medio = models.IntegerField(default=0)
    empresas_grande = models.IntegerField(default=0)
    empresas_enterprise = models.IntegerField(default=0)
    
    # Financeiro
    receita_total = models.DecimalField(
        'Receita Total (R$)',
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Alertas
    alertas_ativos = models.IntegerField(default=0)
    alertas_criticos = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-data']
        indexes = [models.Index(fields=['-data'])]
        unique_together = ['data']
    
    def __str__(self):
        return f"Métricas - {self.data.strftime('%d/%m/%Y')}"


class LogAcesso(models.Model):
    """
    Log de acessos ao dashboard executivo
    Para auditoria de quem acessa informações sensíveis
    """
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='dashboard_acessos'
    )
    
    modulo = models.CharField(
        'Módulo Acessado',
        max_length=50,
        choices=[
            ('DASHBOARD', 'Dashboard Principal'),
            ('EMPRESAS', 'Gestão de Empresas'),
            ('FATURAS', 'Gestão de Faturas'),
            ('METRICAS', 'Métricas/Relatórios'),
            ('AUDITORIA', 'Auditoria'),
            ('ALERTAS', 'Alertas'),
        ]
    )
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    data_acesso = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-data_acesso']
        indexes = [
            models.Index(fields=['usuario', '-data_acesso']),
            models.Index(fields=['-data_acesso']),
        ]
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_modulo_display()}"
