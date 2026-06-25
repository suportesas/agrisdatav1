from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0041_add_tipo_emitente_mdfe'),
    ]

    operations = [
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='xml_cancelamento',
            field=models.TextField(blank=True, verbose_name='XML Cancelamento (base64)'),
        ),
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='xml_cancelamento_url',
            field=models.URLField(blank=True, verbose_name='URL XML Cancelamento (Storage)'),
        ),
    ]
