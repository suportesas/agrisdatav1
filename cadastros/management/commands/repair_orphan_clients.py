from django.core.management.base import BaseCommand, CommandError
from cadastros.models import Cliente
from empresas.models import Empresa

class Command(BaseCommand):
    help = 'Find and optionally repair orphaned Cliente records (empresa missing: NULL or points to non-existent empresa)'

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true', help='List orphaned clients (default)')
        parser.add_argument('--assign', type=int, help='Assign all orphaned clients to the given empresa id')
        parser.add_argument('--assign-by-name', type=str, help='Assign all orphaned clients to the empresa with the given name')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be changed but do not apply')
        parser.add_argument('--confirm', action='store_true', help='Confirm destructive operation (required to perform assignment)')

    def handle(self, *args, **options):
        # Orphans are clients where empresa relation is missing either because empresa_id is NULL
        # or because empresa_id points to a non-existent Empresa record.
        existing_emp_ids = list(Empresa.objects.values_list('pk', flat=True))
        if existing_emp_ids:
            orphans = Cliente.objects.filter(empresa__isnull=True) | Cliente.objects.exclude(empresa_id__in=existing_emp_ids)
        else:
            # If there are no empresas at all, treat all clients as orphaned
            orphans = Cliente.objects.all()

        count = orphans.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No orphaned clients found.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {count} orphaned client(s):'))
        for c in orphans:
            self.stdout.write(f' - id={c.pk} nome="{c.razao_social}" cnpj="{c.cnpj_cpf}" empresa_id={c.empresa_id}')

        assign_id = options.get('assign')
        assign_name = options.get('assign_by_name')
        dry_run = options.get('dry_run')
        confirm = options.get('confirm')

        if not assign_id and not assign_name:
            self.stdout.write(self.style.SUCCESS('Use --assign <empresa_id> or --assign-by-name "Name" to reassign these clients.'))
            return

        # Resolve empresa
        empresa = None
        if assign_id:
            try:
                empresa = Empresa.objects.get(pk=assign_id)
            except Empresa.DoesNotExist:
                raise CommandError(f'Empresa with id={assign_id} does not exist')
        else:
            try:
                empresa = Empresa.objects.get(nome=assign_name)
            except Empresa.DoesNotExist:
                raise CommandError(f'Empresa with name="{assign_name}" does not exist')

        self.stdout.write(self.style.NOTICE(f'Assigning {count} client(s) to empresa id={empresa.pk} nome="{empresa.nome}"'))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run mode: no changes will be made.'))
            return

        if not confirm:
            raise CommandError('Operation aborted: add --confirm to perform the assignment')

        # Perform assignment
        updated = orphans.update(empresa=empresa)
        self.stdout.write(self.style.SUCCESS(f'Successfully assigned {updated} client(s) to empresa id={empresa.pk}'))
