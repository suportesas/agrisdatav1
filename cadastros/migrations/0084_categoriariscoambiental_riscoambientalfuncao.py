from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0083_solicitacaoaso_periodicidade_meses'),
        ('empresas', '0022_empresa_is_interna_saas'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaRiscoAmbiental',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Código interno da categoria (ex.: FISICO, QUIMICO).', max_length=20, verbose_name='Código')),
                ('nome', models.CharField(max_length=80, verbose_name='Nome da Categoria')),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativa')),
                ('eh_padrao_sistema', models.BooleanField(default=False, verbose_name='Categoria Padrão do Sistema')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias_risco_ambiental', to='empresas.empresa', verbose_name='Empresa')),
            ],
            options={
                'verbose_name': 'Categoria de Risco Ambiental',
                'verbose_name_plural': 'Categorias de Risco Ambiental',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='RiscoAmbientalFuncao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agente_especifico', models.CharField(help_text='Ex.: Ruído acima de 85dB, Poeira orgânica, Bactérias ambientais.', max_length=200, verbose_name='Agente Específico')),
                ('intensidade', models.CharField(choices=[('BAIXA', 'Baixa'), ('MEDIA', 'Média'), ('ALTA', 'Alta')], default='MEDIA', max_length=10, verbose_name='Intensidade')),
                ('epi_obrigatorio', models.CharField(blank=True, help_text='Ex.: Protetor auricular, máscara com filtro, luvas específicas.', max_length=255, verbose_name='EPI Obrigatório')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('data_criacao', models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='riscos_funcao', to='cadastros.categoriariscoambiental', verbose_name='Categoria de Risco')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='riscos_ambientais_funcao', to='empresas.empresa', verbose_name='Empresa')),
                ('funcao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='riscos_ambientais', to='cadastros.funcaofuncionario', verbose_name='Função/Cargo')),
            ],
            options={
                'verbose_name': 'Risco Ambiental da Função',
                'verbose_name_plural': 'Riscos Ambientais da Função',
                'ordering': ['categoria__nome', 'agente_especifico'],
            },
        ),
        migrations.AddConstraint(
            model_name='categoriariscoambiental',
            constraint=models.UniqueConstraint(fields=('empresa', 'codigo'), name='unique_categoria_risco_codigo_empresa'),
        ),
        migrations.AddConstraint(
            model_name='categoriariscoambiental',
            constraint=models.UniqueConstraint(fields=('empresa', 'nome'), name='unique_categoria_risco_nome_empresa'),
        ),
        migrations.AddConstraint(
            model_name='riscoambientalfuncao',
            constraint=models.UniqueConstraint(fields=('funcao', 'categoria', 'agente_especifico'), name='unique_risco_ambiental_funcao_categoria_agente'),
        ),
        migrations.AddIndex(
            model_name='riscoambientalfuncao',
            index=models.Index(fields=['empresa', 'ativo'], name='cadastros_r_empresa_19df8f_idx'),
        ),
        migrations.AddIndex(
            model_name='riscoambientalfuncao',
            index=models.Index(fields=['funcao'], name='cadastros_r_funcao__b4e6b4_idx'),
        ),
        migrations.AddIndex(
            model_name='riscoambientalfuncao',
            index=models.Index(fields=['categoria'], name='cadastros_r_catego_8d84cf_idx'),
        ),
    ]
