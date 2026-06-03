from django.core.management.base import BaseCommand
from produtos.natureza_operacao_seed import seed_naturezas_for_empresa, DEFAULT_NATUREZAS


class Command(BaseCommand):
    help = 'Cria as naturezas de operação padrão para todas as empresas (ou uma específica).'

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, help='ID da empresa (padrão: todas)')
        parser.add_argument('--replace', action='store_true',
                            help='Atualiza descrição/observações das naturezas existentes')

    def handle(self, *args, **options):
        from empresas.models import Empresa

        empresa_id = options.get('empresa_id')
        replace = options.get('replace')

        if empresa_id:
            empresas = Empresa.objects.filter(pk=empresa_id)
            if not empresas.exists():
                self.stderr.write(f'Empresa {empresa_id} não encontrada.')
                return
        else:
            empresas = Empresa.objects.all().order_by('nome')

        total_criados = 0
        total_atualizados = 0

        for empresa in empresas:
            criados = seed_naturezas_for_empresa(empresa)
            total_criados += criados

            if replace:
                from produtos.models import NaturezaOperacao
                atualizados = 0
                for n in DEFAULT_NATUREZAS:
                    updated = NaturezaOperacao.objects.filter(
                        empresa=empresa, codigo=n['codigo']
                    ).exclude(
                        descricao=n['descricao']
                    ).update(
                        descricao=n['descricao'],
                        observacoes=n.get('observacoes', ''),
                    )
                    atualizados += updated
                total_atualizados += atualizados
                self.stdout.write(
                    f'{empresa.nome}: {criados} criadas, {atualizados} atualizadas'
                )
            else:
                self.stdout.write(f'{empresa.nome}: {criados} criadas')

        self.stdout.write(self.style.SUCCESS(
            f'\nConcluído. Total criadas: {total_criados} | '
            f'Total atualizadas: {total_atualizados} | '
            f'Empresas processadas: {empresas.count()}'
        ))
