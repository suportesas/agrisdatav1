from django.core.management.base import BaseCommand
from cadastros.models import CFOP, EmpresaCFOP
from empresas.models import Empresa

class Command(BaseCommand):
    help = 'Popula os CFOPs padrões para todas as empresas já existentes.'

    def handle(self, *args, **options):
        total_empresas = 0
        total_cfops = 0
        empresas = Empresa.objects.all()
        templates = CFOP.objects.filter(ativo=True)
        for empresa in empresas:
            bulk = []
            for t in templates:
                if not EmpresaCFOP.objects.filter(empresa=empresa, codigo=t.codigo).exists():
                    bulk.append(EmpresaCFOP(
                        empresa=empresa,
                        codigo=t.codigo,
                        nome=t.nome,
                        descricao=t.descricao,
                        ativo=t.ativo,
                        template=t
                    ))
            if bulk:
                EmpresaCFOP.objects.bulk_create(bulk)
                total_cfops += len(bulk)
            total_empresas += 1
        self.stdout.write(self.style.SUCCESS(f'CFOPs populados para {total_empresas} empresas. Novos CFOPs criados: {total_cfops}'))
