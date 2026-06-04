from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('faturamento', '0011_notafiscal_entrega'),
    ]

    operations = [
        migrations.AddField(
            model_name='notafiscal',
            name='embarque_uf',
            field=models.CharField(
                blank=True, max_length=2,
                verbose_name='UF do Embarque',
                help_text='UF de saída do país (ex: CE, SP). Obrigatório para NF-e de exportação (CFOP 7xxx).',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='embarque_local',
            field=models.CharField(
                blank=True, max_length=60,
                verbose_name='Local do Embarque',
                help_text='Descrição do local de embarque/exportação (ex: Porto Mucuripe).',
            ),
        ),
        migrations.AddField(
            model_name='notafiscal',
            name='embarque_local_despacho',
            field=models.CharField(
                blank=True, max_length=60,
                verbose_name='Local do Despacho',
                help_text='Local de despacho aduaneiro, quando diferente do embarque.',
            ),
        ),
    ]
