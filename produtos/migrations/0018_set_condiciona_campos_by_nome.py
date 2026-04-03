from django.db import migrations
from django.db.models import Q


def set_condiciona_campos_by_nome(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(
        Q(codigo__in=['DEF', 'FERT'])
        | Q(nome__icontains='defensivo')
        | Q(nome__icontains='fertilizante')
    ).update(condiciona_campos=True)


def reverse_set_condiciona_campos_by_nome(apps, schema_editor):
    Categoria = apps.get_model('produtos', 'Categoria')
    Categoria.objects.filter(
        Q(codigo__in=['DEF', 'FERT'])
        | Q(nome__icontains='defensivo')
        | Q(nome__icontains='fertilizante')
    ).update(condiciona_campos=False)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0017_seed_condiciona_campos_def_fert'),
    ]

    operations = [
        migrations.RunPython(
            set_condiciona_campos_by_nome,
            reverse_set_condiciona_campos_by_nome,
        ),
    ]
