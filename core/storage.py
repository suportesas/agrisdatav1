"""
Helper para Supabase Storage
Gerencia uploads de arquivos para Supabase Storage

Uso:
    from core.storage import storage_helper
    url = storage_helper.upload_file(file_obj, 'empresas-logos', 'empresa1/logo.jpg')
"""

import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SupabaseStorageHelper:
    """Helper para gerenciar uploads no Supabase Storage"""
    
    def __init__(self):
        try:
            from core.supabase_config import supabase_auth
            self.client = supabase_auth.client
            self.enabled = settings.SUPABASE_STORAGE_ENABLED
        except Exception as e:
            logger.warning(f"Supabase Storage não disponível: {e}")
            self.client = None
            self.enabled = False
    
    def upload_file(self, file_obj, bucket_name, file_path):
        """
        Upload de arquivo para Supabase Storage
        
        Args:
            file_obj: Objeto de arquivo (FileField, InMemoryUploadedFile)
            bucket_name: Nome do bucket (ex: 'empresas-logos')
            file_path: Caminho do arquivo no bucket (ex: 'empresa1/2026/04/logo.jpg')
        
        Returns:
            URL pública do arquivo ou None se falhar
        """
        try:
            if not self.enabled or not self.client:
                logger.warning("Supabase Storage desativado")
                return None
            
            # Ler arquivo
            if hasattr(file_obj, 'read'):
                content = file_obj.read()
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
            else:
                content = file_obj
            
            # Detectar content-type
            content_type = self._get_content_type(file_path)
            
            # Upload
            self.client.storage.from_(bucket_name).upload(
                file_path,
                content,
                {
                    'contentType': content_type,
                    'upsert': True,
                }
            )
            
            # Retornar URL pública
            url = self.client.storage.from_(bucket_name).get_public_url(file_path)
            logger.info(f"OK: Upload {file_path} em bucket {bucket_name}")
            return url
            
        except Exception as e:
            logger.error(f"ERRO no upload para Supabase: {str(e)}")
            return None
    
    def delete_file(self, bucket_name, file_path):
        """Deleta arquivo do Supabase Storage"""
        try:
            if not self.enabled or not self.client:
                return False
            
            self.client.storage.from_(bucket_name).remove([file_path])
            logger.info(f"Arquivo deletado: {file_path} do bucket {bucket_name}")
            return True
        except Exception as e:
            logger.error(f"ERRO ao deletar arquivo: {str(e)}")
            return False
    
    def get_public_url(self, bucket_name, file_path):
        """Obtém URL pública do arquivo"""
        try:
            if not self.enabled or not self.client:
                return None
            
            url = self.client.storage.from_(bucket_name).get_public_url(file_path)
            return url
        except Exception as e:
            logger.error(f"ERRO ao obter URL: {str(e)}")
            return None
    
    def _get_content_type(self, file_path):
        """Detecta o tipo MIME do arquivo"""
        ext = os.path.splitext(file_path)[1].lower()
        
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.zip': 'application/zip',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.xml': 'application/xml',
        }
        
        return mime_types.get(ext, 'application/octet-stream')


# Instância global
storage_helper = SupabaseStorageHelper()
