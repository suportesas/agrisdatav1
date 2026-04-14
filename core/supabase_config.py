"""
Configuração e cliente Supabase
Fornece métodos para autenticação com Email/Senha e Google
"""

import os
from supabase import create_client, Client
from django.conf import settings
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Cliente singleton para Supabase"""
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Retorna instância única do cliente Supabase"""
        if cls._instance is None:
            url = settings.SUPABASE_URL
            key = settings.SUPABASE_ANON_KEY
            
            if not url or not key:
                raise ValueError(
                    "SUPABASE_URL e SUPABASE_ANON_KEY não configurados em .env"
                )
            
            cls._instance = create_client(url, key)
            logger.info("[OK] Supabase cliente inicializado")
        
        return cls._instance


class SupabaseAuth:
    """
    Adapter de autenticação Supabase
    Fornece métodos para login/register com suporte a múltiplos provedores
    """
    
    def __init__(self):
        self.client = SupabaseClient.get_client()
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
    
    # ═══════════════════ AUTENTICAÇÃO COM EMAIL/SENHA ═══════════════════
    
    def register_with_email(
        self, 
        email: str, 
        password: str, 
        user_metadata: Dict = None
    ) -> Dict:
        """
        Registra novo usuário com email/senha no Supabase Auth
        
        Args:
            email: Email do usuário
            password: Senha (mín 6 caracteres)
            user_metadata: Dados adicionais (nome, empresa_id, etc)
        
        Returns:
            {'user': user_obj, 'session': session_obj} ou {'error': msg}
        """
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata or {}
                }
            })
            logger.info(f"[OK] Usuario registrado: {email}")
            return {
                'user': response.user,
                'session': response.session
            }
        except Exception as e:
            logger.error(f"[ERRO] Erro ao registrar {email}: {str(e)}")
            return {'error': str(e)}
    
    def login_with_email(
        self, 
        email: str, 
        password: str
    ) -> Dict:
        """
        Faz login com email/senha
        
        Returns:
            {'user': user_obj, 'session': session_obj} ou {'error': msg}
        """
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            logger.info(f"[OK] Login bem-sucedido: {email}")
            return {
                'user': response.user,
                'session': response.session
            }
        except Exception as e:
            logger.error(f"[ERRO] Erro ao fazer login {email}: {str(e)}")
            return {'error': str(e)}
    
    def logout(self) -> bool:
        """Faz logout do usuário atual"""
        try:
            self.client.auth.sign_out()
            return True
        except:
            return False
    
    # ═══════════════════ SIGN-IN SOCIAL (GOOGLE, etc) ═══════════════════
    
    def get_google_oauth_url(self, redirect_url: str) -> str:
        """
        Retorna URL para o flow de OAuth do Google
        
        Args:
            redirect_url: URL de callback (ex: http://localhost:8000/auth/callback)
        
        Returns:
            URL para redirecionar o usuário
        """
        try:
            response = self.client.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirectTo": redirect_url
                }
            })
            return response.url if hasattr(response, 'url') else None
        except Exception as e:
            logger.error(f"[ERRO] Erro ao gerar URL Google OAuth: {str(e)}")
            return None
    
    # ═══════════════════ GERENCIAMENTO DE USUÁRIOS ═══════════════════
    
    def get_user(self, access_token: str) -> Dict:
        """Retorna dados do usuário autenticado"""
        try:
            response = self.client.auth.get_user(access_token)
            return response.user.dict() if response.user else None
        except Exception as e:
            logger.error(f"[ERRO] Erro ao obter usuario: {str(e)}")
            return None
    
    def update_user(self, access_token: str, data: Dict) -> Dict:
        """Atualiza dados do usuário (exceto email/password)"""
        try:
            response = self.client.auth.update_user(access_token, data)
            return response.user.dict() if response.user else None
        except Exception as e:
            logger.error(f"[ERRO] Erro ao atualizar usuario: {str(e)}")
            return {'error': str(e)}
    
    def reset_password(self, email: str) -> Dict:
        """Envia email para reset de senha"""
        try:
            response = self.client.auth.reset_password_for_email(email)
            return {'success': True}
        except Exception as e:
            logger.error(f"[ERRO] Erro ao enviar reset: {str(e)}")
            return {'error': str(e)}
    
    # ═══════════════════ JWT / TOKENS ═══════════════════
    
    def refresh_session(self, refresh_token: str) -> Dict:
        """Renova a sessão usando refresh token"""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            return {
                'session': response.session,
                'user': response.user
            }
        except Exception as e:
            logger.error(f"[ERRO] Erro ao renovar sessao: {str(e)}")
            return {'error': str(e)}
    
    # ═══════════════════ ADMIN OPERATIONS (service role) ═══════════════════
    
    def admin_create_user(
        self,
        email: str,
        password: str = None,
        user_metadata: Dict = None,
        email_confirm: bool = False
    ) -> Dict:
        """
        Admin: Cria usuário sem enviar email de confirmação
        Requer SERVICE_ROLE_KEY
        """
        try:
            client = create_client(settings.SUPABASE_URL, self.service_key)
            response = client.auth.admin.create_user({
                "email": email,
                "password": password,
                "user_metadata": user_metadata or {},
                "email_confirm": email_confirm
            })
            return {'user': response.user}
        except Exception as e:
            logger.error(f"[ERRO] Erro ao criar user admin: {str(e)}")
            return {'error': str(e)}
    
    def admin_delete_user(self, user_id: str) -> Dict:
        """Admin: Deleta um usuário"""
        try:
            client = create_client(settings.SUPABASE_URL, self.service_key)
            response = client.auth.admin.delete_user(user_id)
            return {'success': True}
        except Exception as e:
            logger.error(f"[ERRO] Erro ao deletar user: {str(e)}")
            return {'error': str(e)}

    def admin_update_user_password(self, user_id: str, password: str) -> Dict:
        """Admin: Atualiza senha de um usuário"""
        try:
            client = create_client(settings.SUPABASE_URL, self.service_key)
            response = client.auth.admin.update_user_by_id(
                user_id,
                {"password": password}
            )
            return {'success': True, 'user': response.user if hasattr(response, 'user') else None}
        except Exception as e:
            logger.error(f"[ERRO] Erro ao atualizar senha user_id={user_id}: {str(e)}")
            return {'error': str(e)}

    def admin_find_user_by_email(self, email: str) -> Dict:
        """Admin: Busca usuário no Supabase Auth por e-mail."""
        try:
            client = create_client(settings.SUPABASE_URL, self.service_key)
            page = 1
            per_page = 200

            while True:
                response = client.auth.admin.list_users(page=page, per_page=per_page)
                users = getattr(response, 'users', None) or []

                for user in users:
                    if getattr(user, 'email', '').lower() == email.lower():
                        return {'user': user}

                # Se retornou menos que o tamanho da página, acabou a listagem.
                if len(users) < per_page:
                    break

                page += 1

            return {'user': None}
        except Exception as e:
            logger.error(f"[ERRO] Erro ao buscar usuário por email={email}: {str(e)}")
            return {'error': str(e)}

    def admin_upsert_user(
        self,
        email: str,
        password: str,
        user_metadata: Dict = None,
        email_confirm: bool = True
    ) -> Dict:
        """
        Admin: cria usuário no Supabase quando não existe; se existir, atualiza senha/metadata.
        """
        try:
            found = self.admin_find_user_by_email(email)
            if 'error' in found:
                return found

            existing_user = found.get('user')
            client = create_client(settings.SUPABASE_URL, self.service_key)

            if existing_user is None:
                created = self.admin_create_user(
                    email=email,
                    password=password,
                    user_metadata=user_metadata,
                    email_confirm=email_confirm,
                )
                if 'error' in created:
                    return created
                return {'user': created.get('user'), 'created': True}

            payload = {
                'password': password,
                'user_metadata': user_metadata or {},
            }
            updated = client.auth.admin.update_user_by_id(existing_user.id, payload)
            return {
                'user': getattr(updated, 'user', None) or existing_user,
                'created': False,
            }
        except Exception as e:
            logger.error(f"[ERRO] Erro no upsert de usuário admin email={email}: {str(e)}")
            return {'error': str(e)}


# Instância global para uso
supabase_auth = SupabaseAuth()
supabase_client = SupabaseClient.get_client()
