from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0022_fix_sem_condiciona_campos'),
    ]

    operations = [
        migrations.AddField(
            model_name='produtotributacao',
            name='natureza_receita_pis',
            field=models.CharField(
                blank=True, max_length=3,
                verbose_name='Natureza da Receita PIS',
                help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99 (ex: 116).',
            ),
        ),
        migrations.AddField(
            model_name='produtotributacao',
            name='natureza_receita_cofins',
            field=models.CharField(
                blank=True, max_length=3,
                verbose_name='Natureza da Receita COFINS',
                help_text='Código 3 dígitos — obrigatório para CST 04-09, 49, 99 (ex: 116).',
            ),
        ),
    ]
