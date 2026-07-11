"""
Atualiza (apenas no estado) o FK de Armazem.responsavel de cadastros.Funcionario
para rh.Funcionario, acompanhando a migração do model Funcionario para o app rh
(ver cadastros/migrations/0112_remove_rh_models.py).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0018_alter_movimentacaoestoque_numero_and_more'),
        ('rh', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='armazem',
                    name='responsavel',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='armazens_responsavel',
                        to='rh.funcionario',
                        verbose_name='Responsável'
                    ),
                ),
            ],
        ),
    ]
