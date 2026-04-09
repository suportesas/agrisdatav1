#!/usr/bin/env python
import os, sys, django
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from empresas.models import Empresa
from cadastros.models import EmpresaNCM

for emp in Empresa.objects.all():
    ncm_count = EmpresaNCM.objects.filter(empresa=emp).count()
    print(f"[{emp.pk}] {emp.nome} - auto_seed: {emp.auto_seed_ncm} - NCMs: {ncm_count}")
