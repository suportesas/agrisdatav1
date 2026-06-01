from django.contrib import admin
from .models import ContaBancaria, ImportacaoExtrato, ExtratoLancamento, ConciliacaoLancamento


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ('banco', 'agencia', 'conta', 'tipo_conta', 'ativa', 'conta_principal', 'empresa')
    list_filter = ('ativa', 'tipo_conta', 'empresa', 'conta_principal')
    search_fields = ('banco', 'codigo_banco', 'agencia', 'conta')
    list_select_related = ('empresa',)
    ordering = ('empresa', '-conta_principal', 'banco')


@admin.register(ImportacaoExtrato)
class ImportacaoExtratoAdmin(admin.ModelAdmin):
    list_display = ('conta_bancaria', 'tipo_arquivo', 'status', 'total_lancamentos',
                    'total_debitos', 'total_creditos', 'importado_em')
    list_filter = ('status', 'tipo_arquivo', 'empresa')
    readonly_fields = ('importado_em', 'total_lancamentos', 'total_debitos', 'total_creditos')
    list_select_related = ('conta_bancaria', 'empresa')


@admin.register(ExtratoLancamento)
class ExtratoLancamentoAdmin(admin.ModelAdmin):
    list_display = ('data_lancamento', 'tipo', 'valor', 'descricao',
                    'status_conciliacao', 'conta_bancaria', 'numero_documento')
    list_filter = ('tipo', 'status_conciliacao', 'conta_bancaria__empresa')
    search_fields = ('descricao', 'numero_documento', 'fit_id')
    date_hierarchy = 'data_lancamento'
    list_select_related = ('conta_bancaria', 'importacao')


@admin.register(ConciliacaoLancamento)
class ConciliacaoLancamentoAdmin(admin.ModelAdmin):
    list_display = ('lancamento_extrato', 'tipo_operacao', 'score_matching',
                    'conciliado_manualmente', 'conciliado_em')
    list_filter = ('tipo_operacao', 'conciliado_manualmente')
    readonly_fields = ('conciliado_em',)
    list_select_related = ('lancamento_extrato', 'conciliado_por')
