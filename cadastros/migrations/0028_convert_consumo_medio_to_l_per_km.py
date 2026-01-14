from django.db import migrations, models
from decimal import Decimal


def convert_consumo(apps, schema_editor):
    Vehicle = apps.get_model('cadastros', 'Vehicle')
    for v in Vehicle.objects.all():
        if v.consumo_medio is not None:
            try:
                # Previously stored as L per 100km; convert to L/km
                new_val = (Decimal(v.consumo_medio) / Decimal('100'))
                v.consumo_medio = new_val
                v.consumo_unidade = 'L_KM'
                v.save(update_fields=['consumo_medio', 'consumo_unidade'])
            except Exception:
                continue


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0027_vehicle_tank_capacity_and_more'),
    ]

    operations = [
        migrations.RunPython(convert_consumo, reverse_code=migrations.RunPython.noop),
    ]
