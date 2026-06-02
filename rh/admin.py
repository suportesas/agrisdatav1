from django.contrib import admin
from .models import (
    FuncaoFuncionario, Funcionario, DocumentoFuncionario,
    FeriasFuncionario, AfastamentoFuncionario, RescisaoContrato,
    VinculoContrato, LaudoRisco, TipoExameASO, SolicitacaoASO,
    CategoriaRiscoAmbiental, RiscoAmbientalFuncao, RiscoAmbientalCatalogo,
    HistoricoFuncionario, LogEnvioSolicitacaoASO,
)

admin.site.register(FuncaoFuncionario)
admin.site.register(Funcionario)
admin.site.register(DocumentoFuncionario)
admin.site.register(FeriasFuncionario)
admin.site.register(AfastamentoFuncionario)
admin.site.register(RescisaoContrato)
admin.site.register(VinculoContrato)
admin.site.register(LaudoRisco)
admin.site.register(TipoExameASO)
admin.site.register(SolicitacaoASO)
admin.site.register(CategoriaRiscoAmbiental)
admin.site.register(RiscoAmbientalFuncao)
admin.site.register(RiscoAmbientalCatalogo)
admin.site.register(HistoricoFuncionario)
admin.site.register(LogEnvioSolicitacaoASO)
