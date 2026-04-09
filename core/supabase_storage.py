"""
Custom Storage Backend para usar Supabase Storage com Django
Permite que ImageField use o Supabase automaticamente
"""

import os
from django.core.files.storage import Storage
from django.conf import settings
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


class SupabaseStorage(Storage):
    """Storage backend customizado para Supabase"""
    
    def __init__(self, bucket_name='uploads-gerais'):
        self.bucket_name = bucket_name
        try:
            from core.supabase_config import supabase_auth
            self.client = supabase_auth.client
            self.enabled = settings.SUPABASE_STORAGE_ENABLED
        except Exception as e:
            logger.warning(f"Supabase Storage não disponível: {e}")
            self.client = None
            self.enabled = False
    
    def _open(self, name, mode='rb'):
        """Abre arquivo do Supabase Storage"""
        if not self.enabled or not self.client:
            raise IOError(f"Supabase Storage não disponível")
        
        try:
            data = self.client.storage.from_(self.bucket_name).download(name)
            return ContentFile(data)
        except Exception as e:
            logger.error(f"Erro ao baixar {name} do Supabase: {e}")
            raise IOError(f"Não foi possível baixar {name}")
    
    def _save(self, name, content):
        """Salva arquivo no Supabase Storage"""
        if not self.enabled or not self.client:
            logger.warning("Supabase Storage desativado, salvando localmente")
            from django.core.files.storage import default_storage
            return default_storage._save(name, content)
        
        try:
            # Preparar conteúdo
            if hasattr(content, 'read'):
                file_content = content.read()
            else:
                file_content = content
            
            # Detectar content-type
            content_type = self._get_content_type(name)
            
            # Upload para Supabase
            self.client.storage.from_(self.bucket_name).upload(
                name,
                file_content,
                {
                    'contentType': content_type,
                    'upsert': 'true',
                }
            )
            
            logger.info(f"Arquivo salvo no Supabase: {name}")
            return name
            
        except Exception as e:
            logger.error(f"Erro ao salvar {name} no Supabase: {e}")
            raise IOError(f"Não foi possível salvar {name}")
    
    def delete(self, name):
        """Deleta arquivo do Supabase Storage"""
        if not self.enabled or not self.client:
            logger.warning("Supabase Storage desativado")
            return
        
        try:
            self.client.storage.from_(self.bucket_name).remove([name])
            logger.info(f"Arquivo deletado do Supabase: {name}")
        except Exception as e:
            logger.error(f"Erro ao deletar {name} do Supabase: {e}")
    
    def exists(self, name):
        """Verifica se arquivo existe"""
        if not self.enabled or not self.client:
            return False
        
        try:
            # Tentar fazer download (se não existir, vai gerar erro)
            self.client.storage.from_(self.bucket_name).download(name)
            return True
        except:
            return False
    
    def listdir(self, path):
        """Lista diretório"""
        if not self.enabled or not self.client:
            return [], []
        
        try:
            files = self.client.storage.from_(self.bucket_name).list(path)
            dirs = [f['name'] for f in files if f.get('metadata') is None]
            file_names = [f['name'] for f in files if f.get('metadata') is not None]
            return dirs, file_names
        except:
            return [], []
    
    def size(self, name):
        """Retorna tamanho do arquivo"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            # Baixar e verificar tamanho
            data = self.client.storage.from_(self.bucket_name).download(name)
            return len(data) if data else 0
        except:
            return 0
    
    def url(self, name):
        """Retorna URL pública do arquivo"""
        if not self.enabled or not self.client:
            return f"/media/{name}"
        
        try:
            url = self.client.storage.from_(self.bucket_name).get_public_url(name)
            return url['publicUrl'] if isinstance(url, dict) else url
        except Exception as e:
            logger.error(f"Erro ao obter URL para {name}: {e}")
            return f"/media/{name}"
    
    def get_accessed_time(self, name):
        """Retorna tempo de acesso (não implementado obrigatoriamente)"""
        return None
    
    def get_created_time(self, name):
        """Retorna tempo de criação (não implementado obrigatoriamente)"""
        return None
    
    def get_modified_time(self, name):
        """Retorna tempo de modificação (não implementado obrigatoriamente)"""
        return None
    
    @staticmethod
    def _get_content_type(file_path):
        """Detecta content-type pelo arquivo"""
        import mimetypes
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'
