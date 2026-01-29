def run():
    from produtos.models import Produto
    from estoque.models import Lote

    target_produto_id = 13  # Altere se necessário
    produto = Produto.objects.get(pk=target_produto_id)
    lotes = Lote.objects.filter(produto=produto)

    print(f"Produto: {produto.nome} (ID: {produto.id})")
    print("Lotes:")
    for lote in lotes:
        print(f"  Lote: {lote.numero_lote} | Status: {lote.status} | Qtd Atual: {lote.quantidade_atual} | Qtd Inicial: {lote.quantidade_inicial}")

    print(f"Estoque atual do produto: {produto.estoque_atual}")
