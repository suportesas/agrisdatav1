import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from estoque.models import InventarioCiclico, InventarioCiclicoItem
from produtos.models import Produto

# Get the latest inventory
inv = InventarioCiclico.objects.latest('data_contagem')
print(f"Inventário: {inv.numero}")
print(f"Tipo: {inv.tipo_inventario}")
print(f"Total itens: {inv.total_items_sistema}")

# Get ALL items
items = inv.itens.all()
print(f"\nTodos os {items.count()} itens:")
for item in items:
    lote_str = f"Lote: {item.lote.numero}" if item.lote else "Sem lote (Movimentação direta)"
    print(f"  Produto ID {item.produto.id}: {item.produto.codigo} {lote_str}")
    print(f"    Qtd: {item.quantidade_sistema}")

# Get FERT-000002
fert = Produto.objects.get(codigo='FERT-000002')
print(f"\nFert ID: {fert.id}")
print(f"Fert código: {fert.codigo}")

# Try direct filter
items_fert = InventarioCiclicoItem.objects.filter(inventario=inv, produto=fert)
print(f"\nDirect filter result: {items_fert.count()} items")
for item in items_fert:
    print(f"  {item.id}: qtd={item.quantidade_sistema}")
