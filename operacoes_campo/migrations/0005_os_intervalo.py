from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('operacoes_campo', '0004_portalcampoconfig'),
        ('rh', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OSIntervalo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateTimeField(verbose_name='Início')),
                ('fim', models.DateTimeField(blank=True, null=True, verbose_name='Fim')),
                ('os', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='intervalos',
                    to='operacoes_campo.ordemservico',
                    verbose_name='Ordem de Serviço',
                )),
                ('funcionario', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='intervalos_os',
                    to='rh.funcionario',
                    verbose_name='Funcionário',
                )),
            ],
            options={
                'verbose_name': 'Intervalo de Trabalho',
                'verbose_name_plural': 'Intervalos de Trabalho',
                'db_table': 'campo_os_intervalo',
                'ordering': ['inicio'],
            },
        ),
    ]
