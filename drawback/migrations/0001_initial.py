from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('empresas', '0001_initial'),
        ('usuarios', '0001_initial'),
        ('produtos', '0001_initial'),
        ('cadastros', '0001_initial'),
        ('compras', '0001_initial'),
        ('faturamento', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AtoConcessorio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_ac', models.CharField(help_text='Ex: 23/0001234-0', max_length=30, verbose_name='Número do AC')),
                ('tipo', models.CharField(choices=[('SUSPENSAO', 'Suspensão'), ('ISENCAO', 'Isenção'), ('RESTITUICAO', 'Restituição')], default='SUSPENSAO', max_length=15, verbose_name='Tipo')),
                ('data_inicio', models.DateField(verbose_name='Data de Início')),
                ('data_vencimento', models.DateField(verbose_name='Data de Vencimento')),
                ('data_prorrogacao', models.DateField(blank=True, help_text='Preencher apenas se o AC foi prorrogado', null=True, verbose_name='Data de Prorrogação')),
                ('status', models.CharField(choices=[('ATIVO', 'Ativo'), ('VENCIDO', 'Vencido'), ('ENCERRADO', 'Encerrado'), ('CANCELADO', 'Cancelado')], default='ATIVO', max_length=15, verbose_name='Status')),
                ('despachante', models.CharField(blank=True, max_length=150, verbose_name='Despachante Aduaneiro')),
                ('numero_processo_siscomex', models.CharField(blank=True, max_length=50, verbose_name='Nº Processo Siscomex')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Última Atualização')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='atos_concessorios', to='empresas.empresa', verbose_name='Empresa')),
                ('criado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='atos_concessorios_criados', to='usuarios.usuario', verbose_name='Criado por')),
            ],
            options={
                'verbose_name': 'Ato Concessório',
                'verbose_name_plural': 'Atos Concessórios',
                'ordering': ['-data_inicio'],
            },
        ),
        migrations.AddIndex(
            model_name='atoconcessorio',
            index=models.Index(fields=['empresa', 'status'], name='db_ac_emp_status_idx'),
        ),
        migrations.AddIndex(
            model_name='atoconcessorio',
            index=models.Index(fields=['data_vencimento'], name='db_ac_vencimento_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='atoconcessorio',
            unique_together={('empresa', 'numero_ac')},
        ),
        migrations.CreateModel(
            name='DrawbackProdutoAC',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ncm', models.CharField(blank=True, max_length=10, verbose_name='NCM')),
                ('descricao_mercadoria', models.CharField(max_length=200, verbose_name='Descrição conforme AC')),
                ('quantidade_autorizada', models.DecimalField(decimal_places=3, help_text='Total autorizado pelo MDIC para este produto', max_digits=15, verbose_name='Quantidade Autorizada')),
                ('quantidade_minima_export', models.DecimalField(decimal_places=3, help_text='Mínimo necessário para comprovar cumprimento do AC', max_digits=15, verbose_name='Quantidade Mínima a Exportar')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('ato_concessorio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produtos', to='drawback.atoconcessorio', verbose_name='Ato Concessório')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='drawback_produtos', to='produtos.produto', verbose_name='Produto')),
                ('unidade_medida', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='drawback_produtos', to='produtos.unidademedida', verbose_name='Unidade de Medida')),
            ],
            options={
                'verbose_name': 'Produto do AC',
                'verbose_name_plural': 'Produtos do AC',
                'ordering': ['produto__nome'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='drawbackprodutoac',
            unique_together={('ato_concessorio', 'produto')},
        ),
        migrations.CreateModel(
            name='EntradaDrawback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_nf', models.CharField(max_length=20, verbose_name='Número da NF')),
                ('serie_nf', models.CharField(blank=True, default='1', max_length=5, verbose_name='Série')),
                ('data_nf', models.DateField(verbose_name='Data da NF')),
                ('data_recebimento', models.DateField(verbose_name='Data do Recebimento')),
                ('quantidade', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='Quantidade')),
                ('valor_unitario', models.DecimalField(blank=True, decimal_places=4, max_digits=15, null=True, verbose_name='Valor Unitário (R$)')),
                ('tipo_compra', models.CharField(choices=[('IMPORTACAO', 'Importação'), ('MERCADO_INTERNO', 'Mercado Interno')], default='MERCADO_INTERNO', max_length=20, verbose_name='Tipo de Compra')),
                ('origem', models.CharField(choices=[('ERP', 'ERP (vinculado ao recebimento)'), ('MANUAL', 'Manual (lançamento retroativo)')], default='MANUAL', max_length=10, verbose_name='Origem')),
                ('retroativo', models.BooleanField(default=False, help_text='Marcado para lançamentos de regularização de períodos anteriores', verbose_name='Lançamento Retroativo')),
                ('anulado', models.BooleanField(default=False, verbose_name='Anulado')),
                ('motivo_anulacao', models.TextField(blank=True, verbose_name='Motivo da Anulação')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('data_registro', models.DateTimeField(auto_now_add=True, verbose_name='Data do Registro')),
                ('ato_concessorio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entradas', to='drawback.atoconcessorio', verbose_name='Ato Concessório')),
                ('drawback_produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='entradas', to='drawback.drawbackprodutoac', verbose_name='Produto do AC')),
                ('fornecedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='drawback_entradas', to='cadastros.fornecedor', verbose_name='Fornecedor')),
                ('item_recebimento', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='drawback_entrada', to='compras.itemrecebimento', verbose_name='Item do Recebimento')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='drawback_entradas_registradas', to='usuarios.usuario', verbose_name='Registrado por')),
            ],
            options={
                'verbose_name': 'Entrada Drawback',
                'verbose_name_plural': 'Entradas Drawback',
                'ordering': ['data_recebimento', 'numero_nf'],
            },
        ),
        migrations.AddIndex(
            model_name='entradadrawback',
            index=models.Index(fields=['ato_concessorio', 'anulado'], name='db_entrada_ac_anulado_idx'),
        ),
        migrations.AddIndex(
            model_name='entradadrawback',
            index=models.Index(fields=['drawback_produto', 'anulado'], name='db_entrada_prod_anulado_idx'),
        ),
        migrations.AddIndex(
            model_name='entradadrawback',
            index=models.Index(fields=['data_recebimento'], name='db_entrada_data_idx'),
        ),
        migrations.CreateModel(
            name='SaidaDrawback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_nfe', models.CharField(blank=True, max_length=20, verbose_name='Número da NF-e / Invoice')),
                ('numero_re', models.CharField(blank=True, help_text='Número do RE no Siscomex', max_length=30, verbose_name='RE (Registro de Exportação)')),
                ('numero_due', models.CharField(blank=True, max_length=30, verbose_name='DUE (Declaração Única de Exportação)')),
                ('data_embarque', models.DateField(verbose_name='Data de Embarque')),
                ('quantidade', models.DecimalField(decimal_places=3, max_digits=15, verbose_name='Quantidade')),
                ('valor_fob_usd', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True, verbose_name='Valor FOB (USD)')),
                ('origem', models.CharField(choices=[('ERP', 'ERP (vinculado à NF-e)'), ('MANUAL', 'Manual (lançamento retroativo)')], default='MANUAL', max_length=10, verbose_name='Origem')),
                ('retroativo', models.BooleanField(default=False, verbose_name='Lançamento Retroativo')),
                ('anulado', models.BooleanField(default=False, verbose_name='Anulado')),
                ('motivo_anulacao', models.TextField(blank=True, verbose_name='Motivo da Anulação')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('data_registro', models.DateTimeField(auto_now_add=True, verbose_name='Data do Registro')),
                ('ato_concessorio', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='saidas', to='drawback.atoconcessorio', verbose_name='Ato Concessório')),
                ('cliente', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='drawback_saidas', to='cadastros.cliente', verbose_name='Cliente')),
                ('drawback_produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='saidas', to='drawback.drawbackprodutoac', verbose_name='Produto do AC')),
                ('item_nfe', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='drawback_saida', to='faturamento.itemnotafiscal', verbose_name='Item da NF-e')),
                ('registrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='drawback_saidas_registradas', to='usuarios.usuario', verbose_name='Registrado por')),
            ],
            options={
                'verbose_name': 'Saída Drawback',
                'verbose_name_plural': 'Saídas Drawback',
                'ordering': ['data_embarque', 'numero_nfe'],
            },
        ),
        migrations.AddIndex(
            model_name='saidadrawback',
            index=models.Index(fields=['ato_concessorio', 'anulado'], name='db_saida_ac_anulado_idx'),
        ),
        migrations.AddIndex(
            model_name='saidadrawback',
            index=models.Index(fields=['drawback_produto', 'anulado'], name='db_saida_prod_anulado_idx'),
        ),
        migrations.AddIndex(
            model_name='saidadrawback',
            index=models.Index(fields=['data_embarque'], name='db_saida_data_idx'),
        ),
    ]
