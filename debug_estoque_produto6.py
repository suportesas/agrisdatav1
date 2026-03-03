import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from produtos.models import Produto
from estoque.models import Lote, MovimentacaoEstoque
from compras.models import RecebimentoCompra, ItemRecebimento

try:
    produto = Produto.objects.get(pk=6)
    print(f"📦 Produto: {produto.nome}")
    print(f"❌ Estoque Atual: {produto.estoque_atual}")
    
    lote = Lote.objects.get(produto=produto, status='DISPONIVEL')
    print(f"\n📦 Lote: {lote.numero_lote}")
    print(f"   Quantidade Inicial: {lote.quantidade_inicial} (deveria ser 10.000)")
    print(f"   Quantidade Atual: {lote.quantidade_atual} (está com {lote.quantidade_atual}, deveria ser 10.000)")
    
    # Verificar se há outros lotes do mesmo produto
    todos_lotes = Lote.objects.filter(produto=produto).order_by('id')
    print(f"\n🔍 Todos os lotes do produto:")
    for l in todos_lotes:
        print(f"   ID: {l.id}, Status: {l.status}, Qtd Atual: {l.quantidade_atual}")
    
    # Analisar a movimentação
    mov = MovimentacaoEstoque.objects.get(lote=lote)
    print(f"\n📋 Movimentação:")
    print(f"   ID: {mov.id}")
    print(f"   Quantidade: {mov.quantidade} (correto)")
    print(f"   Observação: {mov.observacao}")
    
    # Verificar se há múltiplas linhas na observação
    todas_movs = MovimentacaoEstoque.objects.filter(lote=lote)
    print(f"\n   Total de movimentações para este lote: {todas_movs.count()}")
    for m in todas_movs:
        print(f"      - {m.id}: Qtd {m.quantidade}")
        
except Exception as e:
    import traceback
    print(f"ERRO: {e}")
    traceback.print_exc()



