"""
Remove os 5 models de empréstimo do estado Django de cadastros.
Sem SQL — as tabelas permanecem com o mesmo nome (db_table = 'cadastros_*').
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0109_remove_mip_models'),
        ('emprestimos', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='EmprestimoProdutor'),
                migrations.DeleteModel(name='EmprestimoMovimento'),
                migrations.DeleteModel(name='EmprestimoInteracao'),
                migrations.DeleteModel(name='EmprestimoMensagem'),
                migrations.DeleteModel(name='EmprestimoMensagemAnexo'),
            ],
        ),
    ]
