#!/usr/bin/env python
"""
Importa NCMs diretamente do CSV arquivo para o banco de dados
"""
import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

import csv
from cadastros.models import NCM

csv_path = os.path.join(Path(__file__).parent, 'NCM_import.csv')

print(f"\nImportando NCMs de: {csv_path}")
print("="*60)

if not os.path.exists(csv_path):
    print(f"❌ Arquivo não encontrado: {csv_path}")
    exit(1)

created = 0
updated = 0
skipped = 0

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        codigo = row.get('codigo', '').strip()
        nome = row.get('nome', '').strip()
        
        if not codigo or not nome:
            skipped += 1
            continue
        
        # Truncar nome se exceder 500 caracteres
        if len(nome) > 500:
            nome = nome[:500]
        
        # Criar ou atualizar
        obj, was_created = NCM.objects.get_or_create(
            codigo=codigo,
            defaults={'nome': nome, 'ativo': True}
        )
        
        if was_created:
            created += 1
        else:
            # Atualizar se ativo for False
            if not obj.ativo:
                obj.ativo = True
                obj.save()
            updated += 1

print(f"\n✅ Importação Concluída:")
print(f"   Criados: {created}")
print(f"   Atualizados: {updated}")
print(f"   Ignorados: {skipped}")
print(f"   Total: {NCM.objects.all().count()}")
print(f"   Ativos: {NCM.objects.filter(ativo=True).count()}")

print("\n" + "="*60)
