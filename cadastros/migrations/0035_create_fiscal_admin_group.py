from django.db import migrations


def create_fiscal_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    # Create group
    group, created = Group.objects.get_or_create(name='Fiscal Admin')

    # Permissions to assign
    perm_codenames = [
        'add_cfop', 'change_cfop', 'delete_cfop',
        'add_empresacfop', 'change_empresacfop', 'delete_empresacfop'
    ]

    for codename in perm_codenames:
        try:
            perm = Permission.objects.get(codename=codename, content_type__app_label='cadastros')
            group.permissions.add(perm)
        except Permission.DoesNotExist:
            # permission may not exist yet in some environments; ignore
            pass


def remove_fiscal_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='Fiscal Admin').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cadastros', '0034_empresacfop'),
    ]

    operations = [
        migrations.RunPython(create_fiscal_group, remove_fiscal_group),
    ]
