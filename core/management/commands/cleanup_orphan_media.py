import shutil
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = 'Identifica arquivos órfãos na pasta media e opcionalmente move para quarentena fora do MEDIA_ROOT.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true', help='Move os órfãos para quarentena. Sem esta flag roda em dry-run.')
        parser.add_argument('--limit', type=int, default=0, help='Limita a quantidade de órfãos listados/processados.')
        parser.add_argument('--backup-dir', default='', help='Diretório de destino para quarentena. Padrão: BASE_DIR/media_orphan_backup/<timestamp>/')

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        limit = options['limit'] or 0
        execute = options['execute']
        backup_dir = options['backup_dir']

        referenced_files = self._collect_referenced_files()
        media_files = [path for path in media_root.rglob('*') if path.is_file()]

        orphan_files = []
        missing_files = []
        for file_path in media_files:
            rel_path = file_path.relative_to(media_root).as_posix()
            if rel_path not in referenced_files:
                orphan_files.append(file_path)

        for ref in sorted(referenced_files):
            if not (media_root / ref).exists():
                missing_files.append(ref)

        if limit:
            orphan_files = orphan_files[:limit]
            missing_files = missing_files[:limit]

        self.stdout.write(f'Orfaos encontrados: {len(orphan_files)}')
        self.stdout.write(f'Referencias no banco sem arquivo local: {len(missing_files)}')

        for ref in missing_files:
            self.stdout.write(self.style.WARNING(f'MISSING_LOCAL {ref}'))

        if not orphan_files:
            self.stdout.write(self.style.SUCCESS('Nenhum arquivo órfão para processar.'))
            return

        if not execute:
            for file_path in orphan_files:
                self.stdout.write(f'DRY-RUN ORPHAN {file_path.relative_to(media_root).as_posix()}')
            self.stdout.write(self.style.SUCCESS('Dry-run concluído. Nenhum arquivo foi movido.'))
            return

        if not backup_dir:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_root = Path(settings.BASE_DIR) / 'media_orphan_backup' / timestamp
        else:
            backup_root = Path(backup_dir)

        moved = 0
        for file_path in orphan_files:
            rel_path = file_path.relative_to(media_root)
            destination = backup_root / rel_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(destination))
            moved += 1
            self.stdout.write(f'MOVED {rel_path.as_posix()} -> {destination}')

        self.stdout.write(self.style.SUCCESS(f'Arquivos movidos para quarentena: {moved}'))
        self.stdout.write(self.style.SUCCESS(f'Backup em: {backup_root}'))

    def _collect_referenced_files(self):
        referenced = set()
        for model in apps.get_models():
            file_fields = [
                field for field in model._meta.get_fields()
                if isinstance(field, (models.FileField, models.ImageField))
            ]
            if not file_fields:
                continue

            for instance in model._default_manager.all().iterator():
                for field in file_fields:
                    value = getattr(instance, field.name, None)
                    name = getattr(value, 'name', '') or ''
                    if not name or str(name).startswith(('http://', 'https://')):
                        continue
                    referenced.add(str(name).replace('\\', '/'))
        return referenced