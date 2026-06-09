from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0028_fiscal_storage_urls'),
    ]

    operations = [
        migrations.AddField(
            model_name='manifestodocumentofiscal',
            name='codigo_municipio_carregamento',
            field=models.CharField(blank=True, help_text='7 dígitos IBGE', max_length=7, verbose_name='Código IBGE Município de Carregamento'),
        ),
        migrations.AddField(
            model_name='documentovinculadomdfe',
            name='codigo_municipio_descarregamento',
            field=models.CharField(blank=True, help_text='7 dígitos IBGE', max_length=7, verbose_name='Código IBGE'),
        ),
    ]
