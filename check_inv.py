from estoque.models import InventarioCiclico
from produtos.models import Produto

# Get latest inventories
invs = InventarioCiclico.objects.order_by('-data_contagem')[:5]
print(f"Latest inventories:")
for inv in invs:
    print(f"  {inv.numero}: {inv.tipo_inventario}, {inv.total_items_sistema} items, {inv.itens.count()} actual")
    for item in inv.itens.all():
        print(f"    - Prod: {item.produto.id}, Qtd: {item.quantidade_sistema}")
