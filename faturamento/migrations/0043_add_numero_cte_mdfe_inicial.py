from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0042_add_xml_cancelamento_mdfe'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracaofiscal',
            name='numero_cte_inicial',
            field=models.PositiveIntegerField(
                default=1,
                verbose_name='Número Inicial do CT-e',
                help_text='Usado somente quando não há CT-e emitidos neste sistema. Para migrar de outro sistema, informe o próximo número.',
            ),
        ),
        migrations.AddField(
            model_name='configuracaofiscal',
            name='numero_mdfe_inicial',
            field=models.PositiveIntegerField(
                default=1,
                verbose_name='Número Inicial do MDF-e',
                help_text='Usado somente quando não há MDF-e emitidos neste sistema. Para migrar de outro sistema, informe o próximo número.',
            ),
        ),
    ]
