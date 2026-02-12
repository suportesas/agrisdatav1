"""
Mover logos existentes para o padrao por empresa.
"""
import os
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from empresas.models import Empresa


class Command(BaseCommand):
    help = 'Migrar logos existentes para empresas/logos/<empresa_id>/logo.ext'

    def handle(self, *args, **options):
        total = 0
        updated = 0
        skipped = 0
        missing = 0

        for empresa in Empresa.objects.exclude(logo=''):
            total += 1
            logo = empresa.logo
            if not logo or not getattr(logo, 'name', None):
                skipped += 1
                continue

            old_name = logo.name
            ext = os.path.splitext(old_name)[1] or '.png'
            new_name = f'empresas/logos/{empresa.id}/logo{ext}'

            if old_name == new_name:
                skipped += 1
                continue

            if not default_storage.exists(old_name):
                missing += 1
                self.stdout.write(self.style.WARNING(f'Missing file: {old_name}'))
                continue

            with default_storage.open(old_name, 'rb') as src:
                default_storage.save(new_name, ContentFile(src.read()))

            empresa.logo.name = new_name
            empresa.save(update_fields=['logo'])
            updated += 1

            try:
                if default_storage.exists(old_name):
                    default_storage.delete(old_name)
            except Exception:
                pass

        self.stdout.write(self.style.SUCCESS(f'Total: {total} | Atualizados: {updated} | Ignorados: {skipped} | Ausentes: {missing}'))
