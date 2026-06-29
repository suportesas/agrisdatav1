from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0025_dimensaovariante_produtoatributo'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='produto_base',
            field=models.ForeignKey(
                blank=True,
                help_text='Se preenchido, este produto é uma variante do produto base selecionado.',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='variantes',
                to='produtos.produto',
                verbose_name='Produto Base',
            ),
        ),
    ]
