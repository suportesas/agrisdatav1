from django.contrib import admin
from .models import (
    AplicacaoEstufa,
    Estufa,
    LoteMuda,
    MonitoramentoEstufa,
    PerdaEstufa,
)


class LoteMudaInline(admin.TabularInline):
    model = LoteMuda
    extra = 0
    readonly_fields = ['codigo_lote', 'data_cadastro']


@admin.register(Estufa)
class EstufaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'fazenda', 'tipo', 'ativo']
    list_filter = ['tipo', 'ativo', 'empresa']
    search_fields = ['nome', 'codigo']
    readonly_fields = ['data_cadastro']
    inlines = [LoteMudaInline]


@admin.register(LoteMuda)
class LoteMudaAdmin(admin.ModelAdmin):
    list_display = ['codigo_lote', 'cultura', 'estufa', 'status', 'quantidade_semeada', 'data_semeadura']
    list_filter = ['status', 'empresa']
    search_fields = ['codigo_lote', 'cultura__nome']
    readonly_fields = ['data_cadastro']


