from django.db import migrations


def fix_sem_condiciona_campos(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(codigo='SEM').update(condiciona_campos=False)


def reverse_fix_sem_condiciona_campos(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(codigo='SEM').update(condiciona_campos=True)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0021_produto_classe_agronomica_multiselect'),
    ]

    operations = [
        migrations.RunPython(
            fix_sem_condiciona_campos,
            reverse_fix_sem_condiciona_campos,
        ),
    ]
