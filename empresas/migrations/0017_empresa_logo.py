# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0007_add_ncm_seed_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='empresa',
            name='logo',
            field=models.ImageField(blank=True, help_text='Logo para documentos (PDF, relatórios, etc.)', null=True, upload_to='empresas/logos/', verbose_name='Logo da Empresa'),
        ),
    ]
