"""
Admin do módulo Estoque
"""
from django.contrib import admin
from .models import Armazem, LocalEstocagem, Lote


class LocalEstocagemInline(admin.TabularInline):
    """Inline para locais de estocagem dentro do armazém"""
    model = LocalEstocagem
    extra = 0
    fields = ['codigo', 'tipo', 'descricao', 'capacidade_kg', 'bloqueado', 'ativo']
    readonly_fields = []


@admin.register(Armazem)
class ArmazemAdmin(admin.ModelAdmin):
    """Admin para Armazém"""
    list_display = [
        'codigo', 'nome', 'tipo', 'empresa', 'responsavel',
        'capacidade_kg', 'controla_temperatura', 'ativo'
    ]
    list_filter = ['tipo', 'ativo', 'controla_temperatura', 'empresa']
    search_fields = ['codigo', 'nome', 'localizacao']
    readonly_fields = ['data_cadastro', 'data_atualizacao']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'codigo', 'nome', 'tipo')
        }),
        ('Localização', {
            'fields': ('localizacao', 'fazenda', 'responsavel')
        }),
        ('Capacidade', {
            'fields': ('capacidade_m3', 'capacidade_kg')
        }),
        ('Controle de Temperatura', {
            'fields': ('controla_temperatura', 'temperatura_min', 'temperatura_max'),
            'classes': ('collapse',)
        }),
        ('Informações Adicionais', {
            'fields': ('observacoes', 'ativo')
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'data_atualizacao', 'cadastrado_por'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [LocalEstocagemInline]
    
    def save_model(self, request, obj, form, change):
        """Auto-set cadastrado_por no cadastro"""
        if not change:
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(LocalEstocagem)
class LocalEstocagemAdmin(admin.ModelAdmin):
    """Admin para Local de Estocagem"""
    list_display = [
        'armazem', 'codigo', 'tipo', 'descricao',
        'capacidade_kg', 'bloqueado', 'ativo'
    ]
    list_filter = ['tipo', 'bloqueado', 'ativo', 'armazem']
    search_fields = ['codigo', 'descricao']
    readonly_fields = ['data_cadastro', 'data_bloqueio']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('armazem', 'codigo', 'tipo', 'descricao')
        }),
        ('Capacidade', {
            'fields': ('capacidade_kg',)
        }),
        ('Bloqueio', {
            'fields': ('bloqueado', 'motivo_bloqueio', 'data_bloqueio', 'bloqueado_por'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('data_cadastro',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    """Admin para Lote"""
    list_display = [
        'numero_lote', 'produto', 'armazem', 'quantidade_atual',
        'unidade_medida', 'data_validade', 'status', 'empresa'
    ]
    list_filter = ['status', 'armazem', 'empresa', 'data_validade']
    search_fields = ['numero_lote', 'produto__nome', 'nota_fiscal']
    readonly_fields = ['data_cadastro', 'valor_total']
    date_hierarchy = 'data_validade'
    
    fieldsets = (
        ('Identificação', {
            'fields': ('empresa', 'numero_lote', 'produto')
        }),
        ('Localização', {
            'fields': ('armazem', 'local_estocagem')
        }),
        ('Datas', {
            'fields': ('data_fabricacao', 'data_validade', 'data_entrada')
        }),
        ('Quantidades', {
            'fields': ('quantidade_inicial', 'quantidade_atual', 'unidade_medida')
        }),
        ('Origem', {
            'fields': ('fornecedor', 'nota_fiscal')
        }),
        ('Valores', {
            'fields': ('valor_unitario', 'valor_total'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('status', 'motivo_bloqueio')
        }),
        ('Informações Adicionais', {
            'fields': ('observacoes',),
            'classes': ('collapse',)
        }),
        ('Auditoria', {
            'fields': ('data_cadastro', 'cadastrado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Auto-set cadastrado_por no cadastro"""
        if not change:
            obj.cadastrado_por = request.user
        super().save_model(request, obj, form, change)

