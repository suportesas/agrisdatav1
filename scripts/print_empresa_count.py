import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
import django
django.setup()
from empresas.models import Empresa
print('Empresa count:', Empresa.objects.count())
