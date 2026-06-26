from django.contrib import admin
from .models import AtoConcessorio, DrawbackProdutoAC, EntradaDrawback, SaidaDrawback


class DrawbackProdutoACInline(admin.TabularInline):
    model = DrawbackProdutoAC
    extra = 1
    fields = ('produto', 'ncm', 'descricao_mercadoria', 'unidade_medida',
              'quantidade_autorizada', 'quantidade_minima_export')


@admin.register(AtoConcessorio)
class AtoConcessorioAdmin(admin.ModelAdmin):
    list_display = ('numero_ac', 'empresa', 'tipo', 'data_inicio', 'data_vencimento',
                    'data_prorrogacao', 'status')
    list_filter = ('status', 'tipo', 'empresa')
    search_fields = ('numero_ac', 'despachante')
    inlines = [DrawbackProdutoACInline]
    readonly_fields = ('data_cadastro', 'data_atualizacao')


@admin.register(EntradaDrawback)
class EntradaDrawbackAdmin(admin.ModelAdmin):
    list_display = ('numero_nf', 'ato_concessorio', 'drawback_produto', 'tipo_compra',
                    'quantidade', 'data_recebimento', 'origem', 'retroativo', 'anulado')
    list_filter = ('tipo_compra', 'origem', 'retroativo', 'anulado', 'ato_concessorio')
    search_fields = ('numero_nf', 'fornecedor__nome_fantasia')
    readonly_fields = ('data_registro',)


@admin.register(SaidaDrawback)
class SaidaDrawbackAdmin(admin.ModelAdmin):
    list_display = ('numero_nfe', 'ato_concessorio', 'drawback_produto', 'quantidade',
                    'data_embarque', 'numero_re', 'numero_due', 'origem', 'retroativo', 'anulado')
    list_filter = ('origem', 'retroativo', 'anulado', 'ato_concessorio')
    search_fields = ('numero_nfe', 'numero_re', 'numero_due', 'cliente__nome_fantasia')
    readonly_fields = ('data_registro',)
