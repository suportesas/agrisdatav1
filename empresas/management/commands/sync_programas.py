from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sincroniza a tabela Programa varrendo todas as URLs nomeadas do sistema'

    def handle(self, *args, **options):
        from empresas.programa_discovery import sincronizar_programas

        stats = sincronizar_programas()

        self.stdout.write(self.style.SUCCESS(
            f"Programas sincronizados: {stats['criados']} criados, "
            f"{stats['atualizados']} atualizados, {stats['desativados']} desativados."
        ))
