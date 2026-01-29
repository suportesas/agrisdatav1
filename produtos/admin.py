from django.contrib import admin
from .models import UnidadeMedida, Categoria, SubCategoria, Produto, ProdutoTributacao, NaturezaOperacao, ProdutoDocumento, ProdutoFornecedor


@admin.register(UnidadeMedida)
class UnidadeMedidaAdmin(admin.ModelAdmin):
    list_display = ['sigla', 'nome', 'tipo', 'ativo']
    list_filter = ['tipo', 'ativo']
    search_fields = ['sigla', 'nome']
    ordering = ['nome']


@admin.register(NaturezaOperacao)
class NaturezaOperacaoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'tipo', 'ativo']
    list_filter = ['tipo', 'ativo']
    search_fields = ['codigo', 'descricao']
    ordering = ['codigo']


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'ativo']
    list_filter = ['ativo']
    search_fields = ['codigo', 'nome']
    ordering = ['nome']


@admin.register(SubCategoria)
class SubCategoriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'categoria', 'ativo']
    list_filter = ['categoria', 'ativo']
    search_fields = ['codigo', 'nome']
    ordering = ['categoria', 'nome']


class ProdutoTributacaoInline(admin.TabularInline):
    model = ProdutoTributacao
    extra = 1
    fields = ['cfop', 'descricao', 'icms_situacao_tributaria', 'icms_aliquota', 'padrao', 'ativo']


class ProdutoFornecedorInline(admin.TabularInline):
    model = ProdutoFornecedor
    extra = 1
    fields = ['fornecedor', 'codigo_fornecedor', 'preco_compra', 'prazo_entrega', 'quantidade_minima', 'fornecedor_preferencial', 'ativo']
    autocomplete_fields = ['fornecedor']


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'categoria', 'preco_venda', 'estoque_atual', 'ativo']
    list_filter = ['categoria', 'tipo_produto', 'categoria_agricola', 'ativo']
    search_fields = ['codigo', 'nome', 'codigo_barras']
    ordering = ['nome']
    inlines = [ProdutoTributacaoInline, ProdutoFornecedorInline]
    
    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'codigo_barras', 'nome', 'nome_resumido', 'descricao', 'imagem')
        }),
        ('Classificação', {
            'fields': ('categoria', 'subcategoria', 'tipo_produto')
        }),
        ('Unidades', {
            'fields': ('unidade_medida', 'unidade_compra', 'unidade_venda', 'fator_conversao')
        }),
        ('Fiscal', {
            'fields': ('ncm', 'cest', 'origem_mercadoria', 'tipo_item')
        }),
        ('Financeiro', {
            'fields': ('preco_custo', 'preco_venda', 'margem_lucro', 'preco_minimo')
        }),
        ('Estoque', {
            'fields': ('controla_estoque', 'estoque_minimo', 'estoque_maximo', 'estoque_atual', 'localizacao')
        }),
        ('Rastreabilidade', {
            'fields': ('lote_obrigatorio', 'validade_obrigatoria', 'dias_validade')
        }),
        ('Categoria Agrícola', {
            'fields': ('categoria_agricola',),
            'classes': ('collapse',)
        }),
        ('Defensivos Agrícolas', {
            'fields': ('classe_agronomica', 'ingrediente_ativo', 'concentracao', 'registro_mapa',
                      'classe_toxicologica', 'classe_ambiental', 'periodo_carencia', 'intervalo_reaplicacao'),
            'classes': ('collapse',)
        }),
        ('Fertilizantes', {
            'fields': ('tipo_fertilizante', 'formula_npk', 'nitrogenio_n', 'fosforo_p2o5', 'potassio_k2o',
                      'enxofre_s', 'calcio_ca', 'magnesio_mg', 'micronutrientes'),
            'classes': ('collapse',)
        }),
        ('Dosagem e Aplicação', {
            'fields': ('dosagem_minima', 'dosagem_maxima', 'unidade_dosagem', 'modo_aplicacao'),
            'classes': ('collapse',)
        }),
        ('Segurança', {
            'fields': ('culturas_registradas', 'intervalo_seguranca', 'epi_obrigatorio', 'incompatibilidades'),
            'classes': ('collapse',)
        }),
        ('Armazenamento', {
            'fields': ('temperatura_armazenamento', 'inflamavel', 'corrosivo', 'toxico'),
            'classes': ('collapse',)
        }),
        ('Outros', {
            'fields': ('fornecedor_padrao', 'observacoes', 'ativo')
        }),
    )


@admin.register(ProdutoTributacao)
class ProdutoTributacaoAdmin(admin.ModelAdmin):
    list_display = ['produto', 'cfop', 'descricao', 'icms_aliquota', 'padrao', 'ativo']
    list_filter = ['padrao', 'ativo']
    search_fields = ['produto__codigo', 'produto__nome', 'cfop__codigo']
    ordering = ['produto', 'cfop']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('produto', 'cfop', 'descricao', 'padrao', 'ativo')
        }),
        ('Tributação ICMS', {
            'fields': ('icms_situacao_tributaria', 'icms_modalidade_base', 'icms_aliquota',
                      'icms_reducao_base', 'icms_base_calculo')
        }),
        ('ICMS ST', {
            'fields': ('icms_st_aliquota', 'icms_st_mva', 'icms_st_reducao_base'),
            'classes': ('collapse',)
        }),
        ('Tributação IPI', {
            'fields': ('ipi_situacao_tributaria', 'ipi_aliquota', 'ipi_codigo_enquadramento'),
            'classes': ('collapse',)
        }),
        ('Tributação PIS', {
            'fields': ('pis_situacao_tributaria', 'pis_aliquota', 'pis_base_calculo'),
            'classes': ('collapse',)
        }),
        ('Tributação COFINS', {
            'fields': ('cofins_situacao_tributaria', 'cofins_aliquota', 'cofins_base_calculo'),
            'classes': ('collapse',)
        }),
        ('Outros', {
            'fields': ('beneficio_fiscal', 'observacoes')
        }),
    )


@admin.register(ProdutoDocumento)
class ProdutoDocumentoAdmin(admin.ModelAdmin):
    list_display = ['produto', 'tipo', 'nome', 'arquivo', 'cadastrado_por', 'created_at']
    list_filter = ['tipo', 'created_at']
    search_fields = ['nome', 'produto__nome', 'produto__codigo']
    readonly_fields = ['created_at', 'updated_at', 'cadastrado_por']
    ordering = ['-created_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se é um novo registro
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)
