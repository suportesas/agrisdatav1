#!/usr/bin/env python
"""
Diagnosticar: Por que ainda aparecem funções de outras empresas?
Simular a requisição HTTP completa como se fosse vindo do navegador
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Empresa, Role

print("=" * 80)
print("DIAGNOSTIC: Por que funções de outras empresas ainda aparecem?")
print("=" * 80)

# Encontrar empresa e usuário
empresa = Empresa.objects.get(id=1)
usuario = Usuario.objects.get(id=2)

print(f"\n👤 Usuário sendo editado: {usuario.username} (ID: 2)")
print(f"   Empresa: {usuario.empresa.nome} (ID: {usuario.empresa.id})")

# Encontrar ou criar um admin de AGRICOLA SALUTARIS
try:
    admin = Usuario.objects.get(username='admin_agricola')
except:
    admin = Usuario.objects.create_user(
        username='admin_agricola',
        email='admin@agricola.com',
        password='123456',
        empresa=empresa,
        tipo='ADMIN',
        is_staff=True
    )

print(f"\n👤 Admin logado: {admin.username}")
print(f"   Empresa: {admin.empresa.nome} (ID: {admin.empresa.id})")

# Usar Django Test Client para simular requisição HTTP real
client = Client()

# Fazer login
login_success = client.login(username='admin_agricola', password='123456')
print(f"\n🔐 Login realizado: {login_success}")

# Acessar página de edição
print("\n" + "=" * 80)
print("ACESSANDO: /usuarios/2/editar/")
print("=" * 80)

response = client.get('/usuarios/2/editar/')

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    # Extrair o HTML da resposta
    html_content = response.content.decode('utf-8')
    
    # Procurar por todas as opções de roles
    import re
    
    # Padrão para encontrar <option> no campo roles
    pattern = r'<option value="(\d+)"[^>]*>([^<]+)</option>'
    options = re.findall(pattern, html_content)
    
    print(f"\n📋 FUNÇÕES ENCONTRADAS NO FORMULÁRIO HTML:")
    print(f"   Total: {len(options)}")
    
    for role_id, role_name in options:
        # Verificar a qual empresa essa role pertence
        try:
            role = Role.objects.get(id=int(role_id))
            is_correct = "✅" if role.empresa == empresa else "❌"
            print(f"   {is_correct} [{role_id}] {role_name} (Empresa: {role.empresa.nome})")
        except Role.DoesNotExist:
            print(f"   ⚠️  [{role_id}] {role_name} (Role não encontrada!)")
    
    # Contar roles por empresa
    print(f"\n📊 RESUMO:")
    from collections import defaultdict
    roles_por_empresa = defaultdict(int)
    
    for role_id, role_name in options:
        try:
            role = Role.objects.get(id=int(role_id))
            roles_por_empresa[role.empresa.nome] += 1
        except Role.DoesNotExist:
            roles_por_empresa['[UNKNOWN]'] += 1
    
    for emp_name, count in sorted(roles_por_empresa.items()):
        symbol = "✅" if emp_name == empresa.nome else "❌"
        print(f"   {symbol} {emp_name}: {count} roles")
    
    # Validação
    print(f"\n🔍 VALIDAÇÃO:")
    tem_roles_erradas = any(emp_name != empresa.nome for emp_name in roles_por_empresa.keys())
    
    if tem_roles_erradas:
        print(f"   ❌ PROBLEMA! Aparecem funções de outras empresas no HTML!")
    else:
        print(f"   ✅ CORRETO! Só aparecem funções de {empresa.nome}!")

else:
    print(f"❌ Erro ao acessar página: {response.status_code}")

print("\n" + "=" * 80)
