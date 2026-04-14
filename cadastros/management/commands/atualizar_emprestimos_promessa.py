from datetime import date

from django.core.management.base import BaseCommand

from cadastros.models import EmprestimoProdutor


class Command(BaseCommand):
    help = 'Converte automaticamente empréstimos com promessa vencida para status de empréstimo normal.'

    def handle(self, *args, **options):
        hoje = date.today()
        pendentes = EmprestimoProdutor.objects.filter(
            status='PROMESSA',
            data_promessa_devolucao__lt=hoje,
        ).exclude(saldo_pendente__lte=0)

        total = 0
        for emprestimo in pendentes:
            emprestimo.status = 'NORMAL'
            emprestimo.save(update_fields=['status', 'saldo_pendente', 'atualizado_em'])
            total += 1

        self.stdout.write(self.style.SUCCESS(f'{total} empréstimo(s) convertidos para NORMAL.'))
