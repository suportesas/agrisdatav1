from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0029_mdfe_codigos_municipio'),
    ]

    operations = [
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='tipo_carroceria',
            field=models.CharField(
                blank=True,
                choices=[
                    ('00', '00 - Não Aplicável'),
                    ('01', '01 - Aberta'),
                    ('02', '02 - Fechada/Baú'),
                    ('03', '03 - Graneleira'),
                    ('04', '04 - Porta Container'),
                    ('05', '05 - Sider'),
                ],
                max_length=2,
                verbose_name='Tipo de Carroceria',
            ),
        ),
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='tipo_rodado',
            field=models.CharField(
                blank=True,
                choices=[
                    ('01', '01 - Truck'),
                    ('02', '02 - Toco'),
                    ('03', '03 - Cavalo Mecânico'),
                    ('04', '04 - VAN'),
                    ('05', '05 - Quadro'),
                    ('06', '06 - Outros'),
                ],
                max_length=2,
                verbose_name='Tipo de Rodado',
            ),
        ),
    ]
