import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from estoque.models import Lote, MovimentacaoEstoque
from produtos.models import Produto
from empresas.models import Empresa
from decimal import Decimal
from django.db.models import Sum

empresa = Empresa.objects.first()

# Check FERT-000002
fert = Produto.objects.get(codigo='FERT-000002')
print(f"FERT ID: {fert.id}, código: {fert.codigo}")

# Lotes
lotes_dados = Lote.objects.filter(
    empresa=empresa,
    status__in=['DISPONIVEL', 'BLOQUEADO']
).values('produto').annotate(
    qtd=Sum('quantidade_atual')
)

print(f"\nLotes consolidados:")
for item in lotes_dados:
    prod = Produto.objects.get(id=item['produto'])
    print(f"  {prod.id} {prod.codigo}: {item['qtd']} kg")

# Movimentações entrada
movs_entrada = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    lote__isnull=True,
    tipo='ENTRADA',
    status='EXECUTADO'
).values('produto').annotate(
    qtd=Sum('quantidade')
)

print(f"\nMovimentações ENTRADA:")
for item in movs_entrada:
    prod = Produto.objects.get(id=item['produto'])
    print(f"  {prod.id} {prod.codigo}: {item['qtd']} kg")

# Movimentações saída
movs_saida = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    lote__isnull=True,
    tipo='SAIDA',
    status='EXECUTADO'
).values('produto').annotate(
    qtd=Sum('quantidade')
)

print(f"\nMovimentações SAÍDA:")
for item in movs_saida:
    prod = Produto.objects.get(id=item['produto'])
    print(f"  {prod.id} {prod.codigo}: {item['qtd']} kg")

# Check FERT-000002 specifically
print(f"\n=== FERT-000002 Específico ===")
lotes_fert = Lote.objects.filter(
    empresa=empresa,
    produto=fert,
    status__in=['DISPONIVEL', 'BLOQUEADO']
).aggregate(qtd=Sum('quantidade_atual'))
print(f"Lotes: {lotes_fert['qtd']} kg")

movs_entrada_fert = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    produto=fert,
    lote__isnull=True,
    tipo='ENTRADA',
    status='EXECUTADO'
).aggregate(qtd=Sum('quantidade'))
print(f"Entradas: {movs_entrada_fert['qtd']} kg")

movs_saida_fert = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    produto=fert,
    lote__isnull=True,
    tipo='SAIDA',
    status='EXECUTADO'
).aggregate(qtd=Sum('quantidade'))
print(f"Saídas: {movs_saida_fert['qtd']} kg")

total = (lotes_fert['qtd'] or Decimal('0')) + (movs_entrada_fert['qtd'] or Decimal('0')) - (movs_saida_fert['qtd'] or Decimal('0'))
print(f"TOTAL: {total} kg")

print(f"\nProduto estoque_atual: {fert.estoque_atual} kg")
