"""
Registra os 7 models de estufa no estado Django do app estufas.
Sem SQL — as tabelas permanecem com o mesmo nome (db_table = 'cadastros_*').
"""
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0110_remove_emprestimo_models'),
        ('empresas', '0001_initial'),
        ('produtos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Estufa',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('nome', models.CharField(max_length=100)),
                        ('codigo', models.CharField(max_length=20)),
                        ('area_m2', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='Área (m²)')),
                        ('capacidade_bandejas', models.IntegerField(blank=True, null=True, verbose_name='Capacidade (bandejas)')),
                        ('tipo', models.CharField(choices=[('PLASTICO', 'Plástico'), ('VIDRO', 'Vidro'), ('SOMBRITE', 'Sombrite'), ('OUTRO', 'Outro')], default='PLASTICO', max_length=30)),
                        ('ativo', models.BooleanField(default=True)),
                        ('observacoes', models.TextField(blank=True)),
                        ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                        ('cadastrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='estufas_criadas', to=settings.AUTH_USER_MODEL)),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estufas', to='empresas.empresa')),
                        ('fazenda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='estufas', to='cadastros.fazenda')),
                    ],
                    options={
                        'verbose_name': 'Estufa',
                        'verbose_name_plural': 'Estufas',
                        'db_table': 'cadastros_estufa',
                        'ordering': ['fazenda', 'nome'],
                    },
                ),
                migrations.CreateModel(
                    name='LoteMuda',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('cultivar', models.CharField(blank=True, max_length=100)),
                        ('codigo_lote', models.CharField(max_length=30, unique=True)),
                        ('lote_semente', models.CharField(blank=True, max_length=100, verbose_name='Lote da semente')),
                        ('data_semeadura', models.DateField()),
                        ('quantidade_semeada', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                        ('data_prevista_pronto', models.DateField(blank=True, null=True, verbose_name='Data prevista para transplantio')),
                        ('status', models.CharField(choices=[('SEMEADO', 'Semeado'), ('EM_CRESCIMENTO', 'Em Crescimento'), ('PRONTO', 'Pronto p/ Transplantio'), ('TRANSPLANTADO', 'Transplantado'), ('ENCERRADO', 'Encerrado')], default='SEMEADO', max_length=20)),
                        ('observacoes', models.TextField(blank=True)),
                        ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                        ('cadastrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lotes_criados', to=settings.AUTH_USER_MODEL)),
                        ('cultura', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lotes_muda', to='cadastros.cultura')),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lotes_muda', to='empresas.empresa')),
                        ('estufa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lotes', to='estufas.estufa')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lotes_responsavel', to='cadastros.funcionario')),
                    ],
                    options={
                        'verbose_name': 'Lote de Mudas',
                        'verbose_name_plural': 'Lotes de Mudas',
                        'db_table': 'cadastros_lotemuda',
                        'ordering': ['-data_semeadura'],
                    },
                ),
                migrations.CreateModel(
                    name='PerdaEstufa',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('data', models.DateField()),
                        ('quantidade_perdida', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                        ('motivo', models.CharField(choices=[('DOENCA', 'Doença'), ('PRAGA', 'Praga'), ('AMBIENTE', 'Fator Ambiental'), ('QUALIDADE', 'Qualidade da Semente'), ('OUTRO', 'Outro')], max_length=30)),
                        ('observacao', models.TextField(blank=True)),
                        ('lote_muda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='perdas', to='estufas.lotemuda')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='perdas_estufa', to='cadastros.funcionario')),
                    ],
                    options={
                        'verbose_name': 'Perda na Estufa',
                        'verbose_name_plural': 'Perdas na Estufa',
                        'db_table': 'cadastros_perdaestufa',
                        'ordering': ['-data'],
                    },
                ),
                migrations.CreateModel(
                    name='AplicacaoEstufa',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('data', models.DateField()),
                        ('tipo', models.CharField(choices=[('DEFENSIVO', 'Defensivo'), ('FERTILIZANTE', 'Fertilizante'), ('OUTRO', 'Outro')], max_length=20)),
                        ('quantidade', models.DecimalField(decimal_places=3, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.001'))])),
                        ('custo_unitario', models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='Custo unitário (R$)')),
                        ('observacao', models.CharField(blank=True, max_length=255)),
                        ('receituario', models.CharField(blank=True, max_length=50, verbose_name='Nº Receituário Agronômico')),
                        ('lote_muda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aplicacoes', to='estufas.lotemuda')),
                        ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='produtos.produto')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='aplicacoes_estufa', to='cadastros.funcionario')),
                        ('unidade_medida', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='produtos.unidademedida')),
                    ],
                    options={
                        'verbose_name': 'Aplicação na Estufa',
                        'verbose_name_plural': 'Aplicações na Estufa',
                        'db_table': 'cadastros_aplicacaoestufa',
                        'ordering': ['-data'],
                    },
                ),
                migrations.CreateModel(
                    name='MonitoramentoEstufa',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('data', models.DateField()),
                        ('nivel_infestacao', models.CharField(choices=[('AUSENTE', 'Ausente'), ('BAIXO', 'Baixo'), ('MEDIO', 'Médio'), ('ALTO', 'Alto')], max_length=20)),
                        ('acao_tomada', models.TextField(blank=True)),
                        ('lote_muda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monitoramentos_estufa', to='estufas.lotemuda')),
                        ('praga', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='monitoramentos_estufa', to='cadastros.praga')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='monitoramentos_estufa', to='cadastros.funcionario')),
                    ],
                    options={
                        'verbose_name': 'Monitoramento na Estufa',
                        'verbose_name_plural': 'Monitoramentos na Estufa',
                        'db_table': 'cadastros_monitoramentoestufa',
                        'ordering': ['-data'],
                    },
                ),
                migrations.CreateModel(
                    name='Transplantio',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('data_transplantio', models.DateField()),
                        ('tipo', models.CharField(choices=[('TOTAL', 'Total'), ('PARCIAL', 'Parcial')], default='TOTAL', max_length=10)),
                        ('quantidade_transplantada', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                        ('custo_transferido', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=14)),
                        ('observacao', models.TextField(blank=True)),
                        ('fotos', models.ImageField(blank=True, null=True, upload_to='transplantios/%Y/%m/')),
                        ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                        ('cadastrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transplantios_criados', to=settings.AUTH_USER_MODEL)),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transplantios', to='empresas.empresa')),
                        ('lote_muda', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transplantios', to='estufas.lotemuda')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transplantios', to='cadastros.funcionario')),
                        ('safra', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transplantios', to='cadastros.safra')),
                        ('talhao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='transplantios', to='cadastros.talhao')),
                    ],
                    options={
                        'verbose_name': 'Transplantio',
                        'verbose_name_plural': 'Transplantios',
                        'db_table': 'cadastros_transplantio',
                        'ordering': ['-data_transplantio'],
                    },
                ),
                migrations.CreateModel(
                    name='ReplantioTalhao',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('data_replantio', models.DateField()),
                        ('quantidade', models.IntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                        ('origem_muda', models.CharField(choices=[('ESTUFA', 'Estufa Própria'), ('COMPRA', 'Compra Externa'), ('OUTRA_AREA', 'Outra Área')], max_length=20)),
                        ('motivo_perda', models.CharField(choices=[('CLIMA', 'Clima / Intempérie'), ('PRAGA', 'Praga'), ('DOENCA', 'Doença'), ('MECANICO', 'Dano Mecânico'), ('OUTRO', 'Outro')], max_length=30)),
                        ('custo_adicional', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0'))], verbose_name='Custo adicional (R$)')),
                        ('observacao', models.TextField(blank=True)),
                        ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                        ('cadastrado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replantios_criados', to=settings.AUTH_USER_MODEL)),
                        ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replantios', to='empresas.empresa')),
                        ('lote_muda', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replantios', to='estufas.lotemuda')),
                        ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replantios', to='cadastros.funcionario')),
                        ('safra', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replantios', to='cadastros.safra')),
                        ('talhao', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='replantios', to='cadastros.talhao')),
                    ],
                    options={
                        'verbose_name': 'Replantio',
                        'verbose_name_plural': 'Replantios',
                        'db_table': 'cadastros_replantiotalhao',
                        'ordering': ['-data_replantio'],
                    },
                ),
            ],
        ),
    ]
