from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cadastros.models import VinculoContrato


class Command(BaseCommand):
    help = 'Encerra vínculos com data_fim_prevista vencida e inativa o funcionário sem vínculo ativo.'

    def handle(self, *args, **options):
        hoje = timezone.now().date()
        vinculos = VinculoContrato.objects.filter(
            status__in=['ATIVO', 'PROGRAMADO'],
            data_fim_prevista__isnull=False,
            data_fim_prevista__lte=hoje,
            data_fim_real__isnull=True,
        ).select_related('funcionario')

        total = vinculos.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Nenhum vínculo vencido para encerrar.'))
            return

        encerrados = 0
        funcionarios_inativados = 0

        with transaction.atomic():
            for vinculo in vinculos:
                data_fim = vinculo.data_fim_prevista or hoje
                vinculo.data_fim_real = data_fim
                vinculo.status = 'ENCERRADO'
                vinculo.save(update_fields=['data_fim_real', 'status', 'data_atualizacao'])
                encerrados += 1

                funcionario = vinculo.funcionario
                possui_ativo = funcionario.vinculos.filter(status='ATIVO').exclude(pk=vinculo.pk).exists()
                if not possui_ativo:
                    funcionario.ativo = False
                    funcionario.data_demissao = data_fim
                    funcionario.save(update_fields=['ativo', 'data_demissao'])
                    funcionarios_inativados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Vínculos encerrados: {encerrados}. Funcionários inativados: {funcionarios_inativados}.'
            )
        )
