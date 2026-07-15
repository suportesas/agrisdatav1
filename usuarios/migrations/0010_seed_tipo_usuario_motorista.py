from django.db import migrations


def seed_tipo_motorista(apps, schema_editor):
    TipoUsuario = apps.get_model('usuarios', 'TipoUsuario')
    TipoUsuario.objects.update_or_create(
        codigo='MOTORISTA',
        defaults={
            'nome': 'Motorista',
            'descricao': 'Login unificado do Portal do Motorista.',
            'ordem': 70,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': False,
            'permite_fazer_vendas': False,
        },
    )


def remove_tipo_motorista(apps, schema_editor):
    TipoUsuario = apps.get_model('usuarios', 'TipoUsuario')
    TipoUsuario.objects.filter(codigo='MOTORISTA').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_must_change_password'),
    ]

    operations = [
        migrations.RunPython(seed_tipo_motorista, remove_tipo_motorista),
    ]
