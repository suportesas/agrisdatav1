#!/usr/bin/env python
import os, sys, django
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from cadastros.models import NCM
print(f'Total NCM: {NCM.objects.count()}')
print(f'NCM Ativos: {NCM.objects.filter(ativo=True).count()}')
