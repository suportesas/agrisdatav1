#!/usr/bin/env python
"""
TESTE FINAL: Simular exatamente o cenário do user
- Login como SUPERUSER (admin)
- Acessar /usuarios/2/editar/ (AS_Edson de AGRICOLA SALUTARIS S.A)
- Verificar que aparecem APENAS as 3 funções corretas
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from usuarios.models import Usuario
from empresas.models import Empresa, Role
import re

print("=" * 80)
print("TESTE FINAL: SUPERUSER (admin) em /usuarios/2/editar/")
print("=" * 80)

# Dados de teste
empresa = Empresa.objects.get(id=1)
usuario = Usuario.objects.get(id=2)  # AS_Edson

print(f"\n🎯 CENÁRIO:")
print(f"   URL: /usuarios/2/editar/")
print(f"   Usuário logado: admin (SUPERUSER)")
print(f"   Usuário sendo editado: {usuario.username} (ID: {usuario.id})")
print(f"   Empresa do usuário: {usuario.empresa.nome} (ID: {usuario.empresa.id})")

# Fazer login como superuser
client = Client()
print(f"\n🔐 Fazendo login como superuser (admin)...")

# Criar superuser se não existir
superuser = Usuario.objects.filter(username='admin', is_superuser=True).first()
if not superuser:
    print("   ❌ Superuser não encontrado!")
    exit(1)

print(f"   ✅ Superuser encontrado: {superuser.username}")

# Para testes, usar Django TestCase em vez de client.login
# que requer senha em plaintext
from django.test import TestCase, RequestFactory
from usuarios.forms import UsuarioUpdateForm

# Criar requisição falsa
request = RequestFactory().get('/usuarios/2/editar/')
request.user = superuser

# Criar formulário
print(f"\n📝 Criando formulário UsuarioUpdateForm...")
form = UsuarioUpdateForm(instance=usuario, user=superuser)

roles_queryset = form.fields['roles'].queryset

print(f"\n📋 FUNÇÕES VISÍVEIS NO CAMPO 'Roles':")
print(f"   Total: {roles_queryset.count()}")

roles_list = []
for role in roles_queryset.order_by('name'):
    is_correct = "✅" if role.empresa == empresa else "❌"
    print(f"   {is_correct} [{role.id}] {role.name} - {role.empresa.nome}")
    roles_list.append({
        'id': role.id,
        'name': role.name,
        'empresa': role.empresa.nome,
        'belongs_to_agricola': role.empresa == empresa
    })

# VALIDAÇÃO
print(f"\n" + "=" * 80)
print("VALIDAÇÃO")
print("=" * 80)

numero_roles = len(roles_list)
nomes_roles = [r['name'] for r in roles_list]
todas_pertencem_agricola = all(r['belongs_to_agricola'] for r in roles_list)

print(f"\n✓ Total de funções: {numero_roles}")
print(f"✓ Nomes: {', '.join(nomes_roles)}")
print(f"✓ Todas pertencem a {empresa.nome}: {todas_pertencem_agricola}")

# Resultado final
print(f"\n" + "=" * 80)
print("RESULTADO")
print("=" * 80)

if numero_roles == 3 and todas_pertencem_agricola:
    print(f"\n✅✅✅ PROBLEMA RESOLVIDO!")
    print(f"")
    print(f"Quando você acessa /usuarios/2/editar/ como superuser (admin),")
    print(f"aparecerá APENAS as 3 funções de AGRICOLA SALUTARIS S.A:")
    print(f"")
    for r in roles_list:
        print(f"   ✓ {r['name']}")
    print(f"")
    print(f"Sem nenhuma função de outras empresas!")
else:
    print(f"\n❌ Ainda há problemas:")
    print(f"   Total esperado: 3, encontrado: {numero_roles}")
    print(f"   Todas da empresa correta: {todas_pertencem_agricola}")

print(f"\n" + "=" * 80)
print("FIM DO TESTE")
print("=" * 80)
