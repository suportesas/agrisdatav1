import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('embalagem', '0004_add_itempallet_pallet_misto'),
        ('faturamento', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='romaneiovenda',
            name='invoice_exportacao',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='romaneio_origem',
                to='faturamento.invoiceexportacao',
                verbose_name='Invoice de Exportação',
            ),
        ),
        migrations.AddField(
            model_name='romaneiovenda',
            name='nota_fiscal',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='romaneio_origem',
                to='faturamento.notafiscal',
                verbose_name='Nota Fiscal',
            ),
        ),
    ]
