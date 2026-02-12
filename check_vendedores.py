#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from cadastros.models import Vendedor, Cliente
from cadastros.forms import ClienteForm
from empresas.models import Empresa

# Get the CLIENT 7 empresa, not the first one!
cliente = Cliente.objects.get(pk=7)
emp_obj = cliente.empresa

print(f'Cliente 7 Empresa: {emp_obj} (id={emp_obj.id})')
print(f'Total vendedores nesta empresa: {Vendedor.objects.filter(empresa=emp_obj).count()}')
print(f'Vendedores ATIVO nesta empresa: {Vendedor.objects.filter(empresa=emp_obj, status="ATIVO").count()}')
print('\nVendedores da EMPRESA DO CLIENTE 7:')
for v in Vendedor.objects.filter(empresa=emp_obj):
    print(f'  - {v.nome_completo} (id={v.id}, status={v.status}, tipo_mercado={v.tipo_mercado})')

print(f'\nCliente 7: {cliente.razao_social} (id={cliente.id})')
print(f'  - tipo_cliente: {cliente.tipo_cliente}')
print(f'  - empresa: {cliente.empresa} (id={cliente.empresa.id})')
print(f'  - vendedor_responsavel: {cliente.vendedor_responsavel}')

# Test the form
print("\n===== TESTANDO FORM =====")
form = ClienteForm(instance=cliente, empresa=cliente.empresa, usuario=None)
qs = form.fields['vendedor_responsavel'].queryset
print(f'Queryset: {qs}')
print(f'Queryset count: {qs.count()}')
for v in qs:
    print(f'  - {v.nome_completo}')

# Test manual filters for the correct empresa
print("\n===== TESTE MANUAL FILTERS (EMPRESA CORRETA) =====")
qs_test = Vendedor.objects.filter(empresa=emp_obj)
print(f"1. Filter empresa only: {qs_test.count()} - {list(qs_test.values_list('nome_completo', flat=True))}")

qs_test = Vendedor.objects.filter(empresa=emp_obj, status='ATIVO')
print(f"2. Add status='ATIVO': {qs_test.count()} - {list(qs_test.values_list('nome_completo', flat=True))}")

qs_test = Vendedor.objects.filter(empresa=emp_obj, status='ATIVO', tipo_mercado__in=['EXTERNO', 'AMBOS'])
print(f"3. Add tipo_mercado filter for IMPORTADOR: {qs_test.count()} - {list(qs_test.values_list('nome_completo', flat=True))}")

# For internal client
qs_test = Vendedor.objects.filter(empresa=emp_obj, status='ATIVO', tipo_mercado__in=['INTERNO', 'AMBOS'])
print(f"4. Add tipo_mercado filter for INTERNO: {qs_test.count()} - {list(qs_test.values_list('nome_completo', flat=True))}")


