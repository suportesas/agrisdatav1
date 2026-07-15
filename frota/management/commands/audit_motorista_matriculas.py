from collections import defaultdict

from django.core.management.base import BaseCommand

from frota.services.motorista_portal import normalizar_matricula


class Command(BaseCommand):
    help = (
        'Audita colisões de matrícula (empresa, matrícula normalizada) antes do backfill '
        'de login unificado do motorista. Não altera dados — apenas relata.'
    )

    def handle(self, *args, **options):
        from frota.models import Motorista

        grupos = defaultdict(list)
        sem_matricula_com_pin = []

        for motorista in Motorista.objects.exclude(matricula='').select_related('empresa'):
            chave = (motorista.empresa_id, normalizar_matricula(motorista.matricula))
            grupos[chave].append(motorista)

        for motorista in Motorista.objects.filter(matricula='').exclude(pin=''):
            sem_matricula_com_pin.append(motorista)

        criticas = []
        avisos = []
        for (empresa_id, matricula_norm), motoristas in grupos.items():
            if len(motoristas) <= 1:
                continue
            com_pin = [m for m in motoristas if m.pin]
            if len(com_pin) > 1:
                criticas.append((empresa_id, matricula_norm, motoristas))
            else:
                avisos.append((empresa_id, matricula_norm, motoristas))

        if sem_matricula_com_pin:
            self.stdout.write(self.style.WARNING(
                f'\n{len(sem_matricula_com_pin)} motorista(s) com PIN definido mas sem matrícula (estado inconsistente):'
            ))
            for m in sem_matricula_com_pin:
                self.stdout.write(f'  - Motorista #{m.pk} "{m.nome}" (empresa {m.empresa_id})')

        if avisos:
            self.stdout.write(self.style.WARNING(
                f'\n{len(avisos)} colisão(ões) de matrícula sem PIN duplicado (não bloqueia o backfill, mas violará a constraint de unicidade):'
            ))
            for empresa_id, matricula_norm, motoristas in avisos:
                nomes = ', '.join(f'#{m.pk} "{m.nome}"' for m in motoristas)
                self.stdout.write(f'  - empresa={empresa_id} matricula="{matricula_norm}": {nomes}')

        if criticas:
            self.stdout.write(self.style.ERROR(
                f'\n{len(criticas)} colisão(ões) CRÍTICA(S) — mais de um motorista com PIN definido para a mesma (empresa, matrícula):'
            ))
            for empresa_id, matricula_norm, motoristas in criticas:
                nomes = ', '.join(f'#{m.pk} "{m.nome}"' for m in motoristas)
                self.stdout.write(f'  - empresa={empresa_id} matricula="{matricula_norm}": {nomes}')
            self.stdout.write(self.style.ERROR(
                '\nResolva manualmente (ajuste a matrícula de um dos motoristas) antes de rodar o backfill.'
            ))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS('\nNenhuma colisão crítica encontrada. Pode prosseguir com o backfill.'))
