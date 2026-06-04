from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('financeiro', '10004_pagamento_conta_bancaria'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogAlteracaoPagamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(choices=[('RETORNO_PENDENTE', 'Retorno ao Pendente'), ('EDICAO', 'Edição de Dados')], max_length=30, verbose_name='Ação')),
                ('status_anterior', models.CharField(max_length=20, verbose_name='Status Anterior')),
                ('status_novo', models.CharField(max_length=20, verbose_name='Status Novo')),
                ('dados_anteriores', models.JSONField(default=dict, verbose_name='Dados Anteriores')),
                ('observacao', models.TextField(blank=True, verbose_name='Observação')),
                ('ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')),
                ('data_hora', models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora')),
                ('pagamento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='financeiro.pagamentocontapagar', verbose_name='Pagamento')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='logs_pagamento', to='usuarios.usuario', verbose_name='Usuário')),
            ],
            options={
                'verbose_name': 'Log de Alteração de Pagamento',
                'verbose_name_plural': 'Logs de Alterações de Pagamentos',
                'ordering': ['-data_hora'],
            },
        ),
    ]
