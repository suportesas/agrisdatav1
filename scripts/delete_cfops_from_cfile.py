import re
import pathlib
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from cadastros.models import CFOP

p = pathlib.Path('arq_cfop/C.csv')
codes = set()
with p.open(encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        m = re.match(r'"?\s*(\d{1,4})\s*;', line)
        if m:
            codes.add(m.group(1))

print('Found', len(codes), 'codes in file')
existing = CFOP.objects.filter(codigo__in=codes)
print('Existing CFOPs matching file:', existing.count())
count = existing.count()
existing.delete()
print('Deleted', count, 'CFOPs')
print('CFOP total now:', CFOP.objects.count())
