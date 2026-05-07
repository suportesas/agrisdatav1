from django.core.management.base import BaseCommand
from django.db import transaction
from cadastros.models import Requisicao


class Command(BaseCommand):
    help = 'Deleta todas as requisicoes e seus itens. Use apenas em ambiente de testes.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Lista o que seria deletado sem executar.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        qs = Requisicao.objects.all()
        total = qs.count()

        if total == 0:
            self.stdout.write('Nenhuma requisicao encontrada.')
            return

        for req in qs.order_by('numero'):
            n_itens = req.itens.count() if hasattr(req, 'itens') else 0
            self.stdout.write(f'  {req.numero} | Tipo: {req.tipo} | Status: {req.status} | Itens: {n_itens}')

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\n[DRY RUN] {total} requisicao(oes) seriam deletadas. Execute sem --dry-run para confirmar.'
            ))
            return

        with transaction.atomic():
            qs.delete()

        self.stdout.write(self.style.SUCCESS(f'\nConcluido: {total} requisicao(oes) deletadas.'))
