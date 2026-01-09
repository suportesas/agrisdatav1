# Generated manual migration: add Vehicle models and CNH fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0021_transportadora_contribuinte_icms_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='funcionario',
            name='cnh',
            field=models.CharField('CNH', max_length=20, blank=True),
        ),
        migrations.AddField(
            model_name='funcionario',
            name='cnh_validade',
            field=models.DateField('Validade CNH', null=True, blank=True),
        ),
        migrations.CreateModel(
            name='Vehicle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('LEVE', 'Leve'), ('MEDIO', 'Médio'), ('PESADO', 'Pesado'), ('REBOQUE', 'Reboque'), ('IMPLEMENTO', 'Implemento')], default='LEVE', max_length=20)),
                ('marca', models.CharField(max_length=100, blank=True)),
                ('modelo', models.CharField(max_length=100, blank=True)),
                ('ano_fabricacao', models.IntegerField(null=True, blank=True)),
                ('ano_modelo', models.IntegerField(null=True, blank=True)),
                ('capacidade_ton', models.DecimalField(null=True, decimal_places=2, max_digits=8, blank=True)),
                ('tara_kg', models.IntegerField(null=True, blank=True)),
                ('eixos', models.IntegerField(null=True, blank=True)),
                ('cor', models.CharField(max_length=50, blank=True)),
                ('observacoes', models.TextField(blank=True)),
                ('ativo', models.BooleanField(default=True)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('data_atualizacao', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='veiculos', to='empresas.empresa')),
                ('transportadora', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='veiculos', to='cadastros.transportadora')),
            ],
            options={
                'verbose_name': 'Veículo',
                'verbose_name_plural': 'Veículos',
                'ordering': ['-data_cadastro'],
            },
        ),
        migrations.CreateModel(
            name='VehiclePlate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('placa', models.CharField(max_length=10)),
                ('vigencia_inicio', models.DateField()),
                ('vigencia_fim', models.DateField(null=True, blank=True)),
                ('atual', models.BooleanField(default=False)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plates', to='cadastros.vehicle')),
            ],
            options={
                'ordering': ['-vigencia_inicio'],
                'verbose_name': 'Placa do Veículo',
                'verbose_name_plural': 'Placas do Veículo',
            },
        ),
        migrations.CreateModel(
            name='VehicleAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('placa', models.CharField(max_length=10, blank=True)),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField(null=True, blank=True)),
                ('motivo', models.CharField(max_length=200, blank=True)),
                ('motorista', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='veiculos_atribuidos', to='cadastros.funcionario')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='cadastros.vehicle')),
            ],
            options={
                'ordering': ['-data_inicio'],
                'verbose_name': 'Atribuição de Veículo',
                'verbose_name_plural': 'Atribuições de Veículos',
            },
        ),
        migrations.CreateModel(
            name='VehicleDocument',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(max_length=50)),
                ('numero', models.CharField(max_length=100, blank=True)),
                ('data_emissao', models.DateField(null=True, blank=True)),
                ('data_validade', models.DateField(null=True, blank=True)),
                ('arquivo', models.FileField(upload_to='vehicle_docs/', null=True, blank=True)),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='cadastros.vehicle')),
            ],
            options={
                'verbose_name': 'Documento do Veículo',
                'verbose_name_plural': 'Documentos do Veículo',
            },
        ),
        migrations.AddIndex(
            model_name='vehicle',
            index=models.Index(fields=['empresa', 'ativo'], name='cadastr_vehicle_emp_0c7f3c_idx'),
        ),
    ]
