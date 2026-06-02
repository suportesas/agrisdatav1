"""
Remove os 4 models MIP do estado Django de cadastros.
Sem SQL — as tabelas permanecem com o mesmo nome (db_table = 'cadastros_*').
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0108_remove_frota_models'),
        ('mip', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='EstagioDesenvolvimento'),
                migrations.DeleteModel(name='MonitoramentoMIP'),
                migrations.DeleteModel(name='PragaNoMonitoramento'),
                migrations.DeleteModel(name='PontoMonitoramento'),
            ],
        ),
    ]
