from django.db import migrations, models
import decimal


class Migration(migrations.Migration):

    dependencies = [
        ('operacoes_campo', '0007_osmaquina_data_execucao_nullable'),
    ]

    operations = [
        # Fator de encargos trabalhistas no PortalCampoConfig
        migrations.AddField(
            model_name='portalcampoconfig',
            name='fator_encargos',
            field=models.DecimalField(
                'Fator de Encargos Trabalhistas',
                max_digits=5,
                decimal_places=4,
                default=decimal.Decimal('1.0000'),
                help_text=(
                    'Multiplica o custo/hora da mão de obra para incluir encargos. '
                    'Ex: 1.70 para CLT com INSS+FGTS+férias+13º (~70% sobre salário). '
                    'Use 1.0 para considerar apenas o salário base.'
                ),
            ),
        ),

        # Custo estimado por OS (planejado vs. realizado)
        migrations.AddField(
            model_name='ordemservico',
            name='custo_estimado_mao_obra',
            field=models.DecimalField(
                'Custo Estimado Mão de Obra (R$)',
                max_digits=12, decimal_places=2,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name='ordemservico',
            name='custo_estimado_maquinario',
            field=models.DecimalField(
                'Custo Estimado Maquinário (R$)',
                max_digits=12, decimal_places=2,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name='ordemservico',
            name='custo_estimado_insumos',
            field=models.DecimalField(
                'Custo Estimado Insumos (R$)',
                max_digits=12, decimal_places=2,
                null=True, blank=True,
            ),
        ),

        # GPS no check-in do portal
        migrations.AddField(
            model_name='osintervalo',
            name='latitude',
            field=models.DecimalField(
                'Latitude', max_digits=10, decimal_places=7,
                null=True, blank=True,
            ),
        ),
        migrations.AddField(
            model_name='osintervalo',
            name='longitude',
            field=models.DecimalField(
                'Longitude', max_digits=10, decimal_places=7,
                null=True, blank=True,
            ),
        ),
    ]
