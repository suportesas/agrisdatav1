from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0100_manutencao_motorista_solicitante'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='pin_portal',
            field=models.CharField(
                blank=True,
                help_text='PIN numérico hashado — definido pelo gestor',
                max_length=128,
                verbose_name='PIN (Portal do Campo)',
            ),
        ),
        migrations.AddField(
            model_name='funcionario',
            name='portal_ativo',
            field=models.BooleanField(default=False, verbose_name='Acesso ao Portal do Campo'),
        ),
    ]
