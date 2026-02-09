"""
Management command para importar defensivos em empresas.

Uso:
    python manage.py seed_defensivos --all              # Todas as empresas
    python manage.py seed_defensivos --empresa-id 5     # Empresa específica
    python manage.py seed_defensivos --list             # Listar defensivos
"""

from django.core.management.base import BaseCommand, CommandError
from empresas.models import Empresa
from produtos.defensivos_seed import seed_defensivos_for_empresa, listar_defensivos_seed


class Command(BaseCommand):
    help = 'Importa defensivos agrícolas (MAPA) em empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Importa em TODAS as empresas sem defensivos',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='Importa em empresa específica (ID)',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='Lista todos os defensivos disponíveis',
        )

    def handle(self, *args, **options):
        # Opção 1: Listar defensivos
        if options['list']:
            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS('📋 DEFENSIVOS DISPONÍVEIS (88 total)'))
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
            
            defensivos = listar_defensivos_seed()
            
            # Agrupar por classe agronômica
            classes = {}
            for d in defensivos:
                classe = d['classe_agronomica']
                if classe not in classes:
                    classes[classe] = []
                classes[classe].append(d)
            
            for classe in sorted(classes.keys()):
                defensivos_classe = classes[classe]
                self.stdout.write(self.style.HTTP_INFO(f"\n{classe} ({len(defensivos_classe)})"))
                self.stdout.write("-" * 60)
                
                for d in defensivos_classe:
                    self.stdout.write(
                        f"  • {d['nome_comercial']:<30} | {d['ingrediente_ativo']:<20} | "
                        f"{d['classe_toxicologica']} | {d['empresa_fabricante']}"
                    )
            
            self.stdout.write(self.style.SUCCESS('\n' + '='*60 + '\n'))
            return

        # Opção 2: Importar em empresa específica
        if options['empresa_id']:
            try:
                empresa = Empresa.objects.get(pk=options['empresa_id'])
                self.stdout.write(
                    self.style.SUCCESS(f'\n✅ Importando defensivos em: {empresa.nome_fantasia}...\n')
                )
                
                criados, ignorados = seed_defensivos_for_empresa(empresa)
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Criados: {criados}')
                )
                if ignorados > 0:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Ignorados (já existem): {ignorados}')
                    )
                self.stdout.write('')
                return
                
            except Empresa.DoesNotExist:
                raise CommandError(f'Empresa com ID {options["empresa_id"]} não encontrada')

        # Opção 3: Importar em todas as empresas
        if options['all']:
            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS('🌾 IMPORTADOR DE DEFENSIVOS'))
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
            
            empresas = Empresa.objects.all()
            
            if not empresas.exists():
                raise CommandError('Nenhuma empresa encontrada')
            
            total_criados = 0
            total_ignorados = 0
            
            for empresa in empresas:
                criados, ignorados = seed_defensivos_for_empresa(empresa)
                total_criados += criados
                total_ignorados += ignorados
                
                status = '✅' if criados > 0 else '⚠️'
                self.stdout.write(
                    f'{status} {empresa.nome_fantasia}: {criados} criados, {ignorados} ignorados'
                )
            
            self.stdout.write(self.style.SUCCESS('\n' + '='*60))
            self.stdout.write(self.style.SUCCESS(f'✅ SUCESSO!'))
            self.stdout.write(f'  Total criado: {total_criados}')
            self.stdout.write(f'  Total ignorado: {total_ignorados}')
            self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
            return

        # Nenhuma opção especificada
        self.stdout.write(self.style.ERROR('\n❌ Use uma das opções:'))
        self.stdout.write('  --all           : Importa em todas as empresas')
        self.stdout.write('  --empresa-id ID : Importa em empresa específica')
        self.stdout.write('  --list          : Lista defensivos disponíveis')
        self.stdout.write('')
