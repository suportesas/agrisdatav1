from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0037_alter_fornecedor_celular'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fazenda',
            options={
                'verbose_name': 'Fazenda',
                'verbose_name_plural': 'Fazendas',
                'ordering': ['nome'],
                'permissions': [
                    ('view_other_fazendas_estoque', 'Pode visualizar estoque de outras fazendas'),
                ],
            },
        ),
    ]
