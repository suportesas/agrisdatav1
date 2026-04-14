"""
Comando para garantir um superusuário global (Django + Supabase Auth).

Objetivo:
- Criar/atualizar superusuário no banco do Django.
- Criar/atualizar o mesmo usuário no Supabase Auth.
- Registrar sincronização na tabela bridge SupabaseUsuarioSync.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
import os

from core.supabase_config import SupabaseAuth
from usuarios.models_supabase import SupabaseUsuarioSync


Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Garante e sincroniza um superusuário global entre Django e Supabase Auth.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username do superuser')
        parser.add_argument('--email', type=str, help='E-mail do superuser')
        parser.add_argument('--password', type=str, help='Senha do superuser')
        parser.add_argument(
            '--from-env',
            action='store_true',
            help='Usa DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e DJANGO_SUPERUSER_PASSWORD'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Somente valida os dados e mostra o que seria feito'
        )

    def handle(self, *args, **options):
        self._validate_database_is_centralized()

        username, email, password = self._resolve_credentials(options)

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Nenhuma alteração será aplicada.'))
            self.stdout.write(f'Username: {username}')
            self.stdout.write(f'Email: {email}')
            self.stdout.write('Ações previstas:')
            self.stdout.write('1) Criar/atualizar superuser no Django')
            self.stdout.write('2) Upsert no Supabase Auth')
            self.stdout.write('3) Atualizar bridge em usuarios_supabaseusuariosync')
            return

        auth = self._get_supabase_auth()

        with transaction.atomic():
            usuario, created_local = self._upsert_django_superuser(
                username=username,
                email=email,
                password=password,
            )

            metadata = {
                'username': usuario.username,
                'django_user_id': usuario.id,
                'is_superuser': True,
                'is_staff': True,
                'tipo': usuario.tipo,
            }

            supabase_result = auth.admin_upsert_user(
                email=email,
                password=password,
                user_metadata=metadata,
                email_confirm=True,
            )
            if 'error' in supabase_result:
                raise CommandError(f"Falha no Supabase Auth: {supabase_result['error']}")

            supabase_user = supabase_result.get('user')
            if not supabase_user:
                raise CommandError('Supabase Auth não retornou usuário no upsert.')

            bridge, _ = SupabaseUsuarioSync.objects.update_or_create(
                usuario=usuario,
                defaults={
                    'supabase_uid': supabase_user.id,
                    'sincronizado': True,
                    'erro_sincronizacao': '',
                }
            )

        self.stdout.write(self.style.SUCCESS('[OK] Superuser global sincronizado com sucesso.'))
        self.stdout.write(f"- Django: {'criado' if created_local else 'atualizado'} ({usuario.username})")
        self.stdout.write(
            f"- Supabase Auth: {'criado' if supabase_result.get('created') else 'atualizado'} ({email})"
        )
        self.stdout.write(f"- Bridge UID: {bridge.supabase_uid}")

    def _validate_database_is_centralized(self):
        engine = settings.DATABASES['default']['ENGINE']
        if 'postgresql' not in engine:
            raise CommandError(
                'Banco atual não é PostgreSQL/Supabase. '\
                'Para acesso global em qualquer computador, use banco centralizado.'
            )

    def _resolve_credentials(self, options):
        from_env = options.get('from_env', False)

        username = options.get('username')
        email = options.get('email')
        password = options.get('password')

        if from_env:
            username = username or os.getenv('DJANGO_SUPERUSER_USERNAME')
            email = email or os.getenv('DJANGO_SUPERUSER_EMAIL')
            password = password or os.getenv('DJANGO_SUPERUSER_PASSWORD')

        missing = []
        if not username:
            missing.append('username')
        if not email:
            missing.append('email')
        if not password:
            missing.append('password')

        if missing:
            raise CommandError(
                'Parâmetros obrigatórios ausentes: '
                f"{', '.join(missing)}. "
                'Use --username --email --password ou --from-env com variáveis definidas.'
            )

        return username, email, password

    def _get_supabase_auth(self):
        try:
            return SupabaseAuth()
        except ValueError as exc:
            raise CommandError(
                f'Configuração Supabase inválida: {exc}. '\
                'Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env.'
            )

    def _upsert_django_superuser(self, username, email, password):
        usuario, created = Usuario.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
                'tipo': 'ADMIN',
            }
        )

        # Garante privilégios de superuser e senha atualizada.
        usuario.email = email
        usuario.is_active = True
        usuario.is_staff = True
        usuario.is_superuser = True
        if hasattr(usuario, 'tipo'):
            usuario.tipo = 'ADMIN'
        usuario.set_password(password)
        usuario.save()

        return usuario, created
