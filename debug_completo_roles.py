#!/usr/bin/env python
"""
Teste COMPLETO: Debug detalhado por que roles de outras empresas aparecem
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioUpdateForm

print("=" * 80)
print("DEBUG COMPLETO: Por que roles de outras empresas aparecem?")
print("=" * 80)

# Dados
empresa = Empresa.objects.get(id=1)
usuario = Usuario.objects.get(id=2)

# Encontrar ou criar admin de AGRICOLA SALUTARIS
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

print(f"\n👤 Admin (quem está editando):")
print(f"   Username: {admin.username}")
print(f"   is_superuser: {admin.is_superuser}")
print(f"   is_staff: {admin.is_staff}")
print(f"   empresa: {admin.empresa}")
print(f"   empresa.id: {admin.empresa.id if admin.empresa else None}")
print(f"   tipo: {admin.tipo}")

print(f"\n👤 Usuario sendo editado (ID=2):")
print(f"   Username: {usuario.username}")
print(f"   empresa: {usuario.empresa}")
print(f"   empresa.id: {usuario.empresa.id if usuario.empresa else None}")

# Testar as condições do formulário
print("\n" + "=" * 80)
print("ANALISANDO AS CONDIÇÕES DO FORMULÁRIO")
print("=" * 80)

print(f"\nCondição 1: self.user existe?")
print(f"   resultado: {admin is not None} ✅" if admin else "   resultado: False ❌")

print(f"\nCondição 2: not self.user.is_superuser?")
print(f"   admin.is_superuser = {admin.is_superuser}")
print(f"   not {admin.is_superuser} = {not admin.is_superuser}")
print(f"   resultado: {not admin.is_superuser} {'✅' if not admin.is_superuser else '❌'}")

print(f"\nCondição 3: self.user.empresa exists?")
print(f"   admin.empresa = {admin.empresa}")
print(f"   resultado: {bool(admin.empresa)} {'✅' if admin.empresa else '❌'}")

todas_condicoes_atendidas = (
    admin is not None and 
    not admin.is_superuser and 
    admin.empresa
)

print(f"\n🔍 TODAS AS 3 CONDIÇÕES:")
print(f"   {todas_condicoes_atendidas}")
if todas_condicoes_atendidas:
    print(f"   ✅ Deve filtrar por empresa: {admin.empresa.nome}")
else:
    print(f"   ❌ Vai mostrar TODAS as roles!")

# Testar o formulário
print("\n" + "=" * 80)
print("CRIANDO FORMULÁRIO COM user=admin")
print("=" * 80)

form = UsuarioUpdateForm(instance=usuario, user=admin)

print(f"\nQueryset de roles no formulário:")
roles_queryset = form.fields['roles'].queryset

print(f"   SQL: {roles_queryset.query}")
print(f"   Total: {roles_queryset.count()}")

# Listar todas as roles
print(f"\n📋 ROLES NA QUERYSET:")
for role in roles_queryset:
    is_correct_emp = "✅" if role.empresa == empresa else "❌"
    print(f"   {is_correct_emp} [{role.id}] {role.name} ({role.empresa.nome})")

# Contar por empresa
from collections import defaultdict
roles_por_emp = defaultdict(list)
for role in roles_queryset:
    roles_por_emp[role.empresa.nome].append(role.name)

print(f"\n📊 RESUMO POR EMPRESA:")
for emp_name in sorted(roles_por_emp.keys()):
    is_correct = "✅" if emp_name == empresa.nome else "❌"
    roles = roles_por_emp[emp_name]
    print(f"   {is_correct} {emp_name}: {', '.join(roles)}")

# Validação final
print(f"\n🔍 VALIDAÇÃO FINAL:")
problematico = any(emp_name != empresa.nome for emp_name in roles_por_emp.keys())

if problematico:
    print(f"   ❌ PROBLEMA CONFIRMADO!")
    print(f"   Admin vê funções de outras empresas!")
else:
    print(f"   ✅ CORRETO!")
    print(f"   Admin vê apenas funções de {empresa.nome}!")

print("\n" + "=" * 80)
