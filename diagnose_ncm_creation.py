#!/usr/bin/env python
"""
Diagnóstico: Por que NCMs não estão sendo criados ao criar nova empresa
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

import logging
from cadastros.models import NCM, EmpresaNCM
from empresas.models import Empresa

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("\n" + "="*80)
print("DIAGNÓSTICO: CRIAÇÃO DE NCM EM NOVAS EMPRESAS")
print("="*80)

# 1. Verificar templates NCM globais
print("\n[1] TEMPLATES NCM GLOBAIS (NCM da tabela NCM):")
ncm_globais_ativos = NCM.objects.filter(ativo=True)
ncm_globais_total = NCM.objects.all()
print(f"    Total de NCMs cadastrados: {ncm_globais_total.count()}")
print(f"    NCMs ativos: {ncm_globais_ativos.count()}")

if ncm_globais_ativos.count() == 0:
    print(f"    ⚠️  ALERTA: Nenhum template NCM global ativo!")
    print(f"       Se uma empresa for criada agora, nenhum NCM será gerado.")
    print(f"       Solução: Importar arquivo CSV de NCMs antes de criar empresa")
else:
    print(f"    ✓ Templates disponíveis: {list(ncm_globais_ativos[:3].values_list('codigo', 'nome'))}")

# 2. Verificar arquivo CSV
print("\n[2] ARQUIVO CSV DE IMPORTAÇÃO:")
csv_path = os.path.join(Path(__file__).parent, 'NCM_import.csv')
print(f"    Caminho: {csv_path}")
print(f"    Existe: {os.path.exists(csv_path)}")
if os.path.exists(csv_path):
    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        linhas = len(f.readlines())
    print(f"    Linhas: {linhas}")

# 3. Verificar últimas empresas criadas
print("\n[3] ÚLTIMAS EMPRESAS CRIADAS:")
empresas = Empresa.objects.all().order_by('-data_criacao')[:5]
for emp in empresas:
    ncm_count = EmpresaNCM.objects.filter(empresa=emp).count()
    print(f"    [{emp.pk}] {emp.nome}")
    print(f"          auto_seed_ncm: {emp.auto_seed_ncm}")
    print(f"          EmpresaNCM registrados: {ncm_count}")
    print(f"          Última atualização NCM: {emp.last_ncm_seeded_at}")

# 4. Verificar if campo CFOP também está vazio (pista)
print("\n[4] COMPARAÇÃO COM CFOP (indicador):")
from cadastros.models import CFOP, EmpresaCFOP
cfop_globais = CFOP.objects.filter(ativo=True).count()
print(f"    Templates CFOP globais ativos: {cfop_globais}")
if empresas.first():
    cfop_empresa = EmpresaCFOP.objects.filter(empresa=empresas.first()).count()
    print(f"    CFOP na primeira empresa: {cfop_empresa}")

# 5. Resumo
print("\n" + "="*80)
print("RESUMO DO PROBLEMA:")
print("="*80)

if ncm_globais_ativos.count() == 0:
    print("""
⚠️  PROBLEMA IDENTIFICADO: Nenhum template NCM global cadastrado!

SOLUÇÃO:
1. Importar arquivo CSV com NCMs:
   python manage.py import_ncm --path NCM_import.csv

2. Depois recriar a empresa ou executar:
   python -c \"
   from cadastros.tasks import seed_ncms_for_company
   from empresas.models import Empresa
   empresa = Empresa.objects.last()
   seed_ncms_for_company(empresa.pk, force=True)
   \"
    """)
else:
    print(f"""
✓ Existe {ncm_globais_ativos.count()} templates NCM cadastrados.

Se a empresa foi criada ANTES desses NCMs serem importados,
execute (para cada empresa):

python -c \"
from cadastros.tasks import seed_ncms_for_company
from empresas.models import Empresa
empresa = Empresa.objects.get(pk=X)  # Substitua X pelo ID da empresa
seed_ncms_for_company(empresa.pk, force=True)
\"
    """)

print("="*80 + "\n")
