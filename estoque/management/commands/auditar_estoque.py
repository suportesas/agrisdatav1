import logging
from django.core.management.base import BaseCommand
from django.db.models import Sum
from produtos.models import Produto
from estoque.models import Lote
from decimal import Decimal

logger = logging.getLogger('estoque.auditoria')

class Command(BaseCommand):
    help = 'Valida divergências entre saldo físico (lotes) e saldo lógico (estoque_atual) dos produtos.'

    def handle(self, *args, **options):
        divergencias = []
        for produto in Produto.objects.filter(controla_estoque=True, ativo=True):
            total_lotes = Lote.objects.filter(
                produto=produto,
                status__in=['DISPONIVEL', 'BLOQUEADO']
            ).aggregate(total=Sum('quantidade_atual'))['total'] or Decimal('0')
            if produto.estoque_atual != total_lotes:
                divergencias.append((produto.id, produto.nome, float(produto.estoque_atual), float(total_lotes)))
                logger.warning(f"Divergência: Produto {produto.id} - {produto.nome} | estoque_atual={produto.estoque_atual} | lotes={total_lotes}")
        if divergencias:
            self.stdout.write(self.style.WARNING(f"Foram encontradas {len(divergencias)} divergências de estoque!"))
            for pid, nome, est, lot in divergencias:
                self.stdout.write(f"Produto {pid} - {nome}: estoque_atual={est} | lotes={lot}")
        else:
            self.stdout.write(self.style.SUCCESS("Nenhuma divergência encontrada. Estoque consistente."))
