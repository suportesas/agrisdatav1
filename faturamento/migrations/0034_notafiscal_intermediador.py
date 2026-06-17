from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0033_add_cep_descarregamento_mdfe'),
    ]

    operations = [
        migrations.AddField(
            model_name='notafiscal',
            name='ind_intermediador',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', 'Não se aplica (presencial)'),
                    ('0', '0 – Operação sem intermediador (site/plataforma própria)'),
                    ('1', '1 – Operação em site ou plataforma de terceiros (marketplace)'),
                ],
                default='',
                help_text='Obrigatório quando indPres = 2, 3, 4 ou 9 (não presencial).',
                max_length=1,
                verbose_name='Indicador de Intermediador (indIntermed)',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='intermediador_cnpj',
            field=models.CharField(
                blank=True,
                help_text='CNPJ da plataforma intermediadora (somente dígitos). Obrigatório quando indIntermed = 1.',
                max_length=14,
                verbose_name='CNPJ do Intermediador',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='intermediador_id_cadastro',
            field=models.CharField(
                blank=True,
                help_text='Identificador do vendedor na plataforma intermediadora (ex: login, CPF, código). Obrigatório quando indIntermed = 1.',
                max_length=60,
                verbose_name='ID Cad. no Intermediador (idCadIntTran)',
            ),
        ),
    ]
