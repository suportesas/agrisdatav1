#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para conceder automaticamente a permissão de ver estoque de outras fazendas
a todos os administradores existentes no sistema.

Execução: python setup_admin_permissions.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from cadastros.models import Fazenda
from usuarios.models import Usuario

print("=" * 80)
print("SETUP DE PERMISSOES PARA ADMINISTRADORES")
print("=" * 80)

# Busca a permissão
try:
    content_type = ContentType.objects.get_for_model(Fazenda)
    permission = Permission.objects.get(
        content_type=content_type,
        codename='view_other_fazendas_estoque'
    )
    print("\n[OK] Permissao encontrada: {}".format(permission))
except Permission.DoesNotExist:
    print("\n[ERRO] Permissao 'view_other_fazendas_estoque' nao encontrada!")
    print("Execute a migracao: python manage.py migrate cadastros")
    exit(1)

# Busca todos os admins
admins = Usuario.objects.filter(
    is_superuser=True
) | Usuario.objects.filter(
    is_staff=True
) | Usuario.objects.filter(
    tipo='ADMIN'
)

admins = admins.distinct()

print("\nAdministradores encontrados: {}".format(admins.count()))

# Concede a permissão a cada admin
count = 0
for admin in admins:
    if admin.user_permissions.filter(codename='view_other_fazendas_estoque').exists():
        print("  --> {}: ja possui a permissao".format(admin.email))
    else:
        admin.user_permissions.add(permission)
        print("  [OK] {}: permissao concedida".format(admin.email))
        count += 1

print("\n" + "=" * 80)
print("Resumo: {} permissoes concedidas com sucesso!".format(count))
print("=" * 80 + "\n")

print("[OK] SETUP CONCLUIDO!")
print("\nAGORA:")
print("  * Todos os administradores podem escolher fazendas no estoque")
print("  * Novos admins receberao a permissao automaticamente (signal)")
print("  * Outros usuarios precisam da permissao atribuida via Roles")
