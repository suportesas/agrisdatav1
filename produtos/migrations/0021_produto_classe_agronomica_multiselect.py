from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0020_produto_arquivo_certificado_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produto',
            name='classe_agronomica',
            field=models.CharField(blank=True, max_length=200, verbose_name='Classe Agronômica'),
        ),
    ]
