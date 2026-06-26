from django.core.management.base import BaseCommand
from django.utils import timezone
from drawback.models import AtoConcessorio


class Command(BaseCommand):
    help = 'Vence ACs expirados e envia alertas de vencimento próximo'

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        vencidos = AtoConcessorio.objects.filter(status='ATIVO').select_related('empresa')

        total_vencidos = 0
        total_alertas = 0

        for ac in vencidos:
            data_fim = ac.data_fim_efetiva
            if data_fim < hoje:
                ac.status = 'VENCIDO'
                ac.save(update_fields=['status'])
                total_vencidos += 1
                self.stdout.write(self.style.WARNING(
                    f'AC {ac.numero_ac} ({ac.empresa}) marcado como VENCIDO (venceu em {data_fim:%d/%m/%Y})'
                ))
            elif (data_fim - hoje).days <= 30:
                total_alertas += 1
                self.stdout.write(self.style.NOTICE(
                    f'AC {ac.numero_ac} ({ac.empresa}) vence em {(data_fim - hoje).days} dias ({data_fim:%d/%m/%Y})'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Concluído: {total_vencidos} ACs vencidos, {total_alertas} ACs com alerta de vencimento próximo.'
        ))
