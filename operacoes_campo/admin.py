from django.contrib import admin
from .models import (
    CustoHoraMaquina, TipoServicoOS, SubtipoServicoOS, ModalidadeExecucaoOS,
    OrdemServico, OrdemServicoInsumo, OSFuncionario, OSMaquina, CustoTalhao,
    EtapaColheita, FrotaColheita, CarrocaoFrota, ViagemColheita,
    RegistroPluviometria, InspecaoQualidadeCampo,
    RegistroCadernoCampo, RegistroCadernoCampoInsumo, RegistroCadernoCampoFuncionario,
    PlanejamentoCustoSafra, PlanejamentoCustoItem,
)

admin.site.register(TipoServicoOS)
admin.site.register(SubtipoServicoOS)
admin.site.register(ModalidadeExecucaoOS)
admin.site.register(CustoHoraMaquina)
admin.site.register(OrdemServico)
admin.site.register(OrdemServicoInsumo)
admin.site.register(OSFuncionario)
admin.site.register(OSMaquina)
admin.site.register(CustoTalhao)
admin.site.register(EtapaColheita)
admin.site.register(FrotaColheita)
admin.site.register(CarrocaoFrota)
admin.site.register(ViagemColheita)
admin.site.register(RegistroPluviometria)
admin.site.register(InspecaoQualidadeCampo)
admin.site.register(RegistroCadernoCampo)
admin.site.register(RegistroCadernoCampoInsumo)
admin.site.register(RegistroCadernoCampoFuncionario)
admin.site.register(PlanejamentoCustoSafra)
admin.site.register(PlanejamentoCustoItem)
