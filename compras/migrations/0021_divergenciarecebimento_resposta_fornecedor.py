from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0020_pedidocompramensagem_and_fornecedor_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='divergenciarecebimento',
            name='resposta_fornecedor',
            field=models.TextField(
                blank=True,
                verbose_name='Resposta do Fornecedor',
                help_text='Justificativa ou resposta do fornecedor sobre esta divergência',
            ),
        ),
        migrations.AddField(
            model_name='divergenciarecebimento',
            name='data_resposta_fornecedor',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Data da Resposta do Fornecedor',
            ),
        ),
    ]
