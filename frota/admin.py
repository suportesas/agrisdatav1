from django.contrib import admin

from .models import (
    Vehicle, VehiclePlate, VehicleValueHistory, VehicleDocument,
    Motorista, MotoristadoDocumento, MotoristaVinculoPlaca,
    AbastecimentoVeiculo, ManutencaoVeiculo, ManutencaoItem,
    DocumentoManutencao, AlertaManutencao, PedagioVeiculo,
    TelemetriaVeiculo, FotoAbastecimento,
)


class VehiclePlateInline(admin.TabularInline):
    model = VehiclePlate
    extra = 0
    fields = ['placa', 'vigencia_inicio', 'vigencia_fim', 'atual']


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 0
    fields = ['tipo', 'numero', 'data_emissao', 'data_validade', 'arquivo']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'empresa', 'transportadora', 'tipo', 'ativo', 'consumo_medio', 'consumo_unidade', 'tank_capacity', 'data_cadastro']
    list_filter = ['tipo', 'ativo', 'empresa']
    search_fields = ['marca', 'modelo', 'plates__placa']
    inlines = [VehiclePlateInline, VehicleDocumentInline]
    readonly_fields = ['data_cadastro', 'data_atualizacao']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if hasattr(request.user, 'empresa') and request.user.empresa:
            return qs.filter(empresa=request.user.empresa)
        return qs.none()


@admin.register(VehiclePlate)
class VehiclePlateAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'placa', 'vigencia_inicio', 'vigencia_fim', 'atual']
    search_fields = ['placa', 'vehicle__marca', 'vehicle__modelo']


@admin.register(VehicleValueHistory)
class VehicleValueHistoryAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'tipo', 'percentual', 'previous_value', 'new_value', 'aplicado_por', 'data_aplicacao']
    list_filter = ['tipo']
    search_fields = ['vehicle__marca', 'vehicle__modelo']
    readonly_fields = ['previous_value', 'new_value', 'percentual', 'tipo', 'aplicado_por', 'data_aplicacao']
    ordering = ['-data_aplicacao']


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'empresa', 'tipo', 'ativo', 'data_validade_cnh']
    list_filter = ['empresa', 'tipo', 'ativo']
    search_fields = ['nome', 'cpf', 'cnh']


@admin.register(MotoristaVinculoPlaca)
class MotoristaVinculoPlacaAdmin(admin.ModelAdmin):
    list_display = ['motorista', 'placa_principal', 'data_inicio', 'data_fim', 'ativo', 'empresa']
    list_filter = ['empresa', 'ativo', 'data_inicio']
    search_fields = ['motorista__nome', 'placa_principal__placa']


@admin.register(AbastecimentoVeiculo)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'data', 'tipo_combustivel', 'litros', 'valor_total', 'empresa']
    list_filter = ['empresa', 'tipo_combustivel', 'data']
    search_fields = ['vehicle__marca', 'vehicle__modelo']


@admin.register(ManutencaoVeiculo)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'tipo', 'status', 'descricao', 'data_abertura', 'empresa']
    list_filter = ['empresa', 'tipo', 'status']
    search_fields = ['vehicle__marca', 'descricao']
