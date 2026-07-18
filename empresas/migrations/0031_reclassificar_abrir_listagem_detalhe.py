"""
Reclassifica os Programas ativos que tinham tipo_acao='abrir' (valor antigo,
removido do choices em 0030) em 'listagem' ou 'detalhe', usando a mesma
heurística de sufixo de URL do `empresas/programa_discovery.py`.

Só altera o campo `tipo_acao` — não mexe em `Role.programas`, então nenhuma
concessão já feita é perdida (o Programa mantém o mesmo id).
"""

from django.db import migrations

_SUFIXOS_LISTAGEM = ('_list', '_dashboard')
_SUFIXOS_DETALHE = ('_detail', '_view')


def reclassificar(apps, schema_editor):
    Programa = apps.get_model('empresas', 'Programa')
    for programa in Programa.objects.filter(tipo_acao='abrir'):
        bare = programa.url_name.rsplit(':', 1)[-1]
        if bare.endswith(_SUFIXOS_LISTAGEM):
            programa.tipo_acao = 'listagem'
        elif bare.endswith(_SUFIXOS_DETALHE):
            programa.tipo_acao = 'detalhe'
        else:
            programa.tipo_acao = 'listagem'  # fallback conservador
        programa.save(update_fields=['tipo_acao'])


def reverter(apps, schema_editor):
    Programa = apps.get_model('empresas', 'Programa')
    Programa.objects.filter(tipo_acao__in=['listagem', 'detalhe']).update(tipo_acao='abrir')


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0030_alter_programa_tipo_acao'),
    ]

    operations = [
        migrations.RunPython(reclassificar, reverter),
    ]
