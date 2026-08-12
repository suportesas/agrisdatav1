from django.db import migrations


def seed_tipo_func_campo(apps, schema_editor):
    TipoUsuario = apps.get_model('usuarios', 'TipoUsuario')
    TipoUsuario.objects.update_or_create(
        codigo='FUNC_CAMPO',
        defaults={
            'nome': 'Funcionário de Campo',
            'descricao': 'Login unificado do Portal do Campo.',
            'ordem': 71,
            'protegido': True,
            'administrador_empresa': False,
            'permite_gerenciar_usuarios': False,
            'permite_acessar_financeiro': False,
            'permite_fazer_vendas': False,
        },
    )


def remove_tipo_func_campo(apps, schema_editor):
    TipoUsuario = apps.get_model('usuarios', 'TipoUsuario')
    TipoUsuario.objects.filter(codigo='FUNC_CAMPO').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0011_usuario_pagina_inicial'),
    ]

    operations = [
        migrations.RunPython(seed_tipo_func_campo, remove_tipo_func_campo),
    ]
