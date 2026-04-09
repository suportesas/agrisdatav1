#!/usr/bin/env python
"""
Debug: Testar seed_ncms_for_company manualmente
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from empresas.models import Empresa
from cadastros.models import NCM, EmpresaNCM
from cadastros.tasks import seed_ncms_for_company
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("\nDEBUG: TESTE DE SEED MANUAL")
print("="*60)

# Verificar status antes
print("\n1. VERIFICAÇÃO ANTES:")
print(f"   NCM templates: {NCM.objects.filter(ativo=True).count()}")
print(f"   Total EmpresaNCM: {EmpresaNCM.objects.count()}")

# Pegar primeira empresa
emp = Empresa.objects.first()
print(f"\n2. EMPRESA A SER USADA:")
print(f"   [{emp.pk}] {emp.nome}")

# Limpar NCMs dessa empresa
antes = EmpresaNCM.objects.filter(empresa=emp).count()
EmpresaNCM.objects.filter(empresa=emp).delete()
depois = EmpresaNCM.objects.filter(empresa=emp).count()
print(f"\n3. LIMPEZA:")
print(f"   Antes: {antes}")
print(f"   Depois: {depois}")

# Chamar seed
print(f"\n4. EXECUTANDO SEED:")
result = seed_ncms_for_company(emp.pk, force=True)
print(f"   Resultado: {result}")

# Verificar após
print(f"\n5. VERIFICAÇÃO APÓS:")
ncm_count = EmpresaNCM.objects.filter(empresa=emp).count()
print(f"   EmpresaNCM criados: {ncm_count}")
print(f"   Total EmpresaNCM: {EmpresaNCM.objects.count()}")

print("\n" + "="*60 + "\n")
