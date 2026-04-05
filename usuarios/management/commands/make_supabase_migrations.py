"""
Management command para criar migrações de Supabase
python manage.py make_supabase_migrations
"""

from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection
from django.db.migrations.writer import MigrationWriter
from django.db.migrations.questioner import InteractiveMigrationQuestioner
from django.db.migrations.loader import MigrationLoader
from django.utils.decorators import no_migrations


class Command(BaseCommand):
    help = 'Cria migrações para sincronização com Supabase'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula, não cria arquivos'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checando modelos Supabase...'))
        
        try:
            from usuarios.models_supabase import SupabaseUsuarioSync, LoginSupabase
            self.stdout.write(self.style.SUCCESS(
                '✓ Modelos encontrados: SupabaseUsuarioSync, LoginSupabase'
            ))
        except ImportError:
            self.stdout.write(self.style.ERROR(
                '✗ Modelos Supabase não encontrados. Instale supabase primeiro.'
            ))
            return
        
        # Emula makemigrations
        self.stdout.write(self.style.SUCCESS('\n● Executando: python manage.py makemigrations usuarios'))
        from django.core.management import call_command
        call_command('makemigrations', 'usuarios', dry_run=options['dry_run'])
        
        # Emula migrate
        self.stdout.write(self.style.SUCCESS('\n● Executando: python manage.py migrate usuarios'))
        call_command('migrate', 'usuarios')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Migrações Supabase criadas com sucesso!'))
        self.stdout.write(self.style.WARNING('\nPróximas etapas:\n'))
        self.stdout.write('1. Configure SUPABASE_URL e SUPABASE_ANON_KEY em .env\n')
        self.stdout.write('2. Execute as RLS policies em core/supabase_rls.sql\n')
        self.stdout.write('3. Configure Google OAuth no Supabase\n')
        self.stdout.write('4. Teste login em: http://localhost:8000/auth/register/\n')
