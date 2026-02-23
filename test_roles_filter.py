#!/usr/bin/env python
"""
Testa se o campo 'Funções' está filtrando corretamente por empresa
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioCreateForm

# Criar 2 empresas de teste
print("=" * 60)
print("TESTE: Filtro de Funções por Empresa")
print("=" * 60)

# Empresa 1
emp1, created = Empresa.objects.get_or_create(
    cnpj='12345678000001',
    defaults={'nome': 'Empresa 1', 'ativa': True}
)

# Empresa 2
emp2, created = Empresa.objects.get_or_create(
    cnpj='12345678000002',
    defaults={'nome': 'Empresa 2', 'ativa': True}
)

print(f"\n✅ Empresa 1: {emp1.nome} (CNPJ: {emp1.cnpj})")
print(f"✅ Empresa 2: {emp2.nome} (CNPJ: {emp2.cnpj})")

# Criar roles para cada empresa
print("\n" + "=" * 60)
print("Criando Funções...")
print("=" * 60)

role_emp1_1, _ = Role.objects.get_or_create(
    name='Admin Empresa 1',
    empresa=emp1,
    defaults={'description': 'Administrador da Empresa 1'}
)

role_emp1_2, _ = Role.objects.get_or_create(
    name='Operador Empresa 1',
    empresa=emp1,
    defaults={'description': 'Operador da Empresa 1'}
)

role_emp2_1, _ = Role.objects.get_or_create(
    name='Admin Empresa 2',
    empresa=emp2,
    defaults={'description': 'Administrador da Empresa 2'}
)

role_emp2_2, _ = Role.objects.get_or_create(
    name='Operador Empresa 2',
    empresa=emp2,
    defaults={'description': 'Operador da Empresa 2'}
)

print(f"✅ Empresa 1: {role_emp1_1.name}, {role_emp1_2.name}")
print(f"✅ Empresa 2: {role_emp2_1.name}, {role_emp2_2.name}")

# Criar admin de cada empresa
print("\n" + "=" * 60)
print("Criando Usuarios Para Teste...")
print("=" * 60)

try:
    admin_emp1 = Usuario.objects.get(username='admin_emp1')
except:
    admin_emp1 = Usuario.objects.create_user(
        username='admin_emp1',
        email='admin1@emp1.com',
        password='123456',
        empresa=emp1,
        tipo='ADMIN',
        is_staff=True
    )

try:
    admin_emp2 = Usuario.objects.get(username='admin_emp2')
except:
    admin_emp2 = Usuario.objects.create_user(
        username='admin_emp2',
        email='admin2@emp2.com',
        password='123456',
        empresa=emp2,
        tipo='ADMIN',
        is_staff=True
    )

print(f"✅ Admin Empresa 1: {admin_emp1.username}")
print(f"✅ Admin Empresa 2: {admin_emp2.username}")

# TESTE 1: Admin da Empresa 1 criando usuário
print("\n" + "=" * 60)
print("TESTE 1: Admin da Empresa 1 criando novo usuário")
print("=" * 60)

form1 = UsuarioCreateForm(user=admin_emp1)
roles_disponiveis_admin1 = list(form1.fields['roles'].queryset.values_list('name', flat=True))

print(f"\n👤 Usuário logado: {admin_emp1.username} (Empresa: {admin_emp1.empresa.nome})")
print(f"📋 Funções disponíveis:")
for role in roles_disponiveis_admin1:
    print(f"   - {role}")

if 'Admin Empresa 2' in roles_disponiveis_admin1 or 'Operador Empresa 2' in roles_disponiveis_admin1:
    print("\n❌ ERRO: Admin de Empresa 1 vendo funções de Empresa 2!")
else:
    print("\n✅ CORRETO: Admin de Empresa 1 vendo apenas funções de Empresa 1")

# TESTE 2: Admin da Empresa 2 criando usuário
print("\n" + "=" * 60)
print("TESTE 2: Admin da Empresa 2 criando novo usuário")
print("=" * 60)

form2 = UsuarioCreateForm(user=admin_emp2)
roles_disponiveis_admin2 = list(form2.fields['roles'].queryset.values_list('name', flat=True))

print(f"\n👤 Usuário logado: {admin_emp2.username} (Empresa: {admin_emp2.empresa.nome})")
print(f"📋 Funções disponíveis:")
for role in roles_disponiveis_admin2:
    print(f"   - {role}")

if 'Admin Empresa 1' in roles_disponiveis_admin2 or 'Operador Empresa 1' in roles_disponiveis_admin2:
    print("\n❌ ERRO: Admin de Empresa 2 vendo funções de Empresa 1!")
else:
    print("\n✅ CORRETO: Admin de Empresa 2 vendo apenas funções de Empresa 2")

# TESTE 3: Superuser criando usuário
print("\n" + "=" * 60)
print("TESTE 3: Superuser criando novo usuário")
print("=" * 60)

superuser = Usuario.objects.filter(is_superuser=True).first()
if superuser:
    form3 = UsuarioCreateForm(user=superuser)
    roles_disponiveis_super = list(form3.fields['roles'].queryset.values_list('name', flat=True))
    
    print(f"\n👤 Usuário logado: {superuser.username} (Superuser)")
    print(f"📋 Funções disponíveis (TOTAL):")
    for role in roles_disponiveis_super:
        print(f"   - {role}")
    
    if len(roles_disponiveis_super) == 4:
        print("\n✅ CORRETO: Superuser vendo TODAS as funções")
    else:
        print(f"\n⚠️ AVISO: Superuser vendo {len(roles_disponiveis_super)} funções (esperado 4)")
else:
    print("❌ Nenhum superuser disponível")

print("\n" + "=" * 60)
print("FIM DO TESTE")
print("=" * 60)
