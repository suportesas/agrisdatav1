#!/usr/bin/env python
"""
Teste: Simular a edição do usuário ID=2 (AS_Edson)
Ver qual formulário está sendo usado e quais roles aparecem
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioUpdateForm

print("=" * 80)
print("TESTE: Editar Usuário ID=2 (AS_Edson) da AGRICOLA SALUTARIS S.A")
print("=" * 80)

# Buscar empresa e usuário
empresa = Empresa.objects.get(id=1)
usuario = Usuario.objects.get(id=2)

print(f"\n👤 Usuário: {usuario.username}")
print(f"   Nome: {usuario.get_full_name()}")
print(f"   Empresa: {usuario.empresa.nome}")
print(f"   ID da Empresa: {usuario.empresa.id}")

# Simular a edição ("alguém logado como admin de AGRICOLA SALUTARIS")
# O formulário assume que o usuário que está editando é um admin da empresa

# Criar um usuario admin de AGRICOLA SALUTARIS como se estivesse logado

try:
    admin_agricola = Usuario.objects.get(username='admin_agricola')
except:
    admin_agricola = Usuario.objects.create_user(
        username='admin_agricola',
        email='admin@agricola.com',
        password='123456',
        empresa=empresa,
        tipo='ADMIN',
        is_staff=True
    )

print(f"\n👤 Usuário logado (quem está editando): {admin_agricola.username}")
print(f"   Empresa: {admin_agricola.empresa.nome}")
print(f"   ID da Empresa: {admin_agricola.empresa.id}")

# Criar formulário de edição
print("\n" + "=" * 80)
print("CRIANDO FORMULÁRIO DE EDIÇÃO (UsuarioUpdateForm)")
print("=" * 80)

form = UsuarioUpdateForm(instance=usuario, user=admin_agricola)

print(f"\n📋 CAMPO ROLES NO FORMULÁRIO:")
roles_queryset = form.fields['roles'].queryset
print(f"   Total de roles na queryset: {roles_queryset.count()}")

# Listar todas as roles
print(f"\n📝 ROLES DISPONÍVEIS:")
for role in roles_queryset.order_by('name', 'empresa__nome'):
    empresa_name = role.empresa.nome
    empresa_id = role.empresa.id
    symbol = "✅" if role.empresa.id == empresa.id else "❌"
    print(f"      {symbol} [{role.id}] {role.name} (Empresa: {empresa_name} - ID: {empresa_id})")

# Contar roles por empresa
print(f"\n📊 RESUMO POR EMPRESA:")

roles_por_empresa = {}
for role in roles_queryset:
    emp_name = role.empresa.nome
    if emp_name not in roles_por_empresa:
        roles_por_empresa[emp_name] = 0
    roles_por_empresa[emp_name] += 1

for emp_name, count in sorted(roles_por_empresa.items()):
    symbol = "✅" if emp_name == empresa.nome else "❌"
    print(f"      {symbol} {emp_name}: {count} roles")

# Validação
print(f"\n🔍 VALIDAÇÃO:")
tem_roles_erradas = False
for role in roles_queryset:
    if role.empresa != empresa:
        tem_roles_erradas = True
        break

if tem_roles_erradas:
    print(f"   ❌ PROBLEMA! Admin da {empresa.nome} consegue ver roles de outras empresas!")
else:
    print(f"   ✅ CORRETO! Admin só vê roles de {empresa.nome}!")

print("\n" + "=" * 80)
