from django.contrib import admin
from .models import AdiantamentoInternacional, DescontoAdiantamento, MigracaoAdiantamento


@admin.register(AdiantamentoInternacional)
class AdiantamentoInternacionalAdmin(admin.ModelAdmin):
    list_display = ['numero_referencia', 'cliente', 'safra_referencia', 'moeda', 'valor_estrangeiro', 'status', 'empresa']
    list_filter = ['status', 'moeda', 'empresa']
    search_fields = ['numero_referencia', 'cliente__razao_social']
    raw_id_fields = ['cliente', 'empresa', 'safra', 'invoice_origem']


@admin.register(DescontoAdiantamento)
class DescontoAdiantamentoAdmin(admin.ModelAdmin):
    list_display = ['adiantamento', 'invoice', 'data_desconto', 'valor_desconto_estrangeiro', 'status']
    list_filter = ['status']
    raw_id_fields = ['adiantamento', 'invoice']


@admin.register(MigracaoAdiantamento)
class MigracaoAdiantamentoAdmin(admin.ModelAdmin):
    list_display = ['adiantamento_origem', 'adiantamento_destino', 'saldo_migrado_estrangeiro', 'data_migracao']
    raw_id_fields = ['adiantamento_origem', 'adiantamento_destino', 'migrado_por']
