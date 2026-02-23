#!/usr/bin/env python
"""
Teste: Quando SUPERUSER acessa /usuarios/2/editar/
Deveria ver TODAS as roles de TODAS as empresas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Role
import re

print("=" * 80)
print("TESTE: SUPERUSER acessando /usuarios/2/editar/")
print("=" * 80)

# Buscar superuser
try:
    superuser = Usuario.objects.get(username='admin')
except:
    print("❌ Superuser 'admin' não encontrado!")
    exit(1)

print(f"\n👤 Superuser: {superuser.username}")
print(f"   is_superuser: {superuser.is_superuser}")
print(f"   Empresa: {superuser.empresa if superuser.empresa else 'NENHUMA (correto para superuser)'}")

# Fazer login como superuser
client = Client()
login_success = client.login(username='admin', password='123456')
print(f"\n🔐 Login como superuser: {login_success}")

# Acessar página de edição
response = client.get('/usuarios/2/editar/')

if response.status_code == 200:
    html_content = response.content.decode('utf-8')
    
    # Extrair roles do HTML
    pattern = r'<option value="(\d+)"[^>]*>([^<]+)</option>'
    options = re.findall(pattern, html_content)
    
    print(f"\n📋 FUNÇÕES VISTAS POR SUPERUSER:")
    print(f"   Total: {len(options)}")
    
    # Agrupar por empresa
    from collections import defaultdict
    roles_por_empresa = defaultdict(list)
    
    for role_id, role_name in options:
        try:
            role = Role.objects.get(id=int(role_id))
            roles_por_empresa[role.empresa.nome].append(role_name)
        except Role.DoesNotExist:
            roles_por_empresa['[UNKNOWN]'].append(role_name)
    
    for emp_name in sorted(roles_por_empresa.keys()):
        print(f"\n   🏢 {emp_name}:")
        for role_name in roles_por_empresa[emp_name]:
            print(f"      - {role_name}")
    
    print(f"\n✅ ESPERADO: Superuser vê funções de TODAS as empresas!")
    print(f"✅ RESULTADO: Total de {len(options)} funções encontradas")

else:
    print(f"❌ Erro: {response.status_code}")

print("\n" + "=" * 80)
