from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0001_initial'),
        ('operacoes_campo', '0003_horimetros_nullable'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalCampoConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horario_trabalhadores', models.CharField(
                    choices=[
                        ('AUTO', 'Auto-preencher com horário do operador (editável)'),
                        ('OMITIR', 'Usar horário do operador automaticamente (sem perguntar)'),
                    ],
                    default='AUTO',
                    help_text='Define como o horário é preenchido ao adicionar outros trabalhadores na execução de uma OS.',
                    max_length=10,
                    verbose_name='Horário dos trabalhadores adicionais',
                )),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última atualização')),
                ('empresa', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='portal_campo_config',
                    to='empresas.empresa',
                    verbose_name='Empresa',
                )),
            ],
            options={
                'verbose_name': 'Configuração do Portal do Campo',
                'verbose_name_plural': 'Configurações do Portal do Campo',
                'db_table': 'campo_portal_config',
            },
        ),
    ]
