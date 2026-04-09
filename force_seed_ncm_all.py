#!/usr/bin/env python
"""
Force seed de NCM para todas as empresas
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from empresas.models import Empresa
from cadastros.tasks import seed_ncms_for_company

print("\nFORCANDO SEED DE NCM PARA TODAS AS EMPRESAS")
print("="*60)

for emp in Empresa.objects.filter(bloqueada=False):
    print(f"\n[{emp.pk}] {emp.nome}")
    
    try:
        result = seed_ncms_for_company(emp.pk, force=True)
        print(f"    Resultado: {result}")
    except Exception as e:
        print(f"    ERRO: {e}")

print("\n" + "="*60 + "\n")
