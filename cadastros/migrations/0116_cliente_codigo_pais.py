from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0115_poco_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='codigo_pais',
            field=models.CharField(
                blank=True,
                default='1058',
                help_text='Código IBGE para NF-e (ex: 1058=Brasil, 4235=EUA)',
                max_length=4,
                verbose_name='Cód. IBGE País',
            ),
        ),
    ]
