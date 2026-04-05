"""
Modelo de sincronização com Supabase Auth
Mantém usuários Django sincronizados com Supabase
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

Usuario = get_user_model()


class SupabaseUsuarioSync(models.Model):
    """
    Rastreia sincronização entre Django Usuario e Supabase Auth
    Cada record no Django tem um Supabase UID correspondente
    """
    
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        related_name='supabase_sync',
        verbose_name='Usuário Django'
    )
    
    supabase_uid = models.CharField(
        'Supabase UID',
        max_length=36,
        unique=True,
        db_index=True,
        help_text='ID único do usuário no Supabase Auth'
    )
    
    ultima_sincronizacao = models.DateTimeField(
        'Última Sincronização',
        auto_now=True,
        db_index=True
    )
    
    sincronizado = models.BooleanField(
        'Sincronizado',
        default=True,
        help_text='Se True, usuário está sincronizado com Supabase'
    )
    
    erro_sincronizacao = models.TextField(
        'Erro de Sincronização',
        blank=True,
        help_text='Mensagem de erro da última tentativa'
    )
    
    class Meta:
        verbose_name = 'Sincronização Supabase'
        verbose_name_plural = 'Sincronizações Supabase'
        indexes = [
            models.Index(fields=['usuario', '-ultima_sincronizacao']),
            models.Index(fields=['supabase_uid']),
        ]
    
    def __str__(self):
        return f"{self.usuario.email} → {self.supabase_uid[:8]}..."
    
    @staticmethod
    def get_by_supabase_uid(uid: str):
        """Encontra usuário por Supabase UID"""
        try:
            return SupabaseUsuarioSync.objects.get(supabase_uid=uid).usuario
        except SupabaseUsuarioSync.DoesNotExist:
            return None


class LoginSupabase(models.Model):
    """
    Auditoria: Registra todos os logins via Supabase
    Similar a LoginRegistro mas específico para Supabase
    """
    
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='logins_supabase',
        verbose_name='Usuário',
        null=True,
        blank=True
    )
    
    email = models.EmailField('Email utilizado')
    
    origem = models.CharField(
        'Origem do Login',
        max_length=20,
        choices=[
            ('email', 'Email/Senha'),
            ('google', 'Google OAuth'),
            ('github', 'GitHub OAuth'),
            ('outro', 'Outro'),
        ],
        default='email'
    )
    
    sucesso = models.BooleanField('Login com Sucesso', default=True)
    
    motivo_falha = models.CharField(
        'Motivo da Falha',
        max_length=100,
        blank=True,
        help_text='Ex: email_not_found, wrong_password, user_disabled'
    )
    
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    
    user_agent = models.CharField('User Agent', max_length=500, blank=True)
    
    timestamp = models.DateTimeField(
        'Data/Hora',
        auto_now_add=True,
        db_index=True
    )
    
    class Meta:
        verbose_name = 'Login Supabase'
        verbose_name_plural = 'Logins Supabase'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['email', '-timestamp']),
            models.Index(fields=['usuario', '-timestamp']),
        ]
    
    def __str__(self):
        status = "✓" if self.sucesso else "✗"
        return f"{status} {self.email} ({self.origem}) - {self.timestamp}"
