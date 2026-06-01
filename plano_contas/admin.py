from django.contrib import admin
from .models import ContaContabil, CentroCusto


@admin.register(ContaContabil)
class ContaContabilAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'tipo', 'natureza', 'nivel', 'analitica', 'ativo', 'empresa')
    list_filter = ('tipo', 'natureza', 'analitica', 'ativo', 'empresa')
    search_fields = ('codigo', 'nome')
    list_select_related = ('empresa', 'conta_pai')
    ordering = ('empresa', 'codigo')
    readonly_fields = ('nivel', 'created_at', 'updated_at')
    fieldsets = (
        ('Identificação', {'fields': ('empresa', 'codigo', 'nome')}),
        ('Classificação', {'fields': ('tipo', 'natureza', 'analitica', 'gerencial')}),
        ('Hierarquia', {'fields': ('conta_pai', 'nivel')}),
        ('Descrição', {'fields': ('descricao', 'observacoes'), 'classes': ('collapse',)}),
        ('Controle', {'fields': ('ativo', 'created_at', 'updated_at')}),
    )


@admin.register(CentroCusto)
class CentroCustoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'nivel', 'ativo', 'empresa')
    list_filter = ('ativo', 'empresa')
    search_fields = ('codigo', 'nome')
    ordering = ('empresa', 'codigo')
    readonly_fields = ('nivel', 'created_at', 'updated_at')
    fieldsets = (
        ('Identificação', {'fields': ('empresa', 'codigo', 'nome', 'descricao')}),
        ('Hierarquia', {'fields': ('centro_pai', 'nivel')}),
        ('Controle', {'fields': ('ativo', 'created_at', 'updated_at')}),
    )
