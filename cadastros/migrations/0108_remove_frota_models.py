"""
Remove os models de frota do app cadastros.

Usa SeparateDatabaseAndState para NÃO dropar as tabelas — elas continuam
existindo, agora gerenciadas pelo app frota (db_table = 'cadastros_XXX').

Também atualiza (no estado apenas) os FKs dos modelos que ficam em cadastros
mas referenciam Vehicle/Motorista — agora apontam para frota.Vehicle/frota.Motorista.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0107_integranotas_nfe_fields'),
        ('frota', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                # 1. Atualizar FKs de modelos que ficam em cadastros (estado apenas)
                migrations.AlterField(
                    model_name='requisicao',
                    name='veiculo',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='requisicoes_abastecimento',
                        to='frota.vehicle',
                        verbose_name='Veiculo'
                    ),
                ),
                migrations.AlterField(
                    model_name='custohoramaquina',
                    name='veiculo',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='configuracoes_custo',
                        to='frota.vehicle',
                        verbose_name='Veículo/Máquina'
                    ),
                ),
                migrations.AlterField(
                    model_name='osmaquina',
                    name='veiculo',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='usos_os',
                        to='frota.vehicle',
                        verbose_name='Veículo/Máquina'
                    ),
                ),
                migrations.AlterField(
                    model_name='frotacolheita',
                    name='trator',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='frotas_colheita',
                        to='frota.vehicle',
                        verbose_name='Trator',
                    ),
                ),
                migrations.AlterField(
                    model_name='carrocaofrota',
                    name='veiculo',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='usos_colheita',
                        to='frota.vehicle',
                        verbose_name='Carroção',
                    ),
                ),
                migrations.AlterField(
                    model_name='viagem',
                    name='vehicle',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='viagens',
                        to='frota.vehicle',
                        verbose_name='Veículo'
                    ),
                ),
                migrations.AlterField(
                    model_name='viagem',
                    name='motorista',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='viagens',
                        to='frota.motorista',
                        verbose_name='Motorista'
                    ),
                ),
                # 2. Remover os models de frota do estado de cadastros
                migrations.DeleteModel(name='FotoAbastecimento'),
                migrations.DeleteModel(name='TelemetriaVeiculo'),
                migrations.DeleteModel(name='PedagioVeiculo'),
                migrations.DeleteModel(name='AlertaManutencao'),
                migrations.DeleteModel(name='DocumentoManutencao'),
                migrations.DeleteModel(name='ManutencaoItem'),
                migrations.DeleteModel(name='ManutencaoVeiculo'),
                migrations.DeleteModel(name='AbastecimentoVeiculo'),
                migrations.DeleteModel(name='MotoristaVinculoPlaca'),
                migrations.DeleteModel(name='MotoristadoDocumento'),
                migrations.DeleteModel(name='Motorista'),
                migrations.DeleteModel(name='VehicleDocument'),
                migrations.DeleteModel(name='VehiclePlate'),
                migrations.DeleteModel(name='VehicleValueHistory'),
                migrations.DeleteModel(name='Vehicle'),
            ],
        ),
    ]
