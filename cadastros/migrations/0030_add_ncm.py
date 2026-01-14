from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0029_vehicle_consumo_unidade_alter_vehicle_consumo_medio'),
    ]

    operations = [
        migrations.CreateModel(
            name='NCM',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='8 dígitos numéricos', max_length=8, unique=True, verbose_name='Código NCM')),
                ('nome', models.CharField(max_length=255, verbose_name='Descrição')),
                ('descricao', models.TextField(blank=True, verbose_name='Observações')),
                ('cest', models.CharField(blank=True, max_length=10, verbose_name='CEST')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Data de criação')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Última atualização')),
            ],
            options={
                'verbose_name': 'NCM',
                'verbose_name_plural': 'NCMs',
                'ordering': ['codigo'],
            },
        ),
        migrations.AddIndex(
            model_name='ncm',
            index=models.Index(fields=['codigo'], name='cadastros_ncm_codigo_idx'),
        ),
    ]
