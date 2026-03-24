import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from cadastros.models import NCM, CFOP

print('NCM templates ativos:', NCM.objects.filter(ativo=True).count())
print('CFOP templates ativos:', CFOP.objects.filter(ativo=True).count())
