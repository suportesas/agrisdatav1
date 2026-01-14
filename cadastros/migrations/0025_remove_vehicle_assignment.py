from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0024_add_vehicle_optional_fields'),
    ]

    operations = [
        migrations.DeleteModel(
            name='VehicleAssignment',
        ),
    ]
