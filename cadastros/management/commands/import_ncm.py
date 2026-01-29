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
        parser.add_argument('--apply-to-all-companies', action='store_true', help='Após importar templates, cria cópias para todas as empresas (EmpresaNCM)')
        parser.add_argument('--company-id', type=int, help='Aplica templates apenas para uma empresa específica (id)')

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

        # Decode content once
        text_str = content.decode('utf-8', errors='replace')

        # Try JSON first (file may be JSON export)
        rows = None
        try:
            import json
            parsed = json.loads(text_str)
            if isinstance(parsed, list):
                # expected list of objects
                rows = parsed
            elif isinstance(parsed, dict) and isinstance(parsed.get('data'), list):
                # allow { "data": [...] } formats
                rows = parsed.get('data')
        except Exception:
            rows = None

        # If not JSON, fall back to CSV parsing
        if rows is None:
            # Try to detect encoding and delimiter for CSV
            sample = text_str[:8192]
            sniffer = csv.Sniffer()
            dialect = None
            try:
                dialect = sniffer.sniff(sample)
                delim = dialect.delimiter
            except Exception:
                # fallback to comma
                delim = ','

            text = io.StringIO(text_str)
            reader = csv.DictReader(text, delimiter=delim)
            rows = list(reader)

        if not rows:
            raise CommandError('Arquivo CSV/JSON não contém linhas')

        created = 0
        updated = 0
        invalid = 0
        codes_seen = set()

        if dry_run:
            self.stdout.write('[dry-run] Não serão feitas alterações no banco de dados')


        apply_to_all = options.get('apply_to_all_companies')
        company_id = options.get('company_id')

        # helper: normalized key lookup (remove accents, lower)
        import unicodedata
        def norm(s):
            if s is None:
                return ''
            s = str(s)
            s = s.replace('\ufeff', '')  # drop BOM if present
            s = unicodedata.normalize('NFKD', s)
            s = ''.join(ch for ch in s if not unicodedata.combining(ch))
            return s.lower().strip()

        def get_field(d, candidates):
            # direct keys
            for c in candidates:
                if c in d and d[c] is not None:
                    return str(d[c]).strip()
            # try normalized match
            norm_map = {norm(k): k for k in d.keys()}
            for c in candidates:
                if norm(c) in norm_map:
                    k = norm_map[norm(c)]
                    if d.get(k) is not None:
                        return str(d.get(k)).strip()
            # fallback any key that matches 'codigo' like pattern
            for k in d.keys():
                if norm(k) in ['codigo','cod','ncm','codigo_ncm','codigo_natural']:
                    if d.get(k) is not None:
                        return str(d.get(k)).strip()
            return ''

        with transaction.atomic():
            for r in rows:
                codigo = get_field(r, ['codigo','Codigo','CÓDIGO','cod','Código'])
                nome = get_field(r, ['nome','Nome','NOME','descricao','DESCRICAO','Descrição','Descrição'])
                cest = get_field(r, ['cest','CEST','cest'])
                if not codigo:
                    invalid += 1
                    continue
                # normalize codigo
                import re
                codigo_norm = re.sub(r'\D', '', codigo)
                # Some source files use hierarchical codes like '01' or '01.01' which are not full NCMs
                # We only accept full 8-digit NCM codes
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

            # Optionally remove templates not in file
            if replace and not dry_run:
                to_remove = NCM.objects.exclude(codigo__in=list(codes_seen))
                removed_count = to_remove.count()
                to_remove.delete()
                self.stdout.write(f'Removidos {removed_count} NCMs não presentes no arquivo')

            # Optionally apply templates to company lists
            if (apply_to_all or company_id) and not dry_run:
                from empresas.models import Empresa
                from cadastros.tasks import seed_ncms_for_company
                empresas = []
                if apply_to_all:
                    empresas = list(Empresa.objects.all())
                elif company_id:
                    empresas = list(Empresa.objects.filter(pk=company_id))

                if empresas:
                    for e in empresas:
                        self.stdout.write(f'Aplicando templates para empresa {e}... (async)')
                        # Use existing seeder (bulk + chunked) to avoid per-row creates
                        try:
                            # run synchronously here, it uses bulk_create internally
                            res = seed_ncms_for_company(e.pk)
                            self.stdout.write(f"  Criados {res.get('created',0)} NCMs para {e} (empresa), pulados {res.get('skipped',0)}")
                        except Exception as exc:
                            self.stdout.write(f'  Erro ao popular para {e}: {exc}')


        self.stdout.write(self.style.SUCCESS(f'Import concluído: {created} criados, {updated} atualizados, {invalid} inválidos'))
