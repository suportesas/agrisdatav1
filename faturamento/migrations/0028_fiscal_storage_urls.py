from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0027_mdfe_prodpred_blank'),
    ]

    operations = [
        # NF-e
        migrations.AddField(
            model_name='notafiscal',
            name='xml_autorizacao_url',
            field=models.URLField(blank=True, verbose_name='URL XML Autorizado (Storage)'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='pdf_danfe_url',
            field=models.URLField(blank=True, verbose_name='URL DANFE PDF (Storage)'),
        ),
        # CT-e
        migrations.AddField(
            model_name='conhecimentotransporte',
            name='xml_autorizacao_url',
            field=models.URLField(blank=True, verbose_name='URL XML Autorizado (Storage)'),
        ),
        migrations.AddField(
            model_name='conhecimentotransporte',
            name='xml_cancelamento_url',
            field=models.URLField(blank=True, verbose_name='URL XML Cancelamento (Storage)'),
        ),
        migrations.AddField(
            model_name='conhecimentotransporte',
            name='pdf_dacte_url',
            field=models.URLField(blank=True, verbose_name='URL DACTE PDF (Storage)'),
        ),
        # MDF-e
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='xml_autorizacao_url',
            field=models.URLField(blank=True, verbose_name='URL XML Autorizado (Storage)'),
        ),
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='pdf_damdfe_url',
            field=models.URLField(blank=True, verbose_name='URL DAMDFE PDF (Storage)'),
        ),
    ]
