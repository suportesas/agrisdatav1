#!/usr/bin/env python
"""
Limpar as 6 funções padrão de AGRICOLA SALUTARIS S.A
Criar apenas 3 funções personalizadas: Admin, Gerente, Operador
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from empresas.models import Empresa, Role

print("=" * 80)
print("LIMPEZA: Remover 6 funções padrão e criar 3 personalizadas")
print("=" * 80)

# Buscar empresa
empresa = Empresa.objects.get(id=1)
print(f"\n🏢 Empresa: {empresa.nome}")

# REMOVER as 6 funções padrão
print("\n" + "=" * 80)
print("REMOVENDO 6 FUNÇÕES PADRÃO...")
print("=" * 80)

roles_padrao = ['Almoxarife', 'Financeiro', 'Gerente', 'Operacional do Campo', 'Proprietário', 'Vendedor']

for role_name in roles_padrao:
    try:
        role = Role.objects.get(empresa=empresa, name=role_name)
        print(f"\n❌ Removendo: {role_name} (ID: {role.id})")
        role.delete()
        print(f"   ✓ Deletado")
    except Role.DoesNotExist:
        print(f"\n⚠️  Não encontrado: {role_name}")

# CRIAR as 3 funções personalizadas
print("\n" + "=" * 80)
print("CRIANDO 3 FUNÇÕES PERSONALIZADAS...")
print("=" * 80)

roles_novas = [
    ('Admin', 'Administrador da empresa - acesso total'),
    ('Gerente', 'Gerente - acesso a operações principais'),
    ('Operador', 'Operador - acesso limitado a funcionalidades básicas'),
]

for name, descricao in roles_novas:
    role, created = Role.objects.get_or_create(
        name=name,
        empresa=empresa,
        defaults={'description': descricao}
    )
    
    if created:
        print(f"\n✅ Criada: {name} (ID: {role.id})")
        print(f"   Descrição: {descricao}")
    else:
        print(f"\n⚠️  Já existe: {name} (ID: {role.id})")

# VERIFICAÇÃO FINAL
print("\n" + "=" * 80)
print("VERIFICAÇÃO FINAL")
print("=" * 80)

roles_finais = empresa.roles.all()
print(f"\n✅ Total de funções em {empresa.nome}: {roles_finais.count()}")

for role in roles_finais:
    print(f"   - {role.name} (ID: {role.id})")

print("\n✅ CONCLUÍDO COM SUCESSO!")
print("=" * 80)
