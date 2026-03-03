import os
import django
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto
from estoque.models import Lote, MovimentacaoEstoque

# Corrigir produto 6
produto = Produto.objects.get(pk=6)
print(f"📦 Produto: {produto.nome}")
print(f"❌ Estoque antes: {produto.estoque_atual}")

# Obter o lote e corrigir sua quantidade_atual
lote = Lote.objects.get(produto=produto, status='DISPONIVEL')
print(f"Lote: {lote.numero_lote}")
print(f"  - Quantidade Atual ANTES: {lote.quantidade_atual}")

# A quantidade correta é a soma de TODAS as movimentações de ENTRADA para este lote
movs_entrada = MovimentacaoEstoque.objects.filter(lote=lote, tipo='ENTRADA')
total_quantidade = sum(m.quantidade for m in movs_entrada)
print(f"  - Total de movimentações de entrada: {movs_entrada.count()}")
print(f"  - Soma das movimentações: {total_quantidade}")

# Corrigir lote
lote.quantidade_atual = total_quantidade
lote.save(update_fields=['quantidade_atual'])
print(f"  - Quantidade Atual DEPOIS: {lote.quantidade_atual}")

# Recalcular soma de lotes disponíveis
total_estoque = Decimal('0')
lotes_disponiveis = produto.lotes.filter(status='DISPONIVEL')
for l in lotes_disponiveis:
    total_estoque += l.quantidade_atual

# Atualizar estoque do produto
produto.estoque_atual = total_estoque
produto.save(update_fields=['estoque_atual'])

print(f"\n✅ Estoque do produto corrigido para: {produto.estoque_atual}")

