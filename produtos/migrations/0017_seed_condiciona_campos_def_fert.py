from django.db import migrations


def set_condiciona_campos_for_existing_categories(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(codigo__in=['DEF', 'FERT']).update(condiciona_campos=True)


def reverse_set_condiciona_campos_for_existing_categories(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(codigo__in=['DEF', 'FERT']).update(condiciona_campos=False)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0016_add_armazem_padrao_produto'),
    ]

    operations = [
        migrations.RunPython(
            set_condiciona_campos_for_existing_categories,
            reverse_set_condiciona_campos_for_existing_categories,
        ),
    ]
