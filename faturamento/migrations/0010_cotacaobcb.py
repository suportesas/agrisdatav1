from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0009_invoice_desconto_adiantamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='CotacaoBCB',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(db_index=True, verbose_name='Data de Referência')),
                ('moeda', models.CharField(choices=[('USD', 'Dólar EUA (USD)'), ('EUR', 'Euro (EUR)'), ('GBP', 'Libra Esterlina (GBP)')], max_length=3, verbose_name='Moeda')),
                ('compra', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='Taxa Compra')),
                ('venda', models.DecimalField(decimal_places=4, max_digits=10, verbose_name='Taxa Venda')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Atualizado em')),
            ],
            options={
                'verbose_name': 'Cotação BCB',
                'verbose_name_plural': 'Cotações BCB',
                'ordering': ['-data', 'moeda'],
                'unique_together': {('data', 'moeda')},
            },
        ),
    ]
