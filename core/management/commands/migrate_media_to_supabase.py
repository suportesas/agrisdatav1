import os

from django.apps import apps
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import models


class Command(BaseCommand):
    help = 'Migra arquivos legados da pasta media para o storage padrão configurado (Supabase).'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='Executa a migração. Sem esta flag roda em dry-run.')
        parser.add_argument('--limit', type=int, default=0, help='Limita a quantidade de arquivos processados.')
        parser.add_argument('--delete-local', action='store_true', help='Remove o arquivo local após migrar com sucesso.')
        parser.add_argument('--app', dest='app_labels', action='append', default=[], help='Restringe a migração a um app label específico. Pode ser repetido.')

    def handle(self, *args, **options):
        if not getattr(settings, 'SUPABASE_STORAGE_USE_AS_DEFAULT', False):
            raise CommandError('SUPABASE_STORAGE_USE_AS_DEFAULT precisa estar habilitado para migrar arquivos para o Supabase.')

        execute = options['execute']
        limit = options['limit'] or 0
        delete_local = options['delete_local']
        app_labels = set(options['app_labels'] or [])

        counters = {
            'found': 0,
            'migrated': 0,
            'skipped_remote': 0,
            'missing_local': 0,
            'errors': 0,
        }

        for model in apps.get_models():
            if app_labels and model._meta.app_label not in app_labels:
                continue

            file_fields = [
                field for field in model._meta.get_fields()
                if isinstance(field, (models.FileField, models.ImageField))
            ]
            if not file_fields:
                continue

            queryset = model._default_manager.all().iterator()
            for instance in queryset:
                for field in file_fields:
                    if limit and counters['found'] >= limit:
                        self._print_summary(counters, execute)
                        return

                    field_file = getattr(instance, field.name, None)
                    file_name = getattr(field_file, 'name', '') or ''
                    if not file_name:
                        continue
                    if str(file_name).startswith(('http://', 'https://')):
                        counters['skipped_remote'] += 1
                        continue

                    if default_storage.exists(file_name):
                        counters['skipped_remote'] += 1
                        self.stdout.write(f'SKIP remoto existente: {model._meta.label}.{field.name} #{instance.pk} -> {file_name}')
                        continue

                    counters['found'] += 1
                    local_path = os.path.join(settings.MEDIA_ROOT, file_name)

                    if not os.path.exists(local_path):
                        counters['missing_local'] += 1
                        self.stdout.write(self.style.WARNING(
                            f'AUSENTE local: {model._meta.label}.{field.name} #{instance.pk} -> {file_name}'
                        ))
                        continue

                    self.stdout.write(f"{'MIGRATE' if execute else 'DRY-RUN'} {model._meta.label}.{field.name} #{instance.pk} -> {file_name}")
                    if not execute:
                        continue

                    try:
                        with open(local_path, 'rb') as local_handle:
                            saved_name = default_storage.save(file_name, File(local_handle, name=os.path.basename(file_name)))

                        model._default_manager.filter(pk=instance.pk).update(**{field.name: saved_name})
                        counters['migrated'] += 1

                        if delete_local:
                            try:
                                os.remove(local_path)
                            except OSError:
                                pass
                    except Exception as exc:
                        counters['errors'] += 1
                        self.stdout.write(self.style.ERROR(
                            f'ERRO {model._meta.label}.{field.name} #{instance.pk} -> {file_name}: {exc}'
                        ))

        self._print_summary(counters, execute)

    def _print_summary(self, counters, execute):
        mode = 'EXECUCAO' if execute else 'DRY-RUN'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Resumo da migracao ({mode})'))
        self.stdout.write(f"Arquivos encontrados: {counters['found']}")
        self.stdout.write(f"Migrados: {counters['migrated']}")
        self.stdout.write(f"Ignorados (ja remotos): {counters['skipped_remote']}")
        self.stdout.write(f"Ausentes localmente: {counters['missing_local']}")
        self.stdout.write(f"Erros: {counters['errors']}")