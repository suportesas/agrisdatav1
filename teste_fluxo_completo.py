import os
import django
from decimal import Decimal
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from produtos.models import Produto
from cadastros.models import Fornecedor
from compras.models import SolicitacaoCompra, ItemSolicitacaoCompra, PedidoCompra, ItemPedidoCompra, RecebimentoCompra, ItemRecebimento
from estoque.models import Lote, MovimentacaoEstoque, LocalEstocagem, Armazem
from usuarios.models import Usuario

# Configuração
PRODUTO_ID = 6  # Caixa Pap. Ond.
QUANTIDADE_TESTE = 5000  # Quantidade menor para teste rápido
FORNECEDOR_ID = 1

print("=" * 80)
print("🧪 TESTE COMPLETO: Solicitação → Pedido → Recebimento → Entrada no Estoque")
print("=" * 80)

try:
    # Obter dados necessários
    produto = Produto.objects.get(pk=PRODUTO_ID)
    fornecedor = Fornecedor.objects.get(pk=FORNECEDOR_ID)
    usuario = Usuario.objects.filter(is_superuser=True).first()
    empresa = usuario.empresa
    armazem = Armazem.objects.filter(empresa=empresa).first()
    local_estoque = LocalEstocagem.objects.filter(armazem=armazem).first() if armazem else None
    
    print(f"\n✓ Produtos: {produto.nome}")
    print(f"✓ Fornecedor: {fornecedor.nome}")
    print(f"✓ Empresa: {empresa.nome}")
    print(f"✓ Usuário: {usuario.get_full_name() or usuario.username}")
    print(f"✓ Armazém: {armazem.nome if armazem else 'Nenhum'}")
    print(f"✓ Local Estoque: {local_estoque.descricao if local_estoque else 'Padrão'}")
    
    # PASSO 1: Criar Solicitação de Compra
    print(f"\n{'='*80}")
    print(f"PASSO 1: Criar Solicitação de Compra")
    print(f"{'='*80}")
    
    solicitacao = SolicitacaoCompra.objects.create(
        empresa=empresa,
        solicitante=usuario,
        data_solicitacao=timezone.now(),
        data_necessidade=timezone.now() + timedelta(days=7),
        justificativa="Teste de fluxo completo",
        status='RASCUNHO'
    )
    print(f"✓ Solicitação criada: {solicitacao.numero}")
    
    # Adicionar item à solicitação
    item_sol = ItemSolicitacaoCompra.objects.create(
        solicitacao=solicitacao,
        produto=produto,
        quantidade=Decimal(str(QUANTIDADE_TESTE)),
        unidade_medida=produto.unidade_medida
    )
    print(f"✓ Item adicionado: {QUANTIDADE_TESTE} {produto.unidade_medida.sigla}")
    
    # Aprovar solicitação
    solicitacao.status = 'APROVADA'
    solicitacao.save()
    print(f"✓ Solicitação aprovada")
    
    # PASSO 2: Criar Pedido de Compra
    print(f"\n{'='*80}")
    print(f"PASSO 2: Criar Pedido de Compra")
    print(f"{'='*80}")
    
    pedido = PedidoCompra.objects.create(
        empresa=empresa,
        fornecedor=fornecedor,
        comprador=usuario,
        data_pedido=timezone.now(),
        status='ENVIADO'
    )
    print(f"✓ Pedido criado: {pedido.numero}")
    
    # Adicionar item ao pedido
    item_pedido = ItemPedidoCompra.objects.create(
        pedido=pedido,
        produto=produto,
        quantidade_pedida=Decimal(str(QUANTIDADE_TESTE)),
        unidade_medida=produto.unidade_medida,
        preco_unitario=Decimal('5.50'),
        preco_total=Decimal(str(QUANTIDADE_TESTE)) * Decimal('5.50')
    )
    print(f"✓ Item pedido: {item_pedido.quantidade_pedida} x R$ {item_pedido.preco_unitario} = R$ {item_pedido.preco_total}")
    
    # PASSO 3: Criar Recebimento
    print(f"\n{'='*80}")
    print(f"PASSO 3: Criar Recebimento")
    print(f"{'='*80}")
    
    # Estoque ANTES
    produto_before = Produto.objects.get(pk=produto.pk)
    print(f"✓ Estoque ANTES do recebimento: {produto_before.estoque_atual}")
    
    recebimento = RecebimentoCompra.objects.create(
        empresa=empresa,
        pedido=pedido,
        fornecedor=fornecedor,
        nota_fiscal=f"NF-TESTE-{timezone.now().timestamp()}",
        data_recebimento=timezone.now(),
        recebido_por=usuario,
        status='PENDENTE'
    )
    print(f"✓ Recebimento criado: {recebimento.numero}")
    
    # Adicionar item ao recebimento
    item_rec = ItemRecebimento.objects.create(
        recebimento=recebimento,
        item_pedido=item_pedido,
        quantidade_recebida=Decimal(str(QUANTIDADE_TESTE)),
        unidade_medida=produto.unidade_medida,
        local_estoque=local_estoque
    )
    print(f"✓ Item recebido: {item_rec.quantidade_recebida} {produto.unidade_medida.sigla}")
    
    # PASSO 4: Conferir Recebimento
    print(f"\n{'='*80}")
    print(f"PASSO 4: Conferir Recebimento")
    print(f"{'='*80}")
    
    recebimento.status = 'CONFERIDO'
    recebimento.save()
    print(f"✓ Recebimento conferido (status: CONFERIDO)")
    
    # PASSO 5: Dar Entrada no Estoque
    print(f"\n{'='*80}")
    print(f"PASSO 5: Dar Entrada no Estoque")
    print(f"{'='*80}")
    
    # Chamar registrar_movimento_estoque() UMA VEZ
    print(f"✓ Registrando movimento de estoque (1ª chamada)...")
    item_rec.registrar_movimento_estoque()
    
    produto_after_1 = Produto.objects.get(pk=produto.pk)
    print(f"  Estoque após 1ª chamada: {produto_after_1.estoque_atual}")
    
    # Chamar registrar_movimento_estoque() NOVAMENTE para testar idempotência
    print(f"✓ Registrando movimento de estoque (2ª chamada - teste de idempotência)...")
    item_rec.registrar_movimento_estoque()
    
    produto_after_2 = Produto.objects.get(pk=produto.pk)
    print(f"  Estoque após 2ª chamada: {produto_after_2.estoque_atual}")
    
    # Chamar UMA TERCEIRA VEZ para garantir
    print(f"✓ Registrando movimento de estoque (3ª chamada - teste de idempotência)...")
    item_rec.registrar_movimento_estoque()
    
    produto_after_3 = Produto.objects.get(pk=produto.pk)
    print(f"  Estoque após 3ª chamada: {produto_after_3.estoque_atual}")
    
    # Finalizar recebimento via view
    recebimento.status = 'FINALIZADO'
    recebimento.save()
    print(f"✓ Recebimento finalizado (status: FINALIZADO)")
    
    # RESULTADOS
    print(f"\n{'='*80}")
    print(f"📊 RESULTADOS FINAIS")
    print(f"{'='*80}")
    
    produto_final = Produto.objects.get(pk=produto.pk)
    lote = Lote.objects.filter(produto=produto, status='DISPONIVEL').first()
    movs = MovimentacaoEstoque.objects.filter(lote=lote) if lote else []
    
    print(f"\n📦 Produto: {produto.nome}")
    print(f"  Estoque esperado: {QUANTIDADE_TESTE}")
    print(f"  Estoque atual: {produto_final.estoque_atual}")
    
    if lote:
        print(f"\n📦 Lote: {lote.numero_lote}")
        print(f"  Quantidade Inicial: {lote.quantidade_inicial}")
        print(f"  Quantidade Atual: {lote.quantidade_atual}")
        
    print(f"\n📋 Movimentações:")
    print(f"  Total de movimentações: {movs.count()}")
    for mov in movs:
        print(f"    - {mov.id}: {mov.tipo} ({mov.origem}), Qtd: {mov.quantidade}")
    
    # VALIDAÇÃO
    print(f"\n{'='*80}")
    if float(produto_final.estoque_atual) == QUANTIDADE_TESTE:
        print(f"✅ TESTE PASSOU - Estoque está correto!")
    else:
        print(f"❌ TESTE FALHOU - Estoque incorreto!")
        print(f"   Esperado: {QUANTIDADE_TESTE}")
        print(f"   Obtido: {produto_final.estoque_atual}")
    
    if movs.count() == 1:
        print(f"✅ Idempotência OK - Apenas 1 movimentação registrada (não houve duplicação)")
    else:
        print(f"❌ Idempotência FALHOU - {movs.count()} movimentações registradas")
    
    print(f"{'='*80}\n")

except Exception as e:
    import traceback
    print(f"\n❌ ERRO: {e}")
    traceback.print_exc()
