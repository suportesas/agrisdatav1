#!/usr/bin/env python
"""
Script para testar o novo endpoint /api/empresa/unidades/ com um usuário que tem empresa
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from cadastros.models import Empresa

User = get_user_model()

# Buscar uma empresa com unidades
print("=== Analisando dados ===")
print("\nEmpresas:")
for empresa in Empresa.objects.all()[:3]:
    print(f"  - ID {empresa.id}: {empresa.nome}")
    unidades = empresa.unidade_medida_set.all()
    print(f"    Unidades de medida: {unidades.count()}")

# Buscar um usuário com empresa
print("\nUsuários:")
usuarios_com_empresa = User.objects.filter(empresa__isnull=False).distinct()[:3]
for user in usuarios_com_empresa:
    print(f"  - {user.username} (Empresa: {user.empresa})")

# Usar o primeiro usuário com empresa
user = usuarios_com_empresa.first()
if user:
    print(f"\n✓ Testando com usuário: {user.username}")
    print(f"  Empresa: {user.empresa}")
    
    # Criar cliente autenticado
    client = Client()
    client.force_login(user)
    
    # Testar o novo endpoint
    print("\n=== Testando GET /compras/api/empresa/unidades/ ===")
    response = client.get('/compras/api/empresa/unidades/')
    print(f"Status Code: {response.status_code}")
    
    import json
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        if data.get('success'):
            unidades = data.get('unidades', [])
            print(f"\n✓ Endpoint funcionando corretamente!")
            print(f"  Total de unidades: {len(unidades)}")
            for unit in unidades[:5]:
                print(f"    - ID {unit['id']}: {unit['nome']} ({unit['sigla']})")
        else:
            print(f"\n✗ Erro: {data.get('error')}")
    except Exception as e:
        print(f"✗ Erro ao parsear JSON: {e}")
        print(f"Response text: {response.text}")
else:
    print("\n✗ Nenhum usuário com empresa encontrado no banco de dados")
