from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('operacoes_campo', '0005_os_intervalo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='osfuncionario',
            name='data_execucao',
            field=models.DateField(blank=True, null=True, verbose_name='Data de Execução'),
        ),
        migrations.AlterField(
            model_name='osfuncionario',
            name='hora_inicio',
            field=models.TimeField(blank=True, null=True, verbose_name='Hora de Início'),
        ),
        migrations.AlterField(
            model_name='osfuncionario',
            name='hora_fim',
            field=models.TimeField(blank=True, null=True, verbose_name='Hora de Término'),
        ),
    ]
