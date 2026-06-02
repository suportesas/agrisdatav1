from django.contrib import admin
from .models import (
    EstagioDesenvolvimento, MonitoramentoMIP,
    PragaNoMonitoramento, PontoMonitoramento,
)


class PontoMonitoramentoInline(admin.TabularInline):
    model = PontoMonitoramento
    extra = 0


class PragaNoMonitoramentoInline(admin.TabularInline):
    model = PragaNoMonitoramento
    extra = 0


@admin.register(EstagioDesenvolvimento)
class EstagioDesenvolvimentoAdmin(admin.ModelAdmin):
    list_display = ['praga', 'tipo_estagio', 'descricao', 'ordem_ciclo', 'eh_fase_critica', 'ativo']
    list_filter = ['tipo_estagio', 'eh_fase_critica', 'ativo']
    search_fields = ['praga__nome_comum', 'descricao']


@admin.register(MonitoramentoMIP)
class MonitoramentoMIPAdmin(admin.ModelAdmin):
    list_display = ['numero', 'talhao', 'data_monitoramento', 'status', 'responsavel']
    list_filter = ['status', 'tipo_monitoramento']
    search_fields = ['numero', 'talhao__nome']
    inlines = [PragaNoMonitoramentoInline]


@admin.register(PragaNoMonitoramento)
class PragaNoMonitoramentoAdmin(admin.ModelAdmin):
    list_display = ['monitoramento', 'praga', 'incidencia_percentual', 'ned_atingido', 'resultado_acao']
    list_filter = ['resultado_acao', 'ned_atingido']
    inlines = [PontoMonitoramentoInline]


@admin.register(PontoMonitoramento)
class PontoMonitoramentoAdmin(admin.ModelAdmin):
    list_display = ['praga_monitoramento', 'numero_ponto', 'praga_presente', 'quantidade', 'severidade']
    list_filter = ['praga_presente']
