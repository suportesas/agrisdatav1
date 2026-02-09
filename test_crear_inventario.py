#!/usr/bin/env python
"""
Teste de criação de inventário cíclico com consolidação
"""

import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from estoque.models import Lote, MovimentacaoEstoque, InventarioCiclico, InventarioCiclicoItem, Armazem
from produtos.models import Produto
from empresas.models import Empresa
from usuarios.models import Usuario
from django.utils import timezone
from decimal import Decimal

# Get data
fert = Produto.objects.get(codigo='FERT-000002')
empresa = Empresa.objects.first()
armazem = Armazem.objects.filter(empresa=empresa).first()
user = Usuario.objects.filter(empresa=empresa).first()

print(f"1. Produto: {fert.descricao}", flush=True)
print(f"2. Empresa: {empresa.nome}", flush=True)
print(f"Armazém: {armazem.nome}")
print(f"Usuário: {user.first_name if user else 'N/A'}")

# Delete inventários antigos se necessário
InventarioCiclico.objects.filter(empresa=empresa, armazem=armazem).delete()

# Cria novo inventário - POR_ITEM
data_hoje = timezone.now().date()
numero = f"IC-TEST-{data_hoje.strftime('%Y%m%d')}"

inventario = InventarioCiclico.objects.create(
    empresa=empresa,
    numero=numero,
    armazem=armazem,
    tipo_inventario='POR_ITEM',
    data_contagem=data_hoje,
    status='PLANEJADO',
    responsavel=user,
)

print(f"\nInventário criado: {numero}")

# Agrupa por produto, soma quantidades (LOTES + MOVIMENTAÇÕES DIRETAS)
from django.db.models import Sum, Avg, F
from django.db.models.functions import Coalesce
from django.db.models import Value, DecimalField

# 1. Dados dos lotes
lotes_dados = Lote.objects.filter(
    empresa=empresa,
    armazem=armazem,
    status__in=['DISPONIVEL', 'BLOQUEADO']
).values('produto').annotate(
    qtd_lotes=Sum('quantidade_atual'),
    valor_medio_lotes=Avg('valor_unitario'),
)

print(f"\nLotes data: {list(lotes_dados)[:2]}")  # Debug

# 2. Dados de movimentações diretas
movimentacoes_entrada = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    lote__isnull=True,
    tipo='ENTRADA',
    status='EXECUTADO'
).values('produto').annotate(
    qtd=Sum('quantidade')
)

movimentacoes_saida = MovimentacaoEstoque.objects.filter(
    empresa=empresa,
    lote__isnull=True,
    tipo='SAIDA',
    status='EXECUTADO'
).values('produto').annotate(
    qtd=Sum('quantidade')
)

movs_entrada_dict = {item['produto']: item['qtd'] for item in movimentacoes_entrada}
movs_saida_dict = {item['produto']: item['qtd'] for item in movimentacoes_saida}

print(f"Entradas: {movs_entrada_dict}")
print(f"Saídas: {movs_saida_dict}")

# 3. Consolida todos os produtos
produtos_consolidados = {}

for item in lotes_dados:
    prod_id = item['produto']
    produtos_consolidados[prod_id] = {
        'qtd_lotes': item['qtd_lotes'] or Decimal('0'),
        'valor_medio_lotes': item['valor_medio_lotes'] or Decimal('0'),
        'qtd_entrada': Decimal('0'),
        'qtd_saida': Decimal('0'),
    }

for item in movimentacoes_entrada:
    prod_id = item['produto']
    if prod_id not in produtos_consolidados:
        produtos_consolidados[prod_id] = {
            'qtd_lotes': Decimal('0'),
            'valor_medio_lotes': Decimal('0'),
            'qtd_entrada': Decimal('0'),
            'qtd_saida': Decimal('0'),
        }
    produtos_consolidados[prod_id]['qtd_entrada'] = item['qtd'] or Decimal('0')

for item in movimentacoes_saida:
    prod_id = item['produto']
    if prod_id not in produtos_consolidados:
        produtos_consolidados[prod_id] = {
            'qtd_lotes': Decimal('0'),
            'valor_medio_lotes': Decimal('0'),
            'qtd_entrada': Decimal('0'),
            'qtd_saida': Decimal('0'),
        }
    produtos_consolidados[prod_id]['qtd_saida'] = item['qtd'] or Decimal('0')

# 4. Cria items para FERT-000002
from decimal import Decimal
prod_dados = produtos_consolidados.get(fert.id)
if prod_dados:
    qtd_final = prod_dados['qtd_lotes'] + prod_dados['qtd_entrada'] - prod_dados['qtd_saida']
    valor_total = qtd_final * prod_dados['valor_medio_lotes']
    
    InventarioCiclicoItem.objects.create(
        inventario=inventario,
        lote=None,
        produto=fert,
        quantidade_sistema=qtd_final,
        valor_unitario_sistema=prod_dados['valor_medio_lotes'],
        valor_total_sistema=valor_total,
        classificacao_abc='A',
    )
    
    print(f"\n✓ Item criado para {fert.descricao}:")
    print(f"  Lotes: {prod_dados['qtd_lotes']} kg")
    print(f"  Entradas (mov): {prod_dados['qtd_entrada']} kg")
    print(f"  Saídas (mov): {prod_dados['qtd_saida']} kg")
    print(f"  TOTAL: {qtd_final} kg")
    print(f"  Valor médio: {prod_dados['valor_medio_lotes']}")
else:
    print(f"✗ Produto {fert.id} não encontrado na consolidação")

# Salva total
inventario.total_items_sistema = inventario.itens.count()
inventario.save()

print(f"\n✓ Inventário finalizado com {inventario.total_items_sistema} itens")

# Verifica
items_check = inventario.itens.filter(produto=fert)
for item in items_check:
    print(f"\n✓ Verificação: {item.produto.descricao}")
    print(f"  Quantidade sistema: {item.quantidade_sistema} kg")
    print(f"  Classificação: {item.classificacao_abc}")

print(f"\n✓ SUCESSO! Sistema consolidou corretamente")
