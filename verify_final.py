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

# Get FERT-000002 items
fert = Produto.objects.get(codigo='FERT-000002')
items = inv.itens.filter(produto=fert)

print(f"\nItens de {fert.codigo}:")
for item in items:
    lote_str = f"Lote: {item.lote.numero}" if item.lote else "Sem lote (Movimentação direta)"
    print(f"  {lote_str}")
    print(f"    Qtd: {item.quantidade_sistema} {fert.unidade_medida.sigla}")
    print(f"    Valor unitário: {item.valor_unitario_sistema}")
    print(f"    Total: {item.valor_total_sistema}")
    print(f"    Classificação: {item.classificacao_abc}")

# Sum all for FERT
total_qtd = items.aggregate(total=__import__('django.db.models', fromlist=['Sum']).Sum('quantidade_sistema'))['total'] or 0
print(f"\nTOTAL QTD: {total_qtd} {fert.unidade_medida.sigla}")

# Verify against product
print(f"\nProduto estoque_atual: {fert.estoque_atual} {fert.unidade_medida.sigla}")

if total_qtd == fert.estoque_atual:
    print(f"✓ MATCH! Sistema consolidado corretamente")
else:
    print(f"✗ DISCREPÂNCIA: Inventário={total_qtd}, Produto={fert.estoque_atual}")
