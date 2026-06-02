from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0054_vehicle_descricao'),
    ]

    operations = [
        migrations.CreateModel(
            name='MotoristaVinculoPlaca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateField(verbose_name='Data Inicio')),
                ('data_fim', models.DateField(blank=True, null=True, verbose_name='Data Fim')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observacoes')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data de Cadastro')),
                ('data_atualizacao', models.DateTimeField(auto_now=True, verbose_name='Ultima Atualizacao')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_motorista_placa', to='empresas.empresa', verbose_name='Empresa')),
                ('motorista', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_placas', to='frota.motorista', verbose_name='Motorista')),
                ('placa_principal', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vinculos_principal', to='cadastros.vehicleplate', verbose_name='Placa Principal')),
                ('reboques', models.ManyToManyField(blank=True, related_name='vinculos_reboque', to='cadastros.vehicleplate', verbose_name='Placas de Reboque')),
            ],
            options={
                'verbose_name': 'Vinculo Motorista x Placa',
                'verbose_name_plural': 'Vinculos Motorista x Placa',
                'ordering': ['-data_inicio'],
            },
        ),
        migrations.AddIndex(
            model_name='motoristavinculoplaca',
            index=models.Index(fields=['empresa', 'motorista'], name='cadastros_m_empresa_4a1fb5_idx'),
        ),
        migrations.AddIndex(
            model_name='motoristavinculoplaca',
            index=models.Index(fields=['empresa', 'data_inicio'], name='cadastros_m_empresa_67c7d2_idx'),
        ),
    ]
