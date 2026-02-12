#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Vendedor
from empresas.models import Empresa

# Get Terra Brasilis
emp = Empresa.objects.get(id=35)

# Find James Markley in Terra Brasilis
james_tb = Vendedor.objects.get(empresa=emp, nome_completo='James Markley')

print(f'Corrigindo James Markley em Terra Brasilis...')
print(f'Antes: tipo_mercado={james_tb.tipo_mercado}')

# Update to EXTERNO (he's an export vendor)
james_tb.tipo_mercado = 'EXTERNO'
james_tb.save()

print(f'Depois: tipo_mercado={james_tb.tipo_mercado}')

# Verify
print('\n✅ Vendedores atualizados em Terra Brasilis:')
for v in Vendedor.objects.filter(empresa=emp).order_by('nome_completo'):
    print(f'  - {v.nome_completo} (tipo_mercado={v.tipo_mercado}, status={v.status})')
