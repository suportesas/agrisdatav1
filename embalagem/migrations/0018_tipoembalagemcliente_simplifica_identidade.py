import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0130_cultura_nome_multilingue'),
        ('embalagem', '0017_alter_tipoembalagemcliente_options_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='tipoembalagemcliente',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='tipoembalagemcliente',
            name='produto',
        ),
        migrations.RemoveField(
            model_name='tipoembalagemcliente',
            name='subcategoria',
        ),
        migrations.AlterField(
            model_name='tipoembalagemcliente',
            name='cultura',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ians_cliente', to='cadastros.cultura', verbose_name='Cultura'),
        ),
        migrations.AlterUniqueTogether(
            name='tipoembalagemcliente',
            unique_together={('cultura', 'variedade', 'marca', 'cliente')},
        ),
    ]
