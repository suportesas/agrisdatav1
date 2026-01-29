import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import SolicitacaoCompra

sol = SolicitacaoCompra.objects.get(numero='SC-000003')

print(f"\nStatus: '{sol.status}'")
print(f"Status repr: {repr(sol.status)}")
print(f"Status length: {len(sol.status)}")
print(f"Comparação 1: {sol.status == 'APROVADA'}")
print(f"Comparação 2: {sol.status == 'PARCIALMENTE_COTADA'}")
print(f"Resultado OR: {sol.status == 'APROVADA' or sol.status == 'PARCIALMENTE_COTADA'}")

print(f"\n\nItens:")
for item in sol.itens.all():
    print(f"\n{item.produto.nome}:")
    print(f"  status_item: '{item.status_item}'")
    print(f"  status_item repr: {repr(item.status_item)}")
    print(f"  É PENDENTE? {item.status_item == 'PENDENTE'}")
    print(f"  É SELECIONADO? {item.status_item == 'SELECIONADO'}")
    mostra_checkbox = (sol.status == 'APROVADA' or sol.status == 'PARCIALMENTE_COTADA') and (item.status_item == 'PENDENTE' or item.status_item == 'SELECIONADO')
    print(f"  DEVE MOSTRAR CHECKBOX? {mostra_checkbox}")
