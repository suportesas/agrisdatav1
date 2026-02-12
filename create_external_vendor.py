#!/usr/bin/env python
import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Vendedor
from empresas.models import Empresa

# Get the correct company
emp = Empresa.objects.get(id=35)
print(f'Empresa: {emp} (id={emp.id})')

# Create or update a vendor for external market
vendedor, created = Vendedor.objects.get_or_create(
    empresa=emp,
    cpf='12345678901',
    defaults={
        'nome_completo': 'Carlos Silva - Exportação',
        'tipo_mercado': 'EXTERNO',
        'tipo_vinculo': 'PJ',
        'email_corporativo': 'carlos@terrabasilis.com.br',
        'data_admissao': date.today(),
        'status': 'ATIVO',
    }
)

if created:
    print(f'✅ Vendedor CRIADO: {vendedor.nome_completo} (tipo_mercado={vendedor.tipo_mercado})')
else:
    # Update existing
    vendedor.tipo_mercado = 'EXTERNO'
    vendedor.status = 'ATIVO'
    vendedor.save()
    print(f'✅ Vendedor ATUALIZADO: {vendedor.nome_completo} (tipo_mercado={vendedor.tipo_mercado})')

# Verify
print('\nVendedores atuais da empresa:')
for v in Vendedor.objects.filter(empresa=emp):
    print(f'  - {v.nome_completo} (tipo_mercado={v.tipo_mercado}, status={v.status})')
