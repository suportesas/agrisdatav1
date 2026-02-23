#!/usr/bin/env python
"""
Simula o acesso de um admin de empresa ao formulário de criação de usuário
Reproduz o que o usuário VÊ no navegador
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioCreateForm

print("=" * 80)
print("SIMULAÇÃO: O Que Um Admin de Empresa Vê no Formulário de Criar Usuário")
print("=" * 80)

# Limpar dados de teste anteriores
Empresa.objects.filter(cnpj__startswith='33').delete()

# Criar 2 empresas novamente
emp1 = Empresa.objects.create(nome='Empresa Simulação 1', cnpj='33345678000001', ativa=True)
emp2 = Empresa.objects.create(nome='Empresa Simulação 2', cnpj='33345678000002', ativa=True)

print(f"\n✅ Empresa 1: {emp1.nome}")
print(f"✅ Empresa 2: {emp2.nome}")

# Criar roles para cada empresa
print("\n" + "=" * 80)
print("Criando Funções Personalizadas para Cada Empresa...")
print("=" * 80)

roles_emp1 = [
    ('Gerente Empresa 1', 'Gerente da Empresa 1'),
    ('Supervisor Empresa 1', 'Supervisor da Empresa 1'),
    ('Operador Empresa 1', 'Operador da Empresa 1'),
]

roles_emp2 = [
    ('Gerente Empresa 2', 'Gerente da Empresa 2'),
    ('Supervisor Empresa 2', 'Supervisor da Empresa 2'),
    ('Operador Empresa 2', 'Operador da Empresa 2'),
]

for name, desc in roles_emp1:
    Role.objects.get_or_create(
        name=name,
        empresa=emp1,
        defaults={'description': desc}
    )

for name, desc in roles_emp2:
    Role.objects.get_or_create(
        name=name,
        empresa=emp2,
        defaults={'description': desc}
    )

print(f"✅ Empresa 1 tem {emp1.roles.count()} funções")
print(f"✅ Empresa 2 tem {emp2.roles.count()} funções")

# Criar admins
try:
    admin_sim_emp1 = Usuario.objects.get(username='admin_sim_emp1')
except:
    admin_sim_emp1 = Usuario.objects.create_user(
        username='admin_sim_emp1',
        email='admin_sim1@emp1.com',
        password='123456',
        empresa=emp1,
        tipo='ADMIN',
        is_staff=True
    )

try:
    admin_sim_emp2 = Usuario.objects.get(username='admin_sim_emp2')
except:
    admin_sim_emp2 = Usuario.objects.create_user(
        username='admin_sim_emp2',
        email='admin_sim2@emp2.com',
        password='123456',
        empresa=emp2,
        tipo='ADMIN',
        is_staff=True
    )

# TESTE 1: Admin de Empresa 1
print("\n" + "=" * 80)
print("TESTE 1: Admin da Empresa 1 abre formulário de criar usuário")
print("=" * 80)

factory = RequestFactory()
request1 = factory.get('/usuarios/novo/')
request1.user = admin_sim_emp1

form1 = UsuarioCreateForm(user=admin_sim_emp1)

print(f"\n👤 Usuário logado: {admin_sim_emp1.username}")
print(f"🏢 Empresa: {admin_sim_emp1.empresa.nome}")

print(f"\n📋 CAMPO EMPRESA:")
print(f"   Empresa selecionada: {form1.fields['empresa'].initial}")
print(f"   Empresa desabilitada (disabled): {form1.fields['empresa'].disabled}")
print(f"   Opções disponíveis: {[emp.nome for emp in form1.fields['empresa'].queryset]}")

print(f"\n📋 CAMPO FUNÇÕES (Roles):")
roles_list1 = list(form1.fields['roles'].queryset.values_list('name', 'empresa__nome'))
print(f"   Total de funções: {len(roles_list1)}")
for role_name, emp_name in roles_list1:
    print(f"      ✓ {role_name} (Empresa: {emp_name})")

print(f"\n🔍 VALIDAÇÃO:")
has_emp2_roles = any(emp_name == emp2.nome for _, emp_name in roles_list1)
if has_emp2_roles:
    print(f"   ❌ PROBLEMA: Admin Empresa 1 vendo funções de Empresa 2!")
else:
    print(f"   ✅ CORRETO: Admin Empresa 1 vendo apenas funções de Empresa 1!")

# TESTE 2: Admin de Empresa 2
print("\n" + "=" * 80)
print("TESTE 2: Admin da Empresa 2 abre formulário de criar usuário")
print("=" * 80)

form2 = UsuarioCreateForm(user=admin_sim_emp2)

print(f"\n👤 Usuário logado: {admin_sim_emp2.username}")
print(f"🏢 Empresa: {admin_sim_emp2.empresa.nome}")

print(f"\n📋 CAMPO EMPRESA:")
print(f"   Empresa selecionada: {form2.fields['empresa'].initial}")
print(f"   Empresa desabilitada (disabled): {form2.fields['empresa'].disabled}")
print(f"   Opções disponíveis: {[emp.nome for emp in form2.fields['empresa'].queryset]}")

print(f"\n📋 CAMPO FUNÇÕES (Roles):")
roles_list2 = list(form2.fields['roles'].queryset.values_list('name', 'empresa__nome'))
print(f"   Total de funções: {len(roles_list2)}")
for role_name, emp_name in roles_list2:
    print(f"      ✓ {role_name} (Empresa: {emp_name})")

print(f"\n🔍 VALIDAÇÃO:")
has_emp1_roles = any(emp_name == emp1.nome for _, emp_name in roles_list2)
if has_emp1_roles:
    print(f"   ❌ PROBLEMA: Admin Empresa 2 vendo funções de Empresa 1!")
else:
    print(f"   ✅ CORRETO: Admin Empresa 2 vendo apenas funções de Empresa 2!")

# RESUMO
print("\n" + "=" * 80)
print("RESUMO FINAL")
print("=" * 80)

if not has_emp2_roles and not has_emp1_roles:
    print("\n✅✅✅ TUDO FUNCIONANDO CORRETAMENTE!")
    print("    - Admin de Empresa 1 vê apenas suas funções")
    print("    - Admin de Empresa 2 vê apenas suas funções")
else:
    print("\n❌ PROBLEMA ENCONTRADO!")
    if has_emp2_roles:
        print(f"    - Admin Empresa 1 ainda consegue ver funções de Empresa 2")
    if has_emp1_roles:
        print(f"    - Admin Empresa 2 ainda consegue ver funções de Empresa 1")
