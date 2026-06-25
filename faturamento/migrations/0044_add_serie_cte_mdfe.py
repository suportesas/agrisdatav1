from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0043_add_numero_cte_mdfe_inicial'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaofiscal',
            name='serie_cte',
            field=models.IntegerField(default=1, verbose_name='Série CT-e'),
        ),
        migrations.AddField(
            model_name='configuracaofiscal',
            name='serie_mdfe',
            field=models.IntegerField(default=1, verbose_name='Série MDF-e'),
        ),
    ]
