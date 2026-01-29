import csv
import re
from django.core.management.base import BaseCommand
from cadastros.models import CFOP, EmpresaCFOP
from django.contrib.auth import get_user_model
from django.db import transaction


class Command(BaseCommand):
    help = 'Import CFOPs from a CSV file with columns: codigo,nome,descricao'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Path to CSV file')
        parser.add_argument('--replace', action='store_true', help='Replace existing templates when different')
        parser.add_argument('--apply_to_all_companies', action='store_true', help='Also create EmpresaCFOP copies for all companies')
        parser.add_argument('--dry_run', action='store_true', help='Do not persist changes')

    def handle(self, *args, **options):
        path = options.get('path')
        replace = options.get('replace')
        apply_to_all = options.get('apply_to_all_companies')
        dry_run = options.get('dry_run')

        if not path:
            self.stderr.write('Path is required')
            return

        created = 0
        updated = 0
        invalid = 0
        total = 0

        to_apply = []
        with open(path, newline='', encoding='utf-8') as fh:
            reader = csv.DictReader(fh)
            for r in reader:
                total += 1
                codigo = re.sub(r'\D','', (r.get('codigo') or ''))
                nome = (r.get('nome') or r.get('Nome') or '').strip()
                descricao = (r.get('descricao') or r.get('Descricao') or '').strip()

                if not (2 <= len(codigo) <= 4):
                    invalid += 1
                    self.stdout.write(f'Inválido: {codigo} - {nome}')
                    continue

                # Respect dry_run: do not persist changes when dry_run is True
                cf = CFOP.objects.filter(codigo=codigo).first()
                if cf:
                    # existing
                    if replace:
                        changed = False
                        if cf.nome != nome:
                            changed = True
                        if cf.descricao != descricao:
                            changed = True
                        if changed:
                            if dry_run:
                                updated += 1
                                self.stdout.write(f'Atualizar (dry-run): {codigo} - {nome}')
                            else:
                                cf.nome = nome
                                cf.descricao = descricao
                                cf.save()
                                updated += 1
                                self.stdout.write(f'Atualizado: {codigo} - {nome}')
                else:
                    if dry_run:
                        created += 1
                        self.stdout.write(f'Criado (dry-run): {codigo} - {nome}')
                    else:
                        cf = CFOP.objects.create(codigo=codigo, nome=nome, descricao=descricao, ativo=True)
                        created += 1
                        self.stdout.write(f'Criado: {codigo} - {nome}')

                # Collect to apply to companies (do later to avoid many small transactions)
                if apply_to_all and not dry_run and cf is not None:
                    to_apply.append(cf)

        # Apply templates to all companies in bulk-ish manner
        if apply_to_all and not dry_run and to_apply:
            from empresas.models import Empresa
            empresas = Empresa.objects.all()
            applied = 0
            for e in empresas:
                for cf in to_apply:
                    try:
                        obj, created_flag = EmpresaCFOP.objects.get_or_create(
                            empresa=e,
                            codigo=cf.codigo,
                            defaults={'nome': cf.nome, 'descricao': cf.descricao, 'ativo': cf.ativo, 'template': cf}
                        )
                        if created_flag:
                            applied += 1
                    except Exception as exc:
                        # Don't stop the whole import for one failure
                        self.stderr.write(f'Erro criando EmpresaCFOP for empresa={e.pk} codigo={cf.codigo}: {exc}')
            self.stdout.write(f'EmpresaCFOPs criados: {applied}')

        self.stdout.write(f'Import concluído. Total: {total} Criados: {created} Atualizados: {updated} Inválidos: {invalid} (dry_run={dry_run})')
