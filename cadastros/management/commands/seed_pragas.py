"""
Management command para popular pragas pré-definidas em empresas
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from empresas.models import Empresa
from cadastros.pragas_seed import seed_pragas_for_company


class Command(BaseCommand):
    help = 'Popula pragas pré-definidas em uma ou todas as empresas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID da empresa específica para popular'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Popula todas as empresas'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            default=True,
            help='Pula empresas que já têm pragas (padrão: True)'
        )
    
    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        populate_all = options.get('all')
        skip_existing = options.get('skip_existing')
        
        # Determinar qual(is) empresa(s) processar
        if empresa_id:
            try:
                empresas = [Empresa.objects.get(pk=empresa_id)]
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Empresa com ID {empresa_id} não encontrada')
                )
                return
        elif populate_all:
            empresas = Empresa.objects.all()
        else:
            self.stdout.write(
                self.style.ERROR(
                    '❌ Use --empresa-id <id> ou --all para especificar qual(is) empresa(s) popular'
                )
            )
            return
        
        total_criadas = 0
        total_ignoradas = 0
        
        for empresa in empresas:
            # Se skip_existing, verifica se já tem pragas
            if skip_existing:
                from cadastros.models import Praga
                if Praga.objects.filter(empresa=empresa).exists():
                    self.stdout.write(
                        f"⏭️  {empresa.nome}: Já possui pragas cadastradas, pulando..."
                    )
                    continue
            
            self.stdout.write(f"🌾 Processando: {empresa.nome}...", ending=' ')
            
            criadas, ignoradas = seed_pragas_for_company(empresa)
            total_criadas += criadas
            total_ignoradas += ignoradas
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {criadas} pragas criadas, {ignoradas} ignoradas'
                )
            )
        
        # Resumo final
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f'✅ Total de pragas criadas: {total_criadas}'))
        self.stdout.write(f'⏭️  Total de pragas ignoradas: {total_ignoradas}')
        self.stdout.write("="*60)
