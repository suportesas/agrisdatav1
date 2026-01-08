from django.core.management.base import BaseCommand

DEFAULT_ROLES = [
    'Proprietário',
    'Almoxarife',
    'Operacional do Campo',
    'Financeiro',
    'Gerente',
    'Vendedor',
]


class Command(BaseCommand):
    help = 'Cria roles (funções) padrão para todas as empresas'

    def handle(self, *args, **options):
        from empresas.models import Empresa, Role

        empresas = Empresa.objects.all()
        if not empresas.exists():
            self.stdout.write(self.style.WARNING('Nenhuma empresa encontrada.'))
            return

        for empresa in empresas:
            for nome in DEFAULT_ROLES:
                role, created = Role.objects.get_or_create(
                    empresa=empresa,
                    name=nome,
                    defaults={'builtin': True}
                )
                if created:
                    role.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'Role "{nome}" criada para empresa "{empresa.nome}"'
                    ))
                else:
                    self.stdout.write(f'Role "{nome}" já existe em "{empresa.nome}"')

        self.stdout.write(self.style.SUCCESS('Processo de seed de roles finalizado.'))