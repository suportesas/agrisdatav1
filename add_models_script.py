"""
Script para adicionar os novos modelos ao compras/models.py
Execute após confirmar a estrutura
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Os modelos serão adicionados manualmente ao models.py
# Este script serve como documentação

models_to_add = """

# ===== NOVOS MODELOS - TIPOS DE DIVERGÊNCIA E AVALIAÇÃO =====

class TipoDivergencia(models.Model):
    \"\"\"
    Tipos de divergência que podem ocorrer no recebimento
    Permite configuração flexível pelo usuário
    \"\"\"
    
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
    
    data_criacao = models.DateTimeField('Data de Criação', auto_now_add=True)
    data_atualizacao = models.DateTimeField('Última Atualização', auto_now=True)
    
    class Meta:
        verbose_name = 'Tipo de Divergência'
        verbose_name_plural = 'Tipos de Divergência'
        ordering = ['empresa', 'severidade', 'nome']
        unique_together = ['empresa', 'codigo']
    
    def __str__(self):
        return f"[{self.severidade}] {self.nome}"
"""

print(models_to_add)
