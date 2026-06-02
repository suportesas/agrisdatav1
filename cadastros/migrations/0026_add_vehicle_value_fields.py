from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0025_remove_vehicle_assignment'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='valor_atual',
            field=models.DecimalField(blank=True, null=True, max_digits=12, decimal_places=2),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='percentual_variacao',
            field=models.DecimalField(blank=True, null=True, max_digits=5, decimal_places=2),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='tipo_variacao',
            field=models.CharField(blank=True, max_length=3),
        ),
        migrations.CreateModel(
            name='VehicleValueHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('previous_value', models.DecimalField(max_digits=12, decimal_places=2)),
                ('new_value', models.DecimalField(max_digits=12, decimal_places=2)),
                ('percentual', models.DecimalField(max_digits=6, decimal_places=2)),
                ('tipo', models.CharField(max_length=3)),
                ('data_aplicacao', models.DateTimeField(auto_now_add=True)),
                ('aplicado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='usuarios.usuario')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='value_history', to='frota.vehicle')),
            ],
            options={
                'ordering': ['-data_aplicacao'],
                'verbose_name': 'Histórico de Valor do Veículo',
                'verbose_name_plural': 'Históricos de Valor de Veículos',
            },
        ),
    ]
