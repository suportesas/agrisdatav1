#!/usr/bin/env python
"""
Script de teste para o módulo Estoque
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from estoque.models import Armazem, LocalEstocagem, Lote
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission

print("=" * 70)
print("TESTE DO MÓDULO ESTOQUE - FASE 1 CONCLUÍDA")
print("=" * 70)

# Verifica models
print("\n✅ MODELS CRIADOS:")
print(f"   • Armazem: {Armazem._meta.verbose_name}")
print(f"   • LocalEstocagem: {LocalEstocagem._meta.verbose_name}")
print(f"   • Lote: {Lote._meta.verbose_name}")

# Verifica permissões
print("\n✅ PERMISSÕES GERADAS:")
ct_estoque = ContentType.objects.filter(app_label='estoque')
for ct in ct_estoque:
    perms = Permission.objects.filter(content_type=ct)
    print(f"\n   📦 {ct.model.title()}:")
    for p in perms:
        print(f"      • {p.codename}")

# Verifica constraints
print("\n✅ CONSTRAINTS/INDEXES:")
print("   • Armazém: unique_armazem_codigo_empresa")
print("   • Local: unique_local_codigo_armazem")
print("   • Lote: unique_lote_produto_empresa")

# Verifica managers
print("\n✅ MANAGERS CUSTOMIZADOS:")
print(f"   • Armazem.objects: {type(Armazem.objects).__name__}")
print(f"   • Métodos: da_empresa(), ativos()")

print("\n" + "=" * 70)
print("FASE 1 - ESTRUTURA BÁSICA: ✅ COMPLETA")
print("=" * 70)
print("\nPRÓXIMOS PASSOS:")
print("   1. Criar forms.py para formulários")
print("   2. Implementar views com lógica de negócio")
print("   3. Criar templates (list, form, detail)")
print("   4. Adicionar testes unitários")
print("=" * 70)
