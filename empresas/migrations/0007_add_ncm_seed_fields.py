from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0006_alter_permissiontemplate_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='auto_seed_ncm',
            field=models.BooleanField(default=True, help_text='Se ativo, a lista de NCMs será copiada dos templates globais no cadastro da empresa', verbose_name='Popular NCMs automaticamente ao criar empresa'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='last_ncm_seeded_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Última vez que NCMs foram populados'),
        ),
    ]
