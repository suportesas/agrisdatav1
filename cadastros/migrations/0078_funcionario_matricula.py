from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0077_alter_empresancm_nome'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='matricula',
            field=models.CharField(
                blank=True,
                help_text='Código interno de matrícula do funcionário',
                max_length=30,
                null=True,
                verbose_name='Código da Matrícula',
            ),
        ),
        migrations.AddIndex(
            model_name='funcionario',
            index=models.Index(fields=['empresa', 'matricula'], name='cadastros_f_empresa_7c2f98_idx'),
        ),
    ]
