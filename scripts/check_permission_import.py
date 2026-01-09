import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')

try:
    import django
    django.setup()
    import empresas.models as m
    print('has PermissionTemplate?', hasattr(m, 'PermissionTemplate'))
    print('PermissionTemplate in dir:', 'PermissionTemplate' in dir(m))
    # Try to instantiate model class name
    cls = getattr(m, 'PermissionTemplate', None)
    print('cls is', cls)
except Exception as e:
    import traceback
    print('ERROR during import:')
    traceback.print_exc()