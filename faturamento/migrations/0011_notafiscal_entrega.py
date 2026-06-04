from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0010_cotacaobcb'),
    ]

    operations = [
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_ativo',
            field=models.BooleanField(
                default=False,
                help_text='Marque quando a mercadoria for entregue em endereço diferente do destinatário (ex: porto, obra, filial).',
                verbose_name='Usar endereço de entrega diferente',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_cnpj_cpf',
            field=models.CharField(
                blank=True, max_length=14,
                help_text='Somente dígitos. CNPJ (14) ou CPF (11) do local de entrega.',
                verbose_name='CNPJ/CPF do Local de Entrega',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_logradouro',
            field=models.CharField(blank=True, max_length=60, verbose_name='Logradouro'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_numero',
            field=models.CharField(blank=True, max_length=10, verbose_name='Número'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_complemento',
            field=models.CharField(blank=True, max_length=60, verbose_name='Complemento'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_bairro',
            field=models.CharField(blank=True, max_length=60, verbose_name='Bairro'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_codigo_municipio',
            field=models.CharField(
                blank=True, max_length=7,
                help_text='7 dígitos — código IBGE do município de entrega.',
                verbose_name='Código IBGE do Município',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_nome_municipio',
            field=models.CharField(blank=True, max_length=60, verbose_name='Município'),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='entrega_uf',
            field=models.CharField(blank=True, max_length=2, verbose_name='UF'),
        ),
    ]
