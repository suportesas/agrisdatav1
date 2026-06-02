from django.contrib import admin
from .models import (
    AplicacaoEstufa,
    Estufa,
    LoteMuda,
    MonitoramentoEstufa,
    PerdaEstufa,
    ReplantioTalhao,
    Transplantio,
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


@admin.register(Transplantio)
class TransplantioAdmin(admin.ModelAdmin):
    list_display = ['lote_muda', 'talhao', 'data_transplantio', 'quantidade_transplantada', 'tipo']
    list_filter = ['tipo', 'empresa']
    readonly_fields = ['data_cadastro', 'custo_transferido']


@admin.register(ReplantioTalhao)
class ReplantioTalhaoAdmin(admin.ModelAdmin):
    list_display = ['talhao', 'data_replantio', 'quantidade', 'origem_muda', 'motivo_perda']
    list_filter = ['origem_muda', 'motivo_perda', 'empresa']
    readonly_fields = ['data_cadastro']
