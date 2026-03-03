#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuarios.models import Usuario

user = Usuario.objects.filter(empresa__isnull=False).first()
client = Client()
client.force_login(user)

print("=== Testando página /compras/solicitacoes/nova/ ===")
response = client.get('/compras/solicitacoes/nova/')
print(f"Status: {response.status_code}")

if response.status_code == 200:
    html = response.content.decode('utf-8')
    
    checks = {
        'unidade_medida': 'unidade_medida' in html,
        'carregarUnidadesEmpresa': 'carregarUnidadesEmpresa' in html,
        'atualizarAoMudarProduto': 'atualizarAoMudarProduto' in html,
        'preencherSelectUnidade': 'preencherSelectUnidade' in html,
        'select2': 'select2' in html,
    }
    
    print("\nElementos na página:")
    for element, present in checks.items():
        print(f"  {'✓' if present else '✗'} {element}")
        
    if all(checks.values()):
        print("\n✓ Todos os elementos necessários foram encontrados na página!")
    else:
        print("\n⚠ Alguns elementos estão faltando")
else:
    print(f"✗ Erro ao carregar página: {response.status_code}")
