import csv
from django.core.management.base import BaseCommand
from cadastros.models import NCM

class Command(BaseCommand):
    help = 'Importa todos os NCMs do arquivo NCM.csv para a tabela NCM.'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, default='NCM.csv', help='Caminho para o arquivo CSV de NCMs')

    def limpar_codigo(self, codigo_raw):
        # Extrai apenas dígitos do código e retorna os 8 primeiros
        codigo = ''.join(c for c in codigo_raw if c.isdigit())
        return codigo[:8] if len(codigo) >= 8 else None

    def handle(self, *args, **options):
        file_path = options['file']
        total = 0
        criados = 0
        with open(file_path, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                codigo = row.get('codigo', '').strip()
                nome = row.get('nome', '').strip()
                if len(codigo) == 8 and nome:
                    obj, created = NCM.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
                    if created:
                        criados += 1
                    total += 1
        self.stdout.write(self.style.SUCCESS(f'Processados: {total} | Criados: {criados}'))
