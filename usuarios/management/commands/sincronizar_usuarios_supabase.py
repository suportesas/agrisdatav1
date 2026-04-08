"""
Management command para sincronizar usuarios Django com Supabase Auth
Sincroniza usuarios existentes criando-os no Supabase e registrando na tabela bridge
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
import logging
import string
import secrets

from core.supabase_config import SupabaseAuth
from usuarios.models_supabase import SupabaseUsuarioSync

logger = logging.getLogger(__name__)
Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Sincroniza usuarios Django com Supabase Auth'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--preview',
            action='store_true',
            dest='preview',
            help='Apenas mostra o que seria sincronizado (sem fazer nada)'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            dest='reset',
            help='Remove sincronizacoes antigas e comeca do zero'
        )
        parser.add_argument(
            '--email',
            type=str,
            dest='email',
            help='Sincroniza apenas um usuario pelo email'
        )
        parser.add_argument(
            '--username',
            type=str,
            dest='username',
            help='Sincroniza apenas um usuario pelo username'
        )
        parser.add_argument(
            '--no-email-notification',
            action='store_true',
            dest='no_email',
            help='Nao envia notificacao de senha ao criar no Supabase'
        )
        parser.add_argument(
            '--strategy',
            type=str,
            choices=['create_with_temp_password', 'register_only', 'bridge_only'],
            default='bridge_only',
            help='Estrategia de sincronizacao'
        )
    
    def generate_temp_password(self, length=16) -> str:
        """Gera senha temporaria segura"""
        chars = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    def handle(self, *args, **options):
        # Validacao de configuracao
        try:
            auth = SupabaseAuth()
        except ValueError as e:
            raise CommandError(
                f'ERRO de configuracao Supabase: {str(e)}\n'
                'Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY em .env'
            )
        
        # Opcoes
        preview = options['preview']
        reset = options.get('reset', False)
        email_filter = options.get('email')
        username_filter = options.get('username')
        no_email = options.get('no_email', False)
        strategy = options.get('strategy', 'bridge_only')
        
        # ──────────────────────────────────────────────────────────────
        # PASSO 1: Filtrar usuarios
        # ──────────────────────────────────────────────────────────────
        usuarios = Usuario.objects.filter(is_active=True)
        
        if email_filter:
            usuarios = usuarios.filter(email__iexact=email_filter)
        elif username_filter:
            usuarios = usuarios.filter(username__iexact=username_filter)
        
        total = usuarios.count()
        
        if total == 0:
            self.stdout.write(
                self.style.WARNING('[AVISO] Nenhum usuario encontrado para sincronizar')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'\n[INFO] Encontrados {total} usuario(s) para sincronizar\n')
        )
        
        # ──────────────────────────────────────────────────────────────
        # PASSO 2: Mostrar preview se solicitado
        # ──────────────────────────────────────────────────────────────
        if preview:
            self.stdout.write(self.style.WARNING('[PREVIEW] Modo visao (sem fazer mudancas)\n'))
            self._mostrar_preview(usuarios, strategy)
            return
        
        # ──────────────────────────────────────────────────────────────
        # PASSO 3: Reset de sincronizacoes antigas (se solicitado)
        # ──────────────────────────────────────────────────────────────
        if reset:
            confirmacao = input('[AVISO] Deletar todas as sincronizacoes antigas? (s/N): ')
            if confirmacao.lower() == 's':
                SupabaseUsuarioSync.objects.all().delete()
                self.stdout.write(self.style.WARNING('[OK] Sincronizacoes antigas deletadas\n'))
        
        # ──────────────────────────────────────────────────────────────
        # PASSO 4: Executar sincronizacao
        # ──────────────────────────────────────────────────────────────
        resultado = {
            'sucesso': 0,
            'erro': 0,
            'ja_sincronizado': 0,
            'erros_lista': []
        }
        
        for usuario in usuarios:
            try:
                sync_record = None
                try:
                    sync_record = usuario.supabase_sync
                except SupabaseUsuarioSync.DoesNotExist:
                    sync_record = None

                # Se ja sincronizado de fato, pula
                if sync_record and sync_record.sincronizado and not sync_record.supabase_uid.startswith('pending_'):
                    self.stdout.write(
                        self.style.WARNING(f'[SKIP] {usuario.email} - ja sincronizado')
                    )
                    resultado['ja_sincronizado'] += 1
                    continue
                
                # Executar estrategia
                if strategy == 'create_with_temp_password':
                    self._sincronizar_com_senha_temporaria(
                        usuario, auth, resultado, no_email, sync_record=sync_record
                    )
                elif strategy == 'bridge_only':
                    self._sincronizar_apenas_bridge(usuario, resultado)
                
            except Exception as e:
                resultado['erro'] += 1
                resultado['erros_lista'].append((usuario.email, str(e)))
                self.stdout.write(
                    self.style.ERROR(f'[ERRO] {usuario.email} - {str(e)}')
                )
                logger.error(f'Erro sincronizando {usuario.email}: {str(e)}')
        
        # ──────────────────────────────────────────────────────────────
        # PASSO 5: Relatorio final
        # ──────────────────────────────────────────────────────────────
        self._exibir_relatorio(resultado)
    
    def _mostrar_preview(self, usuarios, strategy: str):
        """Mostra preview do que seria sincronizado"""
        self.stdout.write('=' * 60)
        self.stdout.write('PREVIEW DE SINCRONIZACAO')
        self.stdout.write('=' * 60 + '\n')
        
        for i, usuario in enumerate(usuarios, 1):
            sync_record = None
            try:
                sync_record = usuario.supabase_sync
            except SupabaseUsuarioSync.DoesNotExist:
                sync_record = None

            if not sync_record:
                status = '[OK] Sera sincronizado'
            elif sync_record.supabase_uid.startswith('pending_'):
                status = '[PENDING] Bridge sera convertido'
            else:
                status = '[SKIP] Ja sincronizado'
            self.stdout.write(f'{i:2}. {usuario.email:40} -> {status}')
        
        self.stdout.write('\n' + self.style.SUCCESS('Execute sem --preview para confirmar a acao'))
    
    def _sincronizar_com_senha_temporaria(
        self, usuario, auth: SupabaseAuth, resultado: dict, no_email: bool, sync_record=None
    ):
        """Sincroniza criando no Supabase com senha temporaria"""
        senha_temp = self.generate_temp_password()
        
        # Criar no Supabase Auth
        response = auth.admin_create_user(
            email=usuario.email,
            password=senha_temp,
            user_metadata={
                'username': usuario.username,
                'empresa_id': usuario.empresa.id if usuario.empresa else None,
                'tipo': usuario.tipo,
            },
            email_confirm=not no_email  # Envia email de confirmacao
        )
        
        if 'error' in response:
            raise Exception(f"Supabase: {response['error']}")
        
        # Registrar ou atualizar sincronizacao
        supabase_uid = response['user'].id
        if sync_record:
            sync_record.supabase_uid = supabase_uid
            sync_record.sincronizado = True
            sync_record.erro_sincronizacao = ''
            sync_record.save(update_fields=['supabase_uid', 'sincronizado', 'erro_sincronizacao', 'ultima_sincronizacao'])
        else:
            SupabaseUsuarioSync.objects.create(
                usuario=usuario,
                supabase_uid=supabase_uid,
                sincronizado=True
            )
        
        resultado['sucesso'] += 1
        self.stdout.write(
            self.style.SUCCESS(f'[OK] {usuario.email} - sincronizado (UID: {supabase_uid[:8]}...)')
        )
        
        # Log
        log_msg = f'Criado em Supabase com senha: {senha_temp}'
        if no_email:
            log_msg += ' (email nao enviado)'
        logger.info(f'{usuario.email}: {log_msg}')
    
    def _sincronizar_apenas_bridge(self, usuario: Usuario, resultado: dict):
        """
        Apenas registra que sera sincronizado (sem criar no Supabase ainda)
        Util para preparar a infraestrutura antes de criar contas Supabase
        """
        # Gera um UID simulado (sera substituido depois)
        tentativa = 1
        while SupabaseUsuarioSync.objects.filter(
            supabase_uid__startswith=f'pending_{usuario.id}'
        ).exists():
            tentativa += 1
        
        supabase_uid = f'pending_{usuario.id}_{tentativa}'
        
        SupabaseUsuarioSync.objects.create(
            usuario=usuario,
            supabase_uid=supabase_uid,
            sincronizado=False,
            erro_sincronizacao='Aguardando criacao em Supabase'
        )
        
        resultado['sucesso'] += 1
        self.stdout.write(
            self.style.SUCCESS(f'[OK] {usuario.email} - bridge registrado (aguardando Supabase)')
        )
        logger.info(f'{usuario.email}: Bridge registrado, aguardando criacao no Supabase')
    
    def _exibir_relatorio(self, resultado: dict):
        """Exibe relatorio final da sincronizacao"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('RELATORIO DE SINCRONIZACAO')
        self.stdout.write('=' * 60 + '\n')
        
        self.stdout.write(
            self.style.SUCCESS(f'[OK] Sincronizados com sucesso: {resultado["sucesso"]}')
        )
        self.stdout.write(
            self.style.WARNING(f'[SKIP] Ja estavam sincronizados: {resultado["ja_sincronizado"]}')
        )
        if resultado['erro'] > 0:
            self.stdout.write(
                self.style.ERROR(f'[ERRO] Erros: {resultado["erro"]}')
            )
            self.stdout.write('\nDetalhes dos erros:')
            for email, erro in resultado['erros_lista']:
                self.stdout.write(f'  - {email}: {erro}')
        
        total = resultado['sucesso'] + resultado['ja_sincronizado'] + resultado['erro']
        self.stdout.write(f'\n[INFO] Total processado: {total} usuario(s)\n')
        
        if resultado['sucesso'] > 0:
            self.stdout.write(self.style.SUCCESS(
                '[OK] Sincronizacao concluida com sucesso!\n'
            ))
            self.stdout.write('Proximas etapas:')
            self.stdout.write('1. Verifique em Supabase Dashboard > Authentication > Users')
            self.stdout.write('2. Comunique aos usuarios sobre o novo login Supabase')
            self.stdout.write('3. Configure autenticacao de 2FA se necessario')
