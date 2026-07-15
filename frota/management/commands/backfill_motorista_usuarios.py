from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from frota.services.motorista_portal import gerar_username_motorista


class Command(BaseCommand):
    help = (
        'Cria uma conta Usuario (login unificado) para cada Motorista que já tem PIN definido '
        'e ainda não está vinculado. Idempotente — seguro rodar mais de uma vez.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Só reporta o que seria feito, não grava nada.')

    def handle(self, *args, **options):
        from django.contrib.auth.models import Group
        from usuarios.models import Usuario
        from frota.models import Motorista

        dry_run = options['dry_run']
        elegveis = Motorista.objects.filter(usuario_vinculado__isnull=True).exclude(pin='').exclude(matricula='')

        migrados = 0
        pulados = 0
        falhas = []

        for motorista in elegveis:
            username = gerar_username_motorista(motorista.empresa_id, motorista.matricula)

            if Usuario.objects.filter(username=username).exists():
                falhas.append((motorista, username, 'username já em uso por outro Usuario'))
                continue

            nome_partes = motorista.nome.strip().split(' ', 1)
            first_name = nome_partes[0]
            last_name = nome_partes[1] if len(nome_partes) > 1 else ''

            if dry_run:
                self.stdout.write(f'[dry-run] criaria Usuario username="{username}" para Motorista #{motorista.pk} "{motorista.nome}"')
                migrados += 1
                continue

            try:
                with transaction.atomic():
                    usuario = Usuario(
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        empresa=motorista.empresa,
                        tipo='MOTORISTA',
                        is_active=motorista.ativo,
                    )
                    usuario.password = motorista.pin  # hash já no formato Django — sem re-hash
                    usuario.save()

                    grupo, _ = Group.objects.get_or_create(name='MOTORISTA')
                    usuario.groups.add(grupo)

                    motorista.usuario_vinculado = usuario
                    motorista.save(update_fields=['usuario_vinculado'])
            except IntegrityError as exc:
                falhas.append((motorista, username, str(exc)))
                continue

            migrados += 1
            self.stdout.write(self.style.SUCCESS(
                f'Motorista #{motorista.pk} "{motorista.nome}" -> Usuario username="{username}"'
            ))

        ja_migrados = Motorista.objects.filter(usuario_vinculado__isnull=False).count()
        pulados = ja_migrados

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Migrados nesta execução: {migrados}'))
        self.stdout.write(f'Já migrados anteriormente (total no banco): {pulados}')

        if falhas:
            self.stdout.write(self.style.ERROR(f'\nFalhas ({len(falhas)}):'))
            for motorista, username, motivo in falhas:
                self.stdout.write(self.style.ERROR(
                    f'  - Motorista #{motorista.pk} "{motorista.nome}" (matrícula="{motorista.matricula}", '
                    f'username tentado="{username}"): {motivo}'
                ))
            raise SystemExit(1)
