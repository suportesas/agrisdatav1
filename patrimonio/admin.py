from django.contrib import admin
from .models import (
    Patrimonio,
    PatrimonioDepreciacaoHistorico,
    PatrimonioMovimentacao,
    PatrimonioAuditoria,
    PatrimonioAuditoriaItem,
)


@admin.register(Patrimonio)
class PatrimonioAdmin(admin.ModelAdmin):
    list_display = ['numero_patrimonio', 'descricao', 'categoria', 'estado', 'valor_inicial', 'valor_atual', 'ativo']
    list_filter = ['categoria', 'estado', 'ativo', 'empresa']
    search_fields = ['numero_patrimonio', 'descricao']
    readonly_fields = ['data_cadastro', 'data_atualizacao']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('empresa', 'numero_patrimonio', 'descricao', 'categoria', 'veiculo')
        }),
        ('Valores', {
            'fields': ('valor_inicial', 'valor_atual', 'valor_residual')
        }),
        ('Depreciação', {
            'fields': ('tipo_depreciacao', 'vida_util_anos', 'percentual_depreciacao_anual')
        }),
        ('Datas', {
            'fields': ('data_aquisicao', 'data_baixa', 'data_cadastro', 'data_atualizacao')
        }),
        ('Localização', {
            'fields': ('localizacao', 'responsavel')
        }),
        ('Status', {
            'fields': ('estado', 'ativo', 'observacoes')
        }),
    )


@admin.register(PatrimonioDepreciacaoHistorico)
class PatrimonioDepreciacaoHistoricoAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'data', 'valor_anterior', 'valor_novo', 'depreciacao_aplicada']
    list_filter = ['data', 'patrimonio']
    readonly_fields = ['data', 'patrimonio']


@admin.register(PatrimonioMovimentacao)
class PatrimonioMovimentacaoAdmin(admin.ModelAdmin):
    list_display = ['patrimonio', 'tipo', 'data', 'responsavel_anterior', 'responsavel_novo']
    list_filter = ['tipo', 'data', 'patrimonio']
    readonly_fields = ['data']


@admin.register(PatrimonioAuditoria)
class PatrimonioAuditoriaAdmin(admin.ModelAdmin):
    list_display = ['ano', 'empresa', 'status', 'data_inicio', 'data_fechamento']
    list_filter = ['status', 'empresa', 'ano']
    search_fields = ['ano', 'empresa__razao_social']


@admin.register(PatrimonioAuditoriaItem)
class PatrimonioAuditoriaItemAdmin(admin.ModelAdmin):
    list_display = ['auditoria', 'numero_patrimonio', 'descricao', 'status', 'data_verificacao']
    list_filter = ['status', 'auditoria']
    search_fields = ['numero_patrimonio', 'descricao']
