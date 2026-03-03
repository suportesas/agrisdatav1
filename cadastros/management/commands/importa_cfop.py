import csv
from django.core.management.base import BaseCommand
from cadastros.models import CFOP

class Command(BaseCommand):
    help = 'Importa todos os CFOPs do arquivo CFOP_import.csv para a tabela CFOP.'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='CFOP_import.csv', help='Caminho para o arquivo CSV de CFOPs')

    def handle(self, *args, **options):
        file_path = options['file']
        total = 0
        criados = 0
        with open(file_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            for row in reader:
                codigo = row.get('cfop', '').strip().replace('.', '')
                descricao = row.get('descricao', '').strip()
                tipo = row.get('tipo', '').strip()
                natureza = row.get('natureza', '').strip()
                nome = descricao  # O campo nome é obrigatório no modelo
                obs = f"Tipo: {tipo} | Natureza: {natureza}" if tipo or natureza else ''
                if 2 <= len(codigo) <= 4 and nome:
                    obj, created = CFOP.objects.get_or_create(
                        codigo=codigo,
                        defaults={
                            'nome': nome,
                            'descricao': obs,
                            'ativo': True
                        }
                    )
                    if created:
                        criados += 1
                    total += 1
        self.stdout.write(self.style.SUCCESS(f'Processados: {total} | Criados: {criados}'))
