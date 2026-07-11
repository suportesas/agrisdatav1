"""
Registra a remoção dos modelos RH do estado Django do app cadastros.
Sem SQL — as tabelas permanecem (agora gerenciadas pelo app rh).
Antes de deletar, atualiza FKs de modelos restantes: cadastros.Funcionario -> rh.Funcionario.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0111_remove_estufa_models'),
        ('rh', '0001_initial'),
        # Precisa rodar só depois que outros apps já tiverem repontado seus FKs
        # de cadastros.Funcionario para rh.Funcionario, senão a checagem de
        # referências (lazy references) do Django falha para esses campos.
        ('estufas', '0002_initial'),
        ('estoque', '0019_alter_armazem_responsavel_rh_funcionario'),
        ('patrimonio', '0003_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                # Update FK references in remaining cadastros models before deleting Funcionario
                migrations.AlterField(
                    model_name='requisicao',
                    name='funcionario_destino',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='requisicoes_destino', to='rh.funcionario', verbose_name='Funcionario Destino'),
                ),
                migrations.AlterField(
                    model_name='ordemservico',
                    name='responsavel',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='os_responsavel', to='rh.funcionario', verbose_name='Responsável pela Execução'),
                ),
                migrations.AlterField(
                    model_name='osfuncionario',
                    name='funcionario',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='alocacoes_os', to='rh.funcionario', verbose_name='Funcionário'),
                ),
                migrations.AlterField(
                    model_name='osmaquina',
                    name='operador',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operacoes_maquina_os', to='rh.funcionario', verbose_name='Operador'),
                ),
                migrations.AlterField(
                    model_name='etapacolheita',
                    name='supervisor',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='etapas_supervisionadas', to='rh.funcionario', verbose_name='Supervisor de Campo'),
                ),
                migrations.AlterField(
                    model_name='frotacolheita',
                    name='operador',
                    field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operacoes_colheita', to='rh.funcionario', verbose_name='Operador/Tratorista'),
                ),
                migrations.AlterField(
                    model_name='registrocadernocampofuncionario',
                    name='funcionario',
                    field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='rh.funcionario'),
                ),
                # Delete RH models from cadastros state
                migrations.DeleteModel(name='HistoricoFuncionario'),
                migrations.DeleteModel(name='FuncaoFuncionario'),
                migrations.DeleteModel(name='CategoriaRiscoAmbiental'),
                migrations.DeleteModel(name='RiscoAmbientalFuncao'),
                migrations.DeleteModel(name='RiscoAmbientalCatalogo'),
                migrations.DeleteModel(name='VinculoContrato'),
                migrations.DeleteModel(name='Funcionario'),
                migrations.DeleteModel(name='DocumentoFuncionario'),
                migrations.DeleteModel(name='FeriasFuncionario'),
                migrations.DeleteModel(name='AfastamentoFuncionario'),
                migrations.DeleteModel(name='LaudoRisco'),
                migrations.DeleteModel(name='TipoExameASO'),
                migrations.DeleteModel(name='SolicitacaoASO'),
                migrations.DeleteModel(name='LogEnvioSolicitacaoASO'),
                migrations.DeleteModel(name='RescisaoContrato'),
            ],
        ),
    ]
