import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from compras.models import SolicitacaoCompra

sol = SolicitacaoCompra.objects.get(numero='SC-000003')

print(f"\n{'='*60}")
print(f"DEBUG - VISUALIZAÇÃO DO TEMPLATE")
print(f"{'='*60}")

print(f"\nStatus da solicitação: '{sol.status}'")
print(f"Condição do template: status == 'APROVADA' or status == 'PARCIALMENTE_COTADA'")
print(f"Resultado: {sol.status == 'APROVADA' or sol.status == 'PARCIALMENTE_COTADA'}")

print(f"\n{'='*60}")
print("ITENS E CHECKBOXES:")
print(f"{'='*60}")

for idx, item in enumerate(sol.itens.all(), 1):
    print(f"\n{idx}. {item.produto.nome}")
    print(f"   status_item: '{item.status_item}'")
    
    # Verificar se checkbox deve aparecer
    status_permite = sol.status in ['APROVADA', 'PARCIALMENTE_COTADA']
    item_permite = item.status_item in ['PENDENTE', 'SELECIONADO']
    
    print(f"   Status solicitação permite checkbox? {status_permite}")
    print(f"   Status item permite checkbox? {item_permite}")
    print(f"   DEVE MOSTRAR CHECKBOX: {status_permite and item_permite}")
    
    if status_permite and item_permite:
        print(f"   ✓ CHECKBOX DEVE APARECER")
    else:
        print(f"   ✗ CHECKBOX NÃO DEVE APARECER")
        if not status_permite:
            print(f"      Motivo: Status da solicitação é '{sol.status}'")
        if not item_permite:
            print(f"      Motivo: Status do item é '{item.status_item}'")

print(f"\n{'='*60}\n")
