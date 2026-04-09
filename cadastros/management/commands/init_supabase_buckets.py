"""
Comando Django para inicializar buckets do Supabase Storage
Usage: python manage.py init_supabase_buckets
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Inicializa buckets do Supabase Storage configurados no settings'

    def handle(self, *args, **options):
        try:
            from core.supabase_config import supabase_auth
            
            if not settings.SUPABASE_STORAGE_ENABLED:
                self.stdout.write(
                    self.style.WARNING('⚠️  Supabase Storage não habilitado (SUPABASE_URL não configurado)')
                )
                return
            
            client = supabase_auth.client
            buckets_config = settings.SUPABASE_STORAGE_BUCKETS
            
            self.stdout.write(f'\n📦 Validando buckets do Supabase Storage...\n')
            
            # Listar buckets existentes
            try:
                buckets = client.storage.list_buckets()
                existing_buckets = {b.name for b in buckets}
                self.stdout.write(self.style.SUCCESS(f'✓ Conectado ao Supabase Storage\n'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao conectar ao Supabase: {e}')
                )
                raise CommandError(str(e))
            
            # Validar/listar cada bucket configurado
            self.stdout.write(self.style.WARNING('Buckets Configurados:'))
            self.stdout.write('-' * 60)
            
            found = 0
            missing = []
            
            for bucket_name, description in buckets_config.items():
                if bucket_name in existing_buckets:
                    found += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✅ {bucket_name:25} {description}')
                    )
                else:
                    missing.append((bucket_name, description))
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️  {bucket_name:25} {description} (NÃO ENCONTRADO)')
                    )
            
            self.stdout.write('-' * 60)
            self.stdout.write(f'\n📊 Resumo:')
            self.stdout.write(f'   ✅ Buckets encontrados: {found}/{len(buckets_config)}')
            
            if missing:
                self.stdout.write(f'   ⚠️  Buckets faltando: {len(missing)}')
                self.stdout.write(f'\n❌ Buckets que precisam ser criados:')
                for bucket_name, description in missing:
                    self.stdout.write(f'   • {bucket_name} ({description})')
                
                self.stdout.write(f'\n🔧 Para criar os buckets, siga as opções:')
                self.stdout.write(f'   1. Via Console Supabase: Storage → Create Bucket')
                self.stdout.write(f'   2. Via CLI: supabase storage create <bucket_name>')
                self.stdout.write(f'   3. Solicite permissão de admin para criar buckets')
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ Todos os buckets estão configurados!'))
            
            self.stdout.write('')  # Linha vazia final
            
        except ImportError:
            raise CommandError('Supabase não está configurado no projeto')
        except Exception as e:
            raise CommandError(f'Erro ao inicializar buckets: {str(e)}')
