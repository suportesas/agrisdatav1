"""
Remove os 7 models de estufa do estado Django de cadastros.
Sem SQL — as tabelas permanecem com o mesmo nome (db_table = 'cadastros_*').
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0110_remove_emprestimo_models'),
        ('estufas', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Estufa'),
                migrations.DeleteModel(name='LoteMuda'),
                migrations.DeleteModel(name='PerdaEstufa'),
                migrations.DeleteModel(name='AplicacaoEstufa'),
                migrations.DeleteModel(name='MonitoramentoEstufa'),
                migrations.DeleteModel(name='Transplantio'),
                migrations.DeleteModel(name='ReplantioTalhao'),
            ],
        ),
    ]
