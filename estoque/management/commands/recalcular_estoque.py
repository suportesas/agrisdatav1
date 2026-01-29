"""
Comando para recalcular o estoque_atual de todos os produtos
baseado na soma dos lotes disponíveis
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum, Q
from produtos.models import Produto
from estoque.models import Lote


class Command(BaseCommand):
    help = 'Recalcula o estoque_atual de todos os produtos baseado nos lotes'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando recálculo de estoque...')
        
        produtos = Produto.objects.all()
        total_produtos = produtos.count()
        atualizados = 0
        
        for produto in produtos:
            # Calcula estoque total dos lotes disponíveis
            estoque_lotes = Lote.objects.filter(
                produto=produto,
                status='DISPONIVEL'
            ).aggregate(
                total=Sum('quantidade_atual')
            )['total'] or 0
            
            # Atualiza o estoque_atual se houver diferença
            if produto.estoque_atual != estoque_lotes:
                produto.estoque_atual = estoque_lotes
                produto.save(update_fields=['estoque_atual'])
                atualizados += 1
                
                self.stdout.write(
                    f'  ✓ {produto.nome}: {produto.estoque_atual} → {estoque_lotes}'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nConcluído! {atualizados} de {total_produtos} produtos atualizados.'
            )
        )
