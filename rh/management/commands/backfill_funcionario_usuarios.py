from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction


class Command(BaseCommand):
    help = (
        'Cria uma conta Usuario (login unificado) para cada Funcionario que já tem PIN definido '
        'e ainda não está vinculado. Idempotente — seguro rodar mais de uma vez.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Só reporta o que seria feito, não grava nada.')

    def handle(self, *args, **options):
        from django.contrib.auth.models import Group
        from usuarios.models import Usuario
        from rh.models import Funcionario
        from rh.services.funcionario_portal import gerar_username_funcionario

        dry_run = options['dry_run']
        elegveis = Funcionario.objects.filter(usuario_vinculado__isnull=True).exclude(pin_portal='')

        migrados = 0
        falhas = []

        for funcionario in elegveis:
            username = gerar_username_funcionario(funcionario.empresa_id, funcionario.cpf)

            if Usuario.objects.filter(username=username).exists():
                falhas.append((funcionario, username, 'username já em uso por outro Usuario'))
                continue

            nome_partes = funcionario.nome_completo.strip().split(' ', 1)
            first_name = nome_partes[0]
            last_name = nome_partes[1] if len(nome_partes) > 1 else ''

            if dry_run:
                self.stdout.write(f'[dry-run] criaria Usuario username="{username}" para Funcionario #{funcionario.pk} "{funcionario.nome_completo}"')
                migrados += 1
                continue

            try:
                with transaction.atomic():
                    usuario = Usuario(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        empresa=funcionario.empresa,
                        tipo='FUNC_CAMPO',
                        is_active=funcionario.ativo,
                    )
                    usuario.password = funcionario.pin_portal  # hash já no formato Django — sem re-hash
                    usuario.save()

                    grupo, _ = Group.objects.get_or_create(name='FUNC_CAMPO')
                    usuario.groups.add(grupo)

                    funcionario.usuario_vinculado = usuario
                    funcionario.save(update_fields=['usuario_vinculado'])
            except IntegrityError as exc:
                falhas.append((funcionario, username, str(exc)))
                continue

            migrados += 1
            self.stdout.write(self.style.SUCCESS(
                f'Funcionario #{funcionario.pk} "{funcionario.nome_completo}" -> Usuario username="{username}"'
            ))

        ja_migrados = Funcionario.objects.filter(usuario_vinculado__isnull=False).count()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Migrados nesta execução: {migrados}'))
        self.stdout.write(f'Já migrados anteriormente (total no banco): {ja_migrados}')

        if falhas:
            self.stdout.write(self.style.ERROR(f'\nFalhas ({len(falhas)}):'))
            for funcionario, username, motivo in falhas:
                self.stdout.write(self.style.ERROR(
                    f'  - Funcionario #{funcionario.pk} "{funcionario.nome_completo}" '
                    f'(username tentado="{username}"): {motivo}'
                ))
            raise SystemExit(1)
