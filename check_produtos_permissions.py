#!/usr/bin/env python
"""
Script para verificar permissões do app produtos
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

print("=" * 60)
print("VERIFICANDO PERMISSÕES DO APP PRODUTOS")
print("=" * 60)

# Lista todos os models do app produtos
ct_produtos = ContentType.objects.filter(app_label='produtos')

if not ct_produtos.exists():
    print("\n❌ NENHUM ContentType encontrado para o app 'produtos'")
    print("   As migrações podem não ter sido aplicadas corretamente.")
else:
    print(f"\n✅ {ct_produtos.count()} models encontrados no app produtos:\n")
    
    for ct in ct_produtos:
        print(f"📦 Model: {ct.app_label}.{ct.model} ({ct.model_class()._meta.verbose_name})")
        
        # Lista permissões deste model
        perms = Permission.objects.filter(content_type=ct)
        print(f"   Permissões ({perms.count()}):")
        for p in perms:
            print(f"      • {p.codename} - {p.name}")
        print()

print("=" * 60)

# Verifica na view de roles
print("\nVERIFICANDO APP_LABELS na view de empresas:")
from empresas import views
import inspect

source = inspect.getsource(views.role_permissions_ajax)
if "'produtos'" in source:
    print("✅ 'produtos' está no APP_LABELS")
else:
    print("❌ 'produtos' NÃO está no APP_LABELS")
    print("   RECOMENDAÇÃO: Adicionar 'produtos': 'Produtos' no dicionário APP_LABELS")

print("=" * 60)
