"""
Script para reconstruir produtos/models.py com multi-tenant correto
"""

models_content = """from django.db import models
from cadastros.models import NCM, Fornecedor, CFOP


class UnidadeMedida(models.Model):
    TIPO_CHOICES = [
        ('PESO', 'Peso'),
        ('VOLUME', 'Volume'),
        ('UNIDADE', 'Unidade'),
        ('AREA', 'Área'),
        ('COMPRIMENTO', 'Comprimento'),
    ]
    
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='unidades_medida', verbose_name='Empresa')
    
    sigla = models.CharField(max_length=10, verbose_name='Sigla')
    nome = models.CharField(max_length=50, verbose_name='Nome')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Unidade de Medida'
        verbose_name_plural = 'Unidades de Medida'
        ordering = ['nome']
        unique_together = [['empresa', 'sigla']]
    
    def __str__(self):
        return f"{self.sigla} - {self.nome}"


class Categoria(models.Model):
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='categorias_produto', verbose_name='Empresa')
    
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['nome']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class SubCategoria(models.Model):
    # Multi-tenant (herdado da categoria)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='subcategorias', verbose_name='Categoria')
    codigo = models.CharField(max_length=20, verbose_name='Código')
    nome = models.CharField(max_length=100, verbose_name='Nome')
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'
        ordering = ['categoria', 'nome']
        unique_together = [['categoria', 'codigo']]
    
    def __str__(self):
        return f"{self.categoria.codigo}.{self.codigo} - {self.nome}"


class NaturezaOperacao(models.Model):
    \"\"\"
    Natureza da Operação - Descrições padronizadas para operações fiscais
    \"\"\"
    # Multi-tenant
    empresa = models.ForeignKey('empresas.Empresa', on_delete=models.CASCADE, related_name='naturezas_operacao', verbose_name='Empresa')
    
    codigo = models.CharField(max_length=20, verbose_name='Código')
    descricao = models.CharField(max_length=200, verbose_name='Descrição')
    tipo = models.CharField(max_length=10, choices=[
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
        ('AMBOS', 'Ambos'),
    ], default='AMBOS', verbose_name='Tipo')
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'Natureza da Operação'
        verbose_name_plural = 'Naturezas de Operação'
        ordering = ['codigo']
        unique_together = [['empresa', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.descricao}"
"""

# Continuar com o resto do arquivo...
# Salvar o arquivo
with open('produtos/models.py', 'w', encoding='utf-8') as f:
    f.write(models_content)

print("✅ Arquivo produtos/models.py recriado com sucesso!")
print("⚠️  ATENÇÃO: Arquivo incompleto - apenas primeiros modelos")
print("   Continue editando manualmente para adicionar modelo Produto e ProdutoTributacao")
