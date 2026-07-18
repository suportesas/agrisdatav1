from django.db import migrations


def criar_programa_solicitacao_emergencial(apps, schema_editor):
    Programa = apps.get_model('empresas', 'Programa')
    Programa.objects.get_or_create(
        url_name='compras:solicitacao_emergencial',
        defaults={
            'app_label': 'compras',
            'grupo_tela': 'solicitacao',
            'nome': 'Criar Solicitação Emergencial',
            'tipo_acao': 'outro',
            'ativo': True,
            'descoberta_automatica': False,
        }
    )


def remover_programa_solicitacao_emergencial(apps, schema_editor):
    Programa = apps.get_model('empresas', 'Programa')
    Programa.objects.filter(url_name='compras:solicitacao_emergencial').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0028_programa_descoberta_automatica'),
    ]

    operations = [
        migrations.RunPython(criar_programa_solicitacao_emergencial, remover_programa_solicitacao_emergencial),
    ]
