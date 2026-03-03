#!/usr/bin/env python
"""
Script para testar o novo endpoint /api/empresa/unidades/
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import Client
from usuarios.models import Usuario

# Buscar um usuário que tem uma empresa
user = Usuario.objects.filter(empresa__isnull=False).first()

if user:
    print(f"✓ Testando com usuário: {user}")
    print(f"  Empresa: {user.empresa}")
    print(f"  Unidades no banco: {user.empresa.unidades_medida.count()}")
    
    # Criar cliente autenticado
    client = Client()
    client.force_login(user, backend='django.contrib.auth.backends.ModelBackend')
    
    # Testar o novo endpoint
    print("\n=== Testando GET /compras/api/empresa/unidades/ ===")
    response = client.get('/compras/api/empresa/unidades/')
    print(f"Status Code: {response.status_code}")
    
    import json
    try:
        data = response.json()
        if data.get('success'):
            unidades = data.get('unidades', [])
            print(f"\n✓ Endpoint funcionando corretamente!")
            print(f"  Total de unidades retornadas: {len(unidades)}")
            for unit in unidades:
                print(f"    - ID {unit['id']}: {unit['nome']} ({unit.get('sigla', 'N/A')})")
        else:
            print(f"\n✗ Erro: {data.get('error')}")
    except Exception as e:
        print(f"✗ Erro ao parsear JSON: {e}")
        print(f"Response text: {response.text}")
else:
    print("✗ Nenhum usuário com empresa encontrado no banco de dados")
