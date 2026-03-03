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
from django.contrib.auth import get_user_model

User = get_user_model()

# Buscar um usuário para testar
try:
    user = User.objects.first()
    if user:
        print(f"✓ Usuário encontrado: {user.username}")
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
                for unit in unidades:
                    print(f"    - ID {unit['id']}: {unit['nome']} ({unit['sigla']})")
            else:
                print(f"\n✗ Erro: {data.get('error')}")
        except Exception as e:
            print(f"✗ Erro ao parsear JSON: {e}")
            print(f"Response text: {response.text}")
    else:
        print("✗ Nenhum usuário encontrado no banco de dados")
        print("\nVocê pode criar um usuário e empresa executando:")
        print("  python manage.py shell")
        print("  from usuarios.models import Usuario")
        print("  from cadastros.models import Empresa")
        print("  empresa = Empresa.objects.create(nome='Test')")
        print("  user = Usuario.objects.create_user(username='test', password='test', empresa=empresa)")
except Exception as e:
    print(f"✗ Erro: {e}")
    import traceback
    traceback.print_exc()
