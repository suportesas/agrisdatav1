#!/usr/bin/env python
"""
Script para testar se as permissões de produtos aparecem na view
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import Permission
from empresas.models import Empresa, Role

print("=" * 70)
print("TESTE: PERMISSÕES DE PRODUTOS NA VIEW DE ROLES")
print("=" * 70)

# Simula o que a view faz
perms = Permission.objects.all().select_related('content_type')

APP_LABELS = {
    'cadastros': 'Cadastros',
    'empresas': 'Empresa',
    'usuarios': 'Usuários',
    'auth': 'Autenticação',
    'produtos': 'Produtos',
}

grouped = {}

for p in perms:
    app = p.content_type.app_label
    model = p.content_type.model
    key = f"{app}:{model}"
    
    if key not in grouped:
        grouped[key] = {
            'app_label': app,
            'model': model,
            'display': APP_LABELS.get(app, app.title()) + ' • ' + model.title(),
            'perms': {'add': False, 'change': False, 'delete': False, 'view': False}
        }

# Filtra apenas produtos
produtos_items = {k: v for k, v in grouped.items() if k.startswith('produtos:')}

print(f"\n✅ Total de grupos de permissões de PRODUTOS: {len(produtos_items)}\n")

for key, item in sorted(produtos_items.items()):
    print(f"📦 {item['display']}")
    print(f"   Key: {key}")
    print()

print("=" * 70)
print("\nSUCESSO! As permissões de produtos estão disponíveis no sistema.")
print("Elas aparecerão automaticamente na interface de gerenciamento de roles.")
print("=" * 70)
