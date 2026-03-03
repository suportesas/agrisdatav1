import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from produtos.models import Produto
from cadastros.models import Fornecedor
from compras.models import PedidoCompra, ItemPedidoCompra, RecebimentoCompra, ItemRecebimento
from estoque.models import Lote, MovimentacaoEstoque, Armazem
from usuarios.models import Usuario

# Configuração
PRODUTO_ID = 6
QUANTIDADE_TOTAL_PEDIDO = 10000
QUANTIDADE_PARCELA_1 = 5000
QUANTIDADE_PARCELA_2 = 5000
FORNECEDOR_ID = 1

print("=" * 80)
print("🧪 TESTE: Recebimento Parcial do Pedido")
print("=" * 80)

try:
    # Obter dados necessários
    produto = Produto.objects.get(pk=PRODUTO_ID)
    fornecedor = Fornecedor.objects.get(pk=FORNECEDOR_ID)
    usuario = Usuario.objects.filter(is_superuser=True).first()
    empresa = usuario.empresa
    armazem = Armazem.objects.filter(empresa=empresa).first()
    local_estoque = Armazem.objects.filter(empresa=empresa).first()
    
    print(f"\n✓ Produto: {produto.nome}")
    print(f"✓ Pedido Total: {QUANTIDADE_TOTAL_PEDIDO} unidades")
    print(f"✓ Parcela 1: {QUANTIDADE_PARCELA_1} unidades")
    print(f"✓ Parcela 2: {QUANTIDADE_PARCELA_2} unidades")
    
    # Criar Pedido de Compra
    print(f"\n{'='*80}")
    print(f"PASSO 1: Criar Pedido com {QUANTIDADE_TOTAL_PEDIDO} unidades")
    print(f"{'='*80}")
    
    pedido = PedidoCompra.objects.create(
        empresa=empresa,
        fornecedor=fornecedor,
        comprador=usuario,
        data_pedido=timezone.now(),
        status='ENVIADO'
    )
    print(f"✓ Pedido criado: {pedido.numero}")
    
    item_pedido = ItemPedidoCompra.objects.create(
        pedido=pedido,
        produto=produto,
        quantidade_pedida=Decimal(str(QUANTIDADE_TOTAL_PEDIDO)),
        unidade_medida=produto.unidade_medida,
        preco_unitario=Decimal('5.50'),
        preco_total=Decimal(str(QUANTIDADE_TOTAL_PEDIDO)) * Decimal('5.50')
    )
    print(f"✓ Item: {item_pedido.quantidade_pedida} x R$ {item_pedido.preco_unitario}")
    
    # Estoque ANTES
    produto_before = Produto.objects.get(pk=produto.pk)
    print(f"\n✓ Estoque ANTES de qualquer recebimento: {produto_before.estoque_atual}")
    
    # ============================================================
    # PRIMEIRO RECEBIMENTO (PARCIAL) - 5000 unidades
    # ============================================================
    print(f"\n{'='*80}")
    print(f"PASSO 2: Primeiro Recebimento (PARCIAL) - {QUANTIDADE_PARCELA_1} unidades")
    print(f"{'='*80}")
    
    recebimento_1 = RecebimentoCompra.objects.create(
        empresa=empresa,
        pedido=pedido,
        fornecedor=fornecedor,
        nota_fiscal=f"NF-TESTE-PARCIAL-1-{int(timezone.now().timestamp())}",
        data_recebimento=timezone.now(),
        recebido_por=usuario,
        status='PENDENTE'
    )
    print(f"✓ Recebimento 1 criado: {recebimento_1.numero}")
    
    item_rec_1 = ItemRecebimento.objects.create(
        recebimento=recebimento_1,
        item_pedido=item_pedido,
        quantidade_recebida=Decimal(str(QUANTIDADE_PARCELA_1)),
        unidade_medida=produto.unidade_medida,
        local_estoque=local_estoque
    )
    print(f"✓ Item recebido: {item_rec_1.quantidade_recebida} {produto.unidade_medida.sigla}")
    
    # Conferir e dar entrada
    recebimento_1.status = 'CONFERIDO'
    recebimento_1.save()
    print(f"✓ Recebimento 1 conferido")
    
    item_rec_1.registrar_movimento_estoque()
    recebimento_1.status = 'FINALIZADO'
    recebimento_1.save()
    print(f"✓ Recebimento 1 finalizado - Entrada no estoque registrada")
    
    produto_after_rec1 = Produto.objects.get(pk=produto.pk)
    print(f"\n📊 Estoque APÓS 1º recebimento: {produto_after_rec1.estoque_atual} (esperado: {QUANTIDADE_PARCELA_1})")
    
    # ============================================================
    # SEGUNDO RECEBIMENTO (RESTANTE) - 5000 unidades
    # ============================================================
    print(f"\n{'='*80}")
    print(f"PASSO 3: Segundo Recebimento (RESTANTE) - {QUANTIDADE_PARCELA_2} unidades")
    print(f"{'='*80}")
    
    recebimento_2 = RecebimentoCompra.objects.create(
        empresa=empresa,
        pedido=pedido,
        fornecedor=fornecedor,
        nota_fiscal=f"NF-TESTE-PARCIAL-2-{int(timezone.now().timestamp())}",
        data_recebimento=timezone.now(),
        recebido_por=usuario,
        status='PENDENTE'
    )
    print(f"✓ Recebimento 2 criado: {recebimento_2.numero}")
    
    item_rec_2 = ItemRecebimento.objects.create(
        recebimento=recebimento_2,
        item_pedido=item_pedido,
        quantidade_recebida=Decimal(str(QUANTIDADE_PARCELA_2)),
        unidade_medida=produto.unidade_medida,
        local_estoque=local_estoque
    )
    print(f"✓ Item recebido: {item_rec_2.quantidade_recebida} {produto.unidade_medida.sigla}")
    
    # Conferir e dar entrada
    recebimento_2.status = 'CONFERIDO'
    recebimento_2.save()
    print(f"✓ Recebimento 2 conferido")
    
    item_rec_2.registrar_movimento_estoque()
    recebimento_2.status = 'FINALIZADO'
    recebimento_2.save()
    print(f"✓ Recebimento 2 finalizado - Entrada no estoque registrada")
    
    produto_after_rec2 = Produto.objects.get(pk=produto.pk)
    print(f"\n📊 Estoque APÓS 2º recebimento: {produto_after_rec2.estoque_atual} (esperado: {QUANTIDADE_TOTAL_PEDIDO})")
    
    # ============================================================
    # VALIDAÇÃO FINAL
    # ============================================================
    print(f"\n{'='*80}")
    print(f"📊 RESULTADOS FINAIS")
    print(f"{'='*80}")
    
    lotes = Lote.objects.filter(produto=produto, status='DISPONIVEL').order_by('id')
    print(f"\n📦 Lotes criados:")
    total_lotes = Decimal('0')
    for lote in lotes:
        print(f"  - {lote.numero_lote}: {lote.quantidade_atual} (NF: {lote.nota_fiscal})")
        total_lotes += lote.quantidade_atual
    
    movs = MovimentacaoEstoque.objects.filter(produto=produto, tipo='ENTRADA').order_by('id')
    print(f"\n📋 Movimentações:")
    print(f"  Total: {movs.count()}")
    for mov in movs:
        print(f"    - Lote: {mov.lote.numero_lote if mov.lote else 'NENHUM'}, Qtd: {mov.quantidade}")
    
    print(f"\n{'='*80}")
    if float(produto_after_rec2.estoque_atual) == QUANTIDADE_TOTAL_PEDIDO:
        print(f"✅ TESTE PASSOU - Estoque total correto!")
        print(f"   Total recebido: {QUANTIDADE_PARCELA_1} + {QUANTIDADE_PARCELA_2} = {QUANTIDADE_TOTAL_PEDIDO}")
        print(f"   Estoque final: {produto_after_rec2.estoque_atual}")
    else:
        print(f"❌ TESTE FALHOU - Estoque incorreto!")
        print(f"   Esperado: {QUANTIDADE_TOTAL_PEDIDO}")
        print(f"   Obtido: {produto_after_rec2.estoque_atual}")
    
    if lotes.count() == 2:
        print(f"✅ Dois lotes criados (um para cada recebimento)")
    elif lotes.count() == 1:
        print(f"⚠️ Um único lote criado - verifique se as quantidades foram somadas corretamente")
        print(f"   Quantidade final do lote: {total_lotes}")
    else:
        print(f"❌ Número inesperado de lotes: {lotes.count()}")
    
    print(f"{'='*80}\n")

except Exception as e:
    import traceback
    print(f"\n❌ ERRO: {e}")
    traceback.print_exc()
