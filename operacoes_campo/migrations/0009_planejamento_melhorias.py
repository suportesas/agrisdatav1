from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('operacoes_campo', '0008_melhorias_os'),
    ]

    operations = [
        # Fase de cultivo nos itens de planejamento
        migrations.AddField(
            model_name='planejamentocustoitem',
            name='fase',
            field=models.CharField(
                'Fase de Cultivo',
                max_length=20,
                choices=[
                    ('GERAL', 'Geral'),
                    ('PREPARO_SOLO', 'Preparo de Solo'),
                    ('PLANTIO', 'Plantio / Semeadura'),
                    ('TRATOS_CULTURAIS', 'Tratos Culturais'),
                    ('COLHEITA', 'Colheita'),
                    ('POS_COLHEITA', 'Pós-Colheita'),
                ],
                default='GERAL',
            ),
        ),

        # Receita esperada no cabeçalho do planejamento
        migrations.AddField(
            model_name='planejamentocustosafra',
            name='produtividade_esperada_ha',
            field=models.DecimalField(
                'Produtividade Esperada (kg/ha ou sc/ha)',
                max_digits=12, decimal_places=4,
                null=True, blank=True,
                help_text='Produtividade esperada por hectare (ex: 60 sc/ha para soja).',
            ),
        ),
        migrations.AddField(
            model_name='planejamentocustosafra',
            name='preco_venda_unitario',
            field=models.DecimalField(
                'Preço de Venda Unitário (R$/unidade)',
                max_digits=12, decimal_places=4,
                null=True, blank=True,
                help_text='Preço esperado por unidade produzida (ex: R$ 120,00/sc).',
            ),
        ),
        migrations.AddField(
            model_name='planejamentocustosafra',
            name='unidade_producao',
            field=models.CharField(
                'Unidade de Produção',
                max_length=20,
                default='sc',
                blank=True,
                help_text='Ex: sc, kg, t, cx, dz.',
            ),
        ),
    ]
