"""
Registra os 4 models do MIP no estado Django sem executar SQL.
As tabelas já existem no banco com nomes cadastros_* (db_table no model).
"""
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cadastros', '0108_remove_frota_models'),
        ('empresas', '0001_initial'),
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='EstagioDesenvolvimento',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('tipo_estagio', models.CharField(choices=[('OVO', 'Ovo'), ('NINFA', 'Ninfa'), ('LARVA', 'Larva'), ('PUPA', 'Pupa'), ('ADULTO', 'Adulto'), ('ESPORO', 'Esporo (Fungo)'), ('LESAO', 'Lesão (Doença)'), ('OUTRO', 'Outro')], max_length=20, verbose_name='Tipo de Estágio')),
                        ('descricao', models.CharField(blank=True, max_length=200, verbose_name='Descrição')),
                        ('duracao_minima_dias', models.IntegerField(blank=True, null=True, verbose_name='Duração Mínima (dias)')),
                        ('duracao_maxima_dias', models.IntegerField(blank=True, null=True, verbose_name='Duração Máxima (dias)')),
                        ('ordem_ciclo', models.IntegerField(default=1, verbose_name='Ordem no Ciclo')),
                        ('eh_fase_critica', models.BooleanField(default=False, verbose_name='É Fase Crítica?')),
                        ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                        ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                        ('eh_template', models.BooleanField(default=False, verbose_name='É Estágio Template?')),
                        ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                        ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                        ('empresa', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='estagios_desenvolvimento', to='empresas.empresa', verbose_name='Empresa')),
                        ('praga', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estagios', to='cadastros.praga', verbose_name='Praga')),
                        ('template_original', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='copias', to='mip.estagiodesenvolvimento', verbose_name='Template Original')),
                    ],
                    options={
                        'verbose_name': 'Estágio de Desenvolvimento',
                        'verbose_name_plural': 'Estágios de Desenvolvimento',
                        'db_table': 'cadastros_estagiodesenvolvimento',
                        'ordering': ['praga', 'ordem_ciclo'],
                    },
                ),
                migrations.CreateModel(
                    name='MonitoramentoMIP',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('numero', models.CharField(max_length=20, unique=True, verbose_name='Número')),
                        ('data_monitoramento', models.DateField(verbose_name='Data do Monitoramento')),
                        ('tipo_monitoramento', models.CharField(choices=[('REGULAR', 'Monitoramento Regular'), ('PREVENTIVO', 'Monitoramento Preventivo'), ('EMERGENCIAL', 'Monitoramento Emergencial')], default='REGULAR', max_length=20, verbose_name='Tipo de Monitoramento')),
                        ('quantidade_pontos', models.IntegerField(default=20, verbose_name='Quantidade de Pontos')),
                        ('condicoes_tempo', models.CharField(blank=True, max_length=100, verbose_name='Condições do Tempo')),
                        ('temperatura_media', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Temperatura Média (°C)')),
                        ('umidade_media', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)], verbose_name='Umidade Média (%)')),
                        ('velocidade_vento_media', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Velocidade do Vento Média (km/h)')),
                        ('foto_area_geral', models.ImageField(blank=True, null=True, upload_to='monitoramento_mip/%Y/%m/', verbose_name='Foto da Área Geral')),
                        ('status', models.CharField(choices=[('RASCUNHO', 'Rascunho'), ('COMPLETO', 'Monitoramento Completo'), ('ANALISADO', 'Analisado e Avaliado'), ('CANCELADO', 'Cancelado')], default='RASCUNHO', max_length=20, verbose_name='Status')),
                        ('observacoes_gerais', models.TextField(blank=True, verbose_name='Observações Gerais')),
                        ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                        ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monitoramentos_mip', to='empresas.empresa', verbose_name='Empresa')),
                        ('talhao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='monitoramentos_mip', to='cadastros.talhao', verbose_name='Talhão')),
                        ('safra', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='monitoramentos_mip', to='cadastros.safra', verbose_name='Safra')),
                        ('cultura', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='monitoramentos_mip', to='cadastros.cultura', verbose_name='Cultura')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitoramentos_mip_realizados', to='usuarios.usuario', verbose_name='Responsável (Pragueiro)')),
                        ('criado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitoramentos_mip_criados', to='usuarios.usuario', verbose_name='Criado Por')),
                    ],
                    options={
                        'verbose_name': 'Monitoramento MIP',
                        'verbose_name_plural': 'Monitoramentos MIP',
                        'db_table': 'cadastros_monitoramentomip',
                        'ordering': ['-data_monitoramento'],
                    },
                ),
                migrations.CreateModel(
                    name='PragaNoMonitoramento',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('quantidade_pontos_com_praga', models.IntegerField(verbose_name='Quantidade de Pontos com Praga')),
                        ('incidencia_percentual', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=5, verbose_name='Incidência (%)')),
                        ('detalhes_estagios', models.JSONField(blank=True, default=dict, verbose_name='Detalhes por Estágio')),
                        ('severidade', models.IntegerField(choices=[(1, 'Muito Baixa'), (2, 'Baixa'), (3, 'Média'), (4, 'Alta'), (5, 'Muito Alta')], default=3, verbose_name='Severidade (1-5)')),
                        ('quantidade_total_pragas', models.IntegerField(blank=True, null=True, verbose_name='Quantidade Total de Pragas Encontradas')),
                        ('ned_valor', models.DecimalField(decimal_places=2, default=5.0, max_digits=5, verbose_name='Nível Econômico de Dano (%)')),
                        ('ned_atingido', models.BooleanField(verbose_name='NED Atingido?')),
                        ('resultado_acao', models.CharField(choices=[('SEM_ACAO', 'Sem Ação Necessária'), ('MONITORAR', 'Continuar Monitorando'), ('RECOMENDA_DEFENSIVO', 'Recomenda Defensivo')], default='MONITORAR', max_length=20, verbose_name='Resultado da Ação')),
                        ('fotos', models.JSONField(blank=True, default=list, verbose_name='Fotos da Praga')),
                        ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                        ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                        ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                        ('monitoramento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pragas_detectadas', to='mip.monitoramentomip', verbose_name='Monitoramento MIP')),
                        ('praga', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='monitoramentos', to='cadastros.praga', verbose_name='Praga/Doença')),
                        ('estagio_principal', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='praga_monitoramento_estagio_principal', to='mip.estagiodesenvolvimento', verbose_name='Estágio Principal')),
                    ],
                    options={
                        'verbose_name': 'Praga no Monitoramento',
                        'verbose_name_plural': 'Pragas no Monitoramento',
                        'db_table': 'cadastros_praganomonitoramento',
                        'ordering': ['monitoramento', 'resultado_acao', '-incidencia_percentual'],
                    },
                ),
                migrations.CreateModel(
                    name='PontoMonitoramento',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('numero_ponto', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)], verbose_name='Número do Ponto')),
                        ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Latitude')),
                        ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True, verbose_name='Longitude')),
                        ('praga_presente', models.BooleanField(default=False, verbose_name='Praga Presente?')),
                        ('quantidade', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Quantidade')),
                        ('severidade', models.IntegerField(choices=[(0, 'Nenhuma'), (1, 'Muito Leve'), (2, 'Leve'), (3, 'Média'), (4, 'Severa'), (5, 'Muito Severa')], default=0, verbose_name='Severidade Neste Ponto')),
                        ('foto', models.ImageField(blank=True, null=True, upload_to='monitoramento_pontos/%Y/%m/', verbose_name='Foto do Ponto')),
                        ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                        ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                        ('praga_monitoramento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pontos', to='mip.praganomonitoramento', verbose_name='Praga no Monitoramento')),
                        ('estagio', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='mip.estagiodesenvolvimento', verbose_name='Estágio Encontrado')),
                    ],
                    options={
                        'verbose_name': 'Ponto de Monitoramento',
                        'verbose_name_plural': 'Pontos de Monitoramento',
                        'db_table': 'cadastros_pontomonitoramento',
                        'ordering': ['praga_monitoramento', 'numero_ponto'],
                    },
                ),
            ],
        ),
    ]
