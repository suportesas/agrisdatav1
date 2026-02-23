#!/usr/bin/env python
"""
Diagnosticar o problema de Funções na edição de usuário
Listar todas as roles de "Agricola Salutaris S.A"
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from empresas.models import Empresa, Role
from usuarios.models import Usuario

print("=" * 80)
print("DIAGNÓSTICO: Funções de 'Agricola Salutaris S.A'")
print("=" * 80)

# Buscar a empresa
try:
    empresa = Empresa.objects.get(nome__icontains='Agricola Salutaris')
    print(f"\n✅ Empresa encontrada: {empresa.nome}")
    print(f"   CNPJ: {empresa.cnpj}")
    print(f"   ID: {empresa.id}")
except Empresa.DoesNotExist:
    print("\n❌ Empresa 'Agricola Salutaris S.A' não encontrada!")
    print("\nEmpresas no sistema:")
    for emp in Empresa.objects.all():
        print(f"   - {emp.nome} (ID: {emp.id})")
    exit(1)

# Listar TODAS as roles de Almoxarife no sistema
print("\n" + "=" * 80)
print("ROLES CHAMADAS 'Almoxarife' EM TODAS AS EMPRESAS")
print("=" * 80)

almoxarife_roles = Role.objects.filter(name='Almoxarife')
print(f"Total encontrado: {almoxarife_roles.count()}")

for role in almoxarife_roles:
    is_our_company = "✅" if role.empresa == empresa else "❌"
    print(f"\n{is_our_company} ID: {role.id}")
    print(f"   Nome: {role.name}")
    print(f"   Empresa: {role.empresa.nome} (ID: {role.empresa.id})")
    print(f"   Descrição: {role.description}")

# Listar TODAS as funções de "Agricola Salutaris S.A"
print("\n" + "=" * 80)
print(f"TODAS AS FUNÇÕES DE '{empresa.nome}'")
print("=" * 80)

roles_da_empresa = empresa.roles.all()
print(f"Total: {roles_da_empresa.count()}")

for role in roles_da_empresa:
    print(f"\n   ✓ [{role.id}] {role.name}")
    print(f"      Descrição: {role.description}")

# Listar TODAS as funções do sistema
print("\n" + "=" * 80)
print("TODAS AS FUNÇÕES NO SISTEMA (POR EMPRESA)")
print("=" * 80)

for emp in Empresa.objects.all():
    roles_count = emp.roles.count()
    print(f"\n{emp.nome} (ID: {emp.id}): {roles_count} funções")
    for role in emp.roles.all():
        print(f"      - {role.name}")

# Verificar o usuário que está sendo editado (ID=2)
print("\n" + "=" * 80)
print("USUÁRIO ID=2 (SENDO EDITADO)")
print("=" * 80)

try:
    usuario = Usuario.objects.get(id=2)
    print(f"\n✅ Usuário encontrado: {usuario.username}")
    print(f"   Nome completo: {usuario.get_full_name()}")
    print(f"   Email: {usuario.email}")
    print(f"   Empresa: {usuario.empresa.nome if usuario.empresa else 'NENHUMA (Superuser)'}")
    print(f"   Tipo: {usuario.tipo}")
    print(f"   Roles atribuídas: {usuario.roles.count()}")
    for role in usuario.roles.all():
        print(f"      - {role.name} (Empresa: {role.empresa.nome})")
except Usuario.DoesNotExist:
    print("\n❌ Usuário ID=2 não encontrado!")

print("\n" + "=" * 80)
