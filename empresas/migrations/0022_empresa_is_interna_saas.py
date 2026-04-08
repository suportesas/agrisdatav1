from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0021_empresa_bairro'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='is_interna_saas',
            field=models.BooleanField(
                default=False,
                help_text='Quando ativo, esta empresa e de uso interno do proprietario e nao entra em cobranca.',
                verbose_name='Empresa interna do SaaS',
            ),
        ),
    ]
