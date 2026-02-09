import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from estoque.models import MovimentacaoEstoque
from produtos.models import Produto

fert = Produto.objects.get(codigo='FERT-000002')

print(f"Produto: {fert.descricao}")

# Verifica ENTRADAS
movs_entrada = MovimentacaoEstoque.objects.filter(tipo='ENTRADA', produto=fert)
print(f"\nENTRADAS de {fert.codigo}:")
for m in movs_entrada:
    print(f"  {m.id}: {m.status}, armazem_destino={m.armazem_destino}, origem={m.origem}, lote={m.lote}, qtd={m.quantidade}")

# Verifica SAÍDAS
movs_saida = MovimentacaoEstoque.objects.filter(tipo='SAIDA', produto=fert)
print(f"\nSAÍDAS de {fert.codigo}:")
for m in movs_saida:
    print(f"  {m.id}: {m.status}, armazem_origem={m.armazem_origem}, origem={m.origem}, lote={m.lote}, qtd={m.quantidade}")

# Verifica sem lote
movs_sem_lote_entrada = MovimentacaoEstoque.objects.filter(tipo='ENTRADA', produto=fert, lote__isnull=True, status='EXECUTADO')
print(f"\nENTRADAS sem lote (EXECUTADO):")
print(f"Count: {movs_sem_lote_entrada.count()}")
for m in movs_sem_lote_entrada:
    print(f"  {m.id}: armazem_destino={m.armazem_destino}")
