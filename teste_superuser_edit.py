#!/usr/bin/env python
"""
Teste: SUPERUSER (admin) editando AS_Edson
Deve ver APENAS as 3 funções de AGRICOLA SALUTARIS S.A
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from usuarios.models import Usuario
from empresas.models import Empresa, Role
from usuarios.forms import UsuarioUpdateForm

print("=" * 80)
print("TESTE: SUPERUSER (admin) editando AS_Edson")
print("=" * 80)

# Dados
superuser = Usuario.objects.get(username='admin')
usuario = Usuario.objects.get(id=2)  # AS_Edson de AGRICOLA SALUTARIS S.A
empresa = Empresa.objects.get(id=1)

print(f"\n👤 SUPERUSER (quem está editando):")
print(f"   Username: {superuser.username}")
print(f"   is_superuser: {superuser.is_superuser}")
print(f"   empresa: {superuser.empresa}")

print(f"\n👤 USUARIO SENDO EDITADO:")
print(f"   Username: {usuario.username} (ID: {usuario.id})")
print(f"   Empresa: {usuario.empresa.nome} (ID: {usuario.empresa.id})")

# Criar formulário com superuser
form = UsuarioUpdateForm(instance=usuario, user=superuser)

roles_queryset = form.fields['roles'].queryset

print(f"\n📋 ROLES QUE O SUPERUSER VÊ:")
print(f"   Total: {roles_queryset.count()}")

for role in roles_queryset:
    is_correct = "✅" if role.empresa == empresa else "❌"
    print(f"   {is_correct} [{role.id}] {role.name} ({role.empresa.nome})")

# Validação
from collections import defaultdict
roles_por_empresa = defaultdict(list)
for role in roles_queryset:
    roles_por_empresa[role.empresa.nome].append(role.name)

print(f"\n📊 RESUMO:")
for emp_name in sorted(roles_por_empresa.keys()):
    is_correct = "✅" if emp_name == empresa.nome else "❌"
    roles = roles_por_empresa[emp_name]
    print(f"   {is_correct} {emp_name}: {', '.join(roles)}")

# Resultado
print(f"\n🔍 RESULTADO:")
if len(roles_queryset) == 3 and all(r.empresa == empresa for r in roles_queryset):
    print(f"   ✅ PERFEITO!")
    print(f"   Superuser vê apenas as 3 funções de {empresa.nome}")
else:
    print(f"   ❌ PROBLEMA!")
    print(f"   Superuser está vendo funções extras")

print("\n" + "=" * 80)
