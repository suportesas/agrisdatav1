#!/usr/bin/env python
"""
Reseed de NCMs para todas as empresas com auto_seed_ncm=True
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
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("POPULANDO NCMs EM EMPRESAS")
print("="*80)

# Buscar empresas que devem ter auto_seed
empresas = Empresa.objects.filter(auto_seed_ncm=True, bloqueada=False).order_by('-data_criacao')

print(f"\nEmpresas com auto_seed_ncm=True: {empresas.count()}")

for empresa in empresas:
    print(f"\n[{empresa.pk}] {empresa.nome}")
    
    result = seed_ncms_for_company(empresa.pk, force=True)
    
    if 'error' in result:
        print(f"    [ERRO] {result['error']}")
    else:
        print(f"    [OK] Criados: {result.get('created', 0)}")
        print(f"    [OK] Pulados: {result.get('skipped', 0)}")

print("\n" + "="*80)
print("População concluída!")
print("="*80 + "\n")
