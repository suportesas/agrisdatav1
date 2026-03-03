from django.core.management.base import BaseCommand
from empresas.models import Empresa
from cadastros.tasks import seed_ncms_for_company
from cadastros.models import CFOP, EmpresaCFOP
from produtos.categoria_seed import seed_categorias_for_empresa

class Command(BaseCommand):
    help = 'Popula CFOPs, NCMs e Categorias padrão para todas as empresas já criadas.'

    def handle(self, *args, **options):
        empresas = Empresa.objects.all()
        total_empresas = empresas.count()
        self.stdout.write(f'Processando {total_empresas} empresas...')
        for empresa in empresas:
            # NCM
            res_ncm = seed_ncms_for_company(empresa.pk)
            self.stdout.write(f'NCMs: {res_ncm}')
            # CFOP
            templates = CFOP.objects.filter(ativo=True).order_by('codigo')
            bulk = []
            for t in templates:
                if not EmpresaCFOP.objects.filter(empresa=empresa, codigo=t.codigo).exists():
                    bulk.append(EmpresaCFOP(empresa=empresa, codigo=t.codigo, nome=t.nome, descricao=t.descricao, ativo=t.ativo, template=t))
            if bulk:
                EmpresaCFOP.objects.bulk_create(bulk)
                self.stdout.write(f'CFOPs criados para empresa {empresa}: {len(bulk)}')
            else:
                self.stdout.write(f'CFOPs já existentes para empresa {empresa}')
            # Categoria
            criados, ignorados = seed_categorias_for_empresa(empresa)
            self.stdout.write(f'Categorias: criados={criados}, ignorados={ignorados}')
        self.stdout.write(self.style.SUCCESS('População concluída para todas as empresas.'))
