import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('embalagem', '0011_material_embalagem_rastreabilidade'),
        ('produtos', '0032_produtodefensivocultura_custo_relativo_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='materialembalagem',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='materialembalagem',
            name='fornecedor',
        ),
        migrations.RemoveField(
            model_name='materialembalagem',
            name='nome',
        ),
        migrations.AddField(
            model_name='materialembalagem',
            name='produto',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='materiais_embalagem',
                to='produtos.produto',
                verbose_name='Produto',
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='materialembalagem',
            options={
                'ordering': ['tipo', 'produto__nome'],
                'verbose_name': 'Material de Embalagem',
                'verbose_name_plural': 'Materiais de Embalagem',
            },
        ),
        migrations.AlterModelOptions(
            name='romaneiomaterialembalagem',
            options={
                'ordering': ['material__tipo', 'material__produto__nome'],
                'verbose_name': 'Material de Embalagem do Romaneio',
                'verbose_name_plural': 'Materiais de Embalagem do Romaneio',
            },
        ),
        migrations.AlterUniqueTogether(
            name='materialembalagem',
            unique_together={('empresa', 'produto')},
        ),
    ]
