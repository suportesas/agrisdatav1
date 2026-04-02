from django.db import migrations


def create_def_fert_for_all_empresas(apps, schema_editor):
    Empresa = apps.get_model('empresas', 'Empresa')
    Categoria = apps.get_model('produtos', 'Categoria')

    defaults_by_code = {
        'DEF': {
            'nome': 'Defensivo Agrícola',
            'descricao': 'Produtos defensivos para uso agrícola.',
            'ativo': True,
            'condiciona_campos': True,
        },
        'FERT': {
            'nome': 'Fertilizante',
            'descricao': 'Fertilizantes e adubos.',
            'ativo': True,
            'condiciona_campos': True,
        },
    }

    for empresa in Empresa.objects.all().iterator():
        for codigo, defaults in defaults_by_code.items():
            Categoria.objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults=defaults,
            )


def noop_reverse(apps, schema_editor):
    # No-op reverse to avoid deleting categories that may have been edited by users.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0021_empresa_bairro'),
        ('produtos', '0018_set_condiciona_campos_by_nome'),
    ]

    operations = [
        migrations.RunPython(create_def_fert_for_all_empresas, noop_reverse),
    ]
