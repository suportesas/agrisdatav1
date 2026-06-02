"""
Registra a remoção dos modelos de Operações de Campo do estado Django do app cadastros.
Sem SQL — as tabelas permanecem (agora gerenciadas pelo app operacoes_campo).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0112_remove_rh_models'),
        ('operacoes_campo', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='TipoServicoOS'),
                migrations.DeleteModel(name='SubtipoServicoOS'),
                migrations.DeleteModel(name='ModalidadeExecucaoOS'),
                migrations.DeleteModel(name='CustoHoraMaquina'),
                migrations.DeleteModel(name='OrdemServico'),
                migrations.DeleteModel(name='OrdemServicoInsumo'),
                migrations.DeleteModel(name='OSFuncionario'),
                migrations.DeleteModel(name='OSMaquina'),
                migrations.DeleteModel(name='CustoTalhao'),
                migrations.DeleteModel(name='EtapaColheita'),
                migrations.DeleteModel(name='FrotaColheita'),
                migrations.DeleteModel(name='CarrocaoFrota'),
                migrations.DeleteModel(name='ViagemColheita'),
                migrations.DeleteModel(name='RegistroPluviometria'),
                migrations.DeleteModel(name='InspecaoQualidadeCampo'),
                migrations.DeleteModel(name='RegistroCadernoCampo'),
                migrations.DeleteModel(name='RegistroCadernoCampoInsumo'),
                migrations.DeleteModel(name='RegistroCadernoCampoFuncionario'),
                migrations.DeleteModel(name='PlanejamentoCustoSafra'),
                migrations.DeleteModel(name='PlanejamentoCustoItem'),
            ],
        ),
    ]
