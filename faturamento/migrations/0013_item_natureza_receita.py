from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0012_notafiscal_embarque'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemnotafiscal',
            name='natureza_receita_pis',
            field=models.CharField(
                blank=True, max_length=3,
                verbose_name='Natureza da Receita PIS',
                help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99.',
            ),
        ),
        migrations.AddField(
            model_name='itemnotafiscal',
            name='natureza_receita_cofins',
            field=models.CharField(
                blank=True, max_length=3,
                verbose_name='Natureza da Receita COFINS',
                help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99.',
            ),
        ),
    ]
