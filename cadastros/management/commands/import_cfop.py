import csv
import os
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from cadastros.models import CFOP, EmpresaCFOP

DEFAULT_CSV = os.path.join(settings.BASE_DIR, 'CFOP_import.csv')


class Command(BaseCommand):
    help = 'Importa CFOPs do arquivo CFOP_import.csv (padrão) ou de outro arquivo CSV.'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, help='Caminho para o CSV (padrão: CFOP_import.csv na raiz do projeto)')
        parser.add_argument('--replace', action='store_true', help='Atualiza templates existentes quando diferentes')
        parser.add_argument('--apply_to_all_companies', action='store_true', help='Cria EmpresaCFOP para todas as empresas')
        parser.add_argument('--dry_run', action='store_true', help='Não persiste alterações')

    def handle(self, *args, **options):
        path = options.get('path') or DEFAULT_CSV
        replace = options.get('replace')
        apply_to_all = options.get('apply_to_all_companies')
        dry_run = options.get('dry_run')

        if not os.path.exists(path):
            self.stderr.write(f'Arquivo não encontrado: {path}')
            return

        created = 0
        updated = 0
        invalid = 0
        skipped = 0
        total = 0
        to_apply = []

        with open(path, newline='', encoding='utf-8') as fh:
            # Auto-detecta delimitador: se a primeira linha contém ';', usa ';'
            first_line = fh.readline()
            fh.seek(0)
            delimiter = ';' if ';' in first_line else ','
            # Detecta formato pelo cabeçalho: 'cfop' = novo formato; 'codigo' = legado
            new_format = 'cfop' in first_line.lower()
            reader = csv.DictReader(fh, delimiter=delimiter)

            for r in reader:
                total += 1
                if new_format:
                    # Formato CFOP_import.csv: cfop;descricao;tipo;natureza
                    raw_codigo = (r.get('cfop') or '').strip()
                    nome = (r.get('descricao') or '').strip()
                else:
                    # Formato legado: codigo,nome,descricao
                    raw_codigo = (r.get('codigo') or '').strip()
                    nome = (r.get('nome') or r.get('Nome') or '').strip()

                codigo = re.sub(r'\D', '', raw_codigo)
                tipo = (r.get('tipo') or '').strip().upper()

                # Ignora linhas de grupo/subgrupo — não são CFOPs utilizáveis
                if tipo in ('GRUPO', 'SUBGRUPO'):
                    skipped += 1
                    continue

                if not (2 <= len(codigo) <= 4):
                    invalid += 1
                    self.stdout.write(f'Inválido: {raw_codigo} - {nome}')
                    continue

                cf = CFOP.objects.filter(codigo=codigo).first()
                if cf:
                    if replace and cf.nome != nome:
                        if not dry_run:
                            cf.nome = nome
                            cf.save(update_fields=['nome', 'atualizado_em'])
                        updated += 1
                        prefix = 'Atualizado (dry-run)' if dry_run else 'Atualizado'
                        self.stdout.write(f'{prefix}: {codigo} - {nome}')
                else:
                    if not dry_run:
                        cf = CFOP.objects.create(codigo=codigo, nome=nome, ativo=True)
                    created += 1
                    prefix = 'Criado (dry-run)' if dry_run else 'Criado'
                    self.stdout.write(f'{prefix}: {codigo} - {nome}')

                if apply_to_all and not dry_run and cf is not None:
                    to_apply.append(cf)

        if apply_to_all and not dry_run and to_apply:
            from empresas.models import Empresa
            empresas = list(Empresa.objects.all())
            applied = 0
            for e in empresas:
                for cf in to_apply:
                    try:
                        _, flag = EmpresaCFOP.objects.get_or_create(
                            empresa=e,
                            codigo=cf.codigo,
                            defaults={'nome': cf.nome, 'descricao': cf.descricao, 'ativo': cf.ativo, 'template': cf}
                        )
                        if flag:
                            applied += 1
                    except Exception as exc:
                        self.stderr.write(f'Erro EmpresaCFOP empresa={e.pk} codigo={cf.codigo}: {exc}')
            self.stdout.write(f'EmpresaCFOPs criados: {applied}')

        self.stdout.write(
            f'Importação concluída. Total lido: {total} | '
            f'Criados: {created} | Atualizados: {updated} | '
            f'Inválidos: {invalid} | Grupos ignorados: {skipped} | '
            f'(dry_run={dry_run})'
        )
