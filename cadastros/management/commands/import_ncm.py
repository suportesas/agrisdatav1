from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from cadastros.models import NCM
import csv
import requests
import io
import os


class Command(BaseCommand):
    help = 'Importa uma lista de NCM a partir de CSV. As colunas aceitas: codigo, nome, cest (opcional)'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, help='URL do CSV para baixar')
        parser.add_argument('--path', type=str, help='Caminho local para arquivo CSV')
        parser.add_argument('--replace', action='store_true', help='Se definido, remove NCMs não presentes no arquivo')
        parser.add_argument('--dry-run', action='store_true', help='Roda sem salvar alterações')

    def handle(self, *args, **options):
        url = options.get('url')
        path = options.get('path')
        replace = options.get('replace')
        dry_run = options.get('dry_run')

        if not url and not path:
            raise CommandError('Forneça --url ou --path para o arquivo CSV')

        # Load CSV bytes
        if url:
            self.stdout.write(f'Baixando CSV de {url}...')
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                raise CommandError(f'Erro ao baixar URL: {resp.status_code}')
            content = resp.content
        else:
            if not os.path.exists(path):
                raise CommandError(f'Arquivo não encontrado: {path}')
            with open(path, 'rb') as fh:
                content = fh.read()

        # Try to detect encoding and delimiter
        sample = content[:8192].decode('utf-8', errors='replace')
        sniffer = csv.Sniffer()
        dialect = None
        try:
            dialect = sniffer.sniff(sample)
            delim = dialect.delimiter
        except Exception:
            # fallback to comma
            delim = ','

        text = io.StringIO(content.decode('utf-8', errors='replace'))
        reader = csv.DictReader(text, delimiter=delim)

        rows = list(reader)
        if not rows:
            raise CommandError('Arquivo CSV não contém linhas')

        created = 0
        updated = 0
        invalid = 0
        codes_seen = set()

        if dry_run:
            self.stdout.write('[dry-run] Não serão feitas alterações no banco de dados')

        with transaction.atomic():
            for r in rows:
                codigo = (r.get('codigo') or r.get('Codigo') or r.get('CÓDIGO') or r.get('cod') or '').strip()
                nome = (r.get('nome') or r.get('Nome') or r.get('DESCRICAO') or r.get('descricao') or r.get('nome_ncm') or '').strip()
                cest = (r.get('cest') or r.get('CEST') or '').strip()
                if not codigo:
                    invalid += 1
                    continue
                # normalize codigo
                import re
                codigo_norm = re.sub(r'\D', '', codigo)
                if len(codigo_norm) != 8:
                    invalid += 1
                    continue
                codes_seen.add(codigo_norm)
                if dry_run:
                    # don't touch DB
                    continue
                obj, created_flag = NCM.objects.update_or_create(
                    codigo=codigo_norm,
                    defaults={'nome': nome, 'cest': cest, 'ativo': True}
                )
                if created_flag:
                    created += 1
                else:
                    updated += 1

            if replace and not dry_run:
                # remove those not in file
                to_remove = NCM.objects.exclude(codigo__in=list(codes_seen))
                removed_count = to_remove.count()
                to_remove.delete()
                self.stdout.write(f'Removidos {removed_count} NCMs não presentes no arquivo')

        self.stdout.write(self.style.SUCCESS(f'Import concluído: {created} criados, {updated} atualizados, {invalid} inválidos'))
