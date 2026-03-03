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
QUANTIDADE_PEDIDA = 10000
QUANTIDADE_DIVERGENCIA = 7000  # Menos que o pedido
FORNECEDOR_ID = 1

print("=" * 80)
print("🧪 TESTE: Recebimento com DIVERGÊNCIA/PROBLEMA")
print("=" * 80)

try:
    # Obter dados necessários
    produto = Produto.objects.get(pk=PRODUTO_ID)
    fornecedor = Fornecedor.objects.get(pk=FORNECEDOR_ID)
    usuario = Usuario.objects.filter(is_superuser=True).first()
    empresa = usuario.empresa
    armazem = Armazem.objects.filter(empresa=empresa).first()
    local_estoque = armazem  # Usar armazem como local_estoque
    
    print(f"\n✓ Produto: {produto.nome}")
    print(f"✓ Quantidade Pedida: {QUANTIDADE_PEDIDA} unidades")
    print(f"✓ Quantidade Recebida: {QUANTIDADE_DIVERGENCIA} unidades")
    print(f"✓ Diferença: {QUANTIDADE_PEDIDA - QUANTIDADE_DIVERGENCIA} unidades faltando")
    
    # Criar Pedido de Compra
    print(f"\n{'='*80}")
    print(f"PASSO 1: Criar Pedido com {QUANTIDADE_PEDIDA} unidades")
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
        quantidade_pedida=Decimal(str(QUANTIDADE_PEDIDA)),
        unidade_medida=produto.unidade_medida,
        preco_unitario=Decimal('5.50'),
        preco_total=Decimal(str(QUANTIDADE_PEDIDA)) * Decimal('5.50')
    )
    print(f"✓ Item: {item_pedido.quantidade_pedida} x R$ {item_pedido.preco_unitario}")
    
    # Estoque ANTES
    produto_before = Produto.objects.get(pk=produto.pk)
    print(f"\n✓ Estoque ANTES do recebimento: {produto_before.estoque_atual}")
    
    # ============================================================
    # RECEBIMENTO COM DIVERGÊNCIA
    # ============================================================
    print(f"\n{'='*80}")
    print(f"PASSO 2: Recebimento com DIVERGÊNCIA")
    print(f"{'='*80}")
    print(f"Pedido: {QUANTIDADE_PEDIDA} unidades")
    print(f"Recebido: {QUANTIDADE_DIVERGENCIA} unidades")
    print(f"Faltam: {QUANTIDADE_PEDIDA - QUANTIDADE_DIVERGENCIA} unidades")
    
    recebimento = RecebimentoCompra.objects.create(
        empresa=empresa,
        pedido=pedido,
        fornecedor=fornecedor,
        nota_fiscal=f"NF-DIVERGENCIA-{int(timezone.now().timestamp())}",
        data_recebimento=timezone.now(),
        recebido_por=usuario,
        status='PENDENTE'
    )
    print(f"\n✓ Recebimento criado: {recebimento.numero}")
    print(f"  Status: PENDENTE")
    
    # Receber MENOS que o pedido
    item_rec = ItemRecebimento.objects.create(
        recebimento=recebimento,
        item_pedido=item_pedido,
        quantidade_recebida=Decimal(str(QUANTIDADE_DIVERGENCIA)),
        unidade_medida=produto.unidade_medida,
        local_estoque=local_estoque
    )
    print(f"✓ Item recebido: {item_rec.quantidade_recebida} {produto.unidade_medida.sigla}")
    
    # ============================================================
    # CONFERÊNCIA - MARCAR COMO DIVERGENTE
    # ============================================================
    print(f"\n{'='*80}")
    print(f"PASSO 3: Conferência - DIVERGÊNCIA DETECTADA")
    print(f"{'='*80}")
    
    recebimento.status = 'DIVERGENTE'
    recebimento.divergencias = f"Recebido apenas {QUANTIDADE_DIVERGENCIA} unidades de {QUANTIDADE_PEDIDA} pedidas. Faltam {QUANTIDADE_PEDIDA - QUANTIDADE_DIVERGENCIA} unidades. Fornecedor informou que completará o envio em 3 dias."
    recebimento.save()
    print(f"✓ Recebimento marcado como: DIVERGENTE")
    print(f"✓ Divergências registradas:")
    print(f"  {recebimento.divergencias}")
    
    # ============================================================
    # OPÇÃO 1: ACEITAR E DAR ENTRADA (mesmo com falta)
    # ============================================================
    print(f"\n{'='*80}")
    print(f"PASSO 4: Aceitar Recebimento e Dar Entrada no Estoque")
    print(f"{'='*80}")
    print(f"(Nota: Mesmo com divergência, a entrada será registrada com a quantidade recebida)")
    
    recebimento.status = 'CONFERIDO'  # Mudar para CONFERIDO para poder finalizar
    recebimento.save()
    
    # Registrar movimento de estoque
    item_rec.registrar_movimento_estoque()
    recebimento.status = 'FINALIZADO'
    recebimento.save()
    
    print(f"✓ Movimento de estoque registrado")
    print(f"✓ Recebimento finalizado")
    
    produto_after = Produto.objects.get(pk=produto.pk)
    print(f"\n📊 Estoque APÓS recebimento parcial: {produto_after.estoque_atual}")
    print(f"   (Apenas {QUANTIDADE_DIVERGENCIA} entraram, não {QUANTIDADE_PEDIDA})")
    
    # ============================================================
    # ANÁLISE FINAL
    # ============================================================
    print(f"\n{'='*80}")
    print(f"📊 ANÁLISE FINAL")
    print(f"{'='*80}")
    
    lotes = Lote.objects.filter(produto=produto, status='DISPONIVEL').order_by('-id').first()
    if lotes:
        print(f"\n📦 Lote Criado:")
        print(f"  Número: {lotes.numero_lote}")
        print(f"  Quantidade: {lotes.quantidade_atual}")
        print(f"  NF: {lotes.nota_fiscal}")
    
    movs = MovimentacaoEstoque.objects.filter(produto=produto, tipo='ENTRADA').order_by('-id').first()
    if movs:
        print(f"\n📋 Movimento de Entrada:")
        print(f"  Quantidade: {movs.quantidade}")
        print(f"  Observação: {movs.observacao[:80]}...")
    
    print(f"\n{'='*80}")
    print(f"📝 RESUMO:")
    print(f"  Pedido original: {QUANTIDADE_PEDIDA} unidades")
    print(f"  Recebido: {QUANTIDADE_DIVERGENCIA} unidades")
    print(f"  Status do recebimento: {recebimento.status}")
    print(f"  Divergências que ficaram registradas: SIM")
    print(f"  Estoque atual: {produto_after.estoque_atual}")
    
    print(f"\n✅ PRÓXIMAS ETAPAS:")
    print(f"  1. Fornecedor deverá enviar as {QUANTIDADE_PEDIDA - QUANTIDADE_DIVERGENCIA} unidades faltantes")
    print(f"  2. Ao receber complemento, criar novo recebimento (parcial 2)")
    print(f"  3. Finalizar quando todo pedido for recebido")
    print(f"{'='*80}\n")

except Exception as e:
    import traceback
    print(f"\n❌ ERRO: {e}")
    traceback.print_exc()
