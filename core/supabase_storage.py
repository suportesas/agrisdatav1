"""Backend de storage Django roteado para Supabase Storage."""

import mimetypes
import os
import posixpath
import logging
import unicodedata

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.text import get_valid_filename

logger = logging.getLogger(__name__)


class RoutedSupabaseStorage(Storage):
    """Storage backend que escolhe o bucket com base no path do arquivo."""

    def __init__(self, bucket_name=None):
        self.default_bucket = bucket_name or getattr(settings, 'SUPABASE_STORAGE_DEFAULT_BUCKET', 'uploads-gerais')
        self.enabled = bool(
            getattr(settings, 'SUPABASE_STORAGE_ENABLED', False)
            and getattr(settings, 'SUPABASE_STORAGE_USE_AS_DEFAULT', False)
            and getattr(settings, 'SUPABASE_URL', None)
        )
        self.client = None
        self.local_storage = FileSystemStorage(
            location=getattr(settings, 'MEDIA_ROOT', None),
            base_url=getattr(settings, 'MEDIA_URL', '/media/'),
        )

        if not self.enabled:
            return

        try:
            from supabase import create_client

            service_key = getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
            anon_key = getattr(settings, 'SUPABASE_ANON_KEY', None)
            key = service_key or anon_key
            if not key:
                raise ValueError('SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY não configurada')

            self.client = create_client(settings.SUPABASE_URL, key)
        except Exception as exc:
            logger.warning('Supabase Storage indisponível, mantendo fallback local: %s', exc)
            self.client = None
            self.enabled = False

    def deconstruct(self):
        """Permite que o Django serialize este storage nas migrations."""
        return ('core.supabase_storage.RoutedSupabaseStorage', [], {})

    def _open(self, name, mode='rb'):
        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            return self.local_storage._open(normalized_name, mode)

        bucket_name = self._get_bucket_name(normalized_name)
        try:
            data = self.client.storage.from_(bucket_name).download(normalized_name)
            return ContentFile(data, name=normalized_name)
        except Exception as exc:
            logger.error('Erro ao baixar %s do bucket %s: %s', normalized_name, bucket_name, exc)
            raise IOError(f'Não foi possível baixar {normalized_name}') from exc

    def _ensure_bucket_exists(self, bucket_name):
        """Cria ou corrige a visibilidade do bucket no Supabase."""
        should_be_public = bucket_name in getattr(settings, 'SUPABASE_STORAGE_PUBLIC_BUCKETS', set())
        try:
            bucket = self.client.storage.get_bucket(bucket_name)
            if getattr(bucket, 'public', None) != should_be_public:
                self.client.storage.update_bucket(bucket_name, options={'public': should_be_public})
                logger.info('Bucket "%s" atualizado para público=%s', bucket_name, should_be_public)
        except Exception:
            try:
                self.client.storage.create_bucket(bucket_name, options={'public': should_be_public})
                logger.info('Bucket "%s" criado no Supabase (público=%s)', bucket_name, should_be_public)
            except Exception as exc:
                logger.warning('Não foi possível criar bucket "%s": %s', bucket_name, exc)

    def _save(self, name, content):
        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            return self.local_storage._save(normalized_name, content)

        bucket_name = self._get_bucket_name(normalized_name)
        self._ensure_bucket_exists(bucket_name)
        try:
            content_type = getattr(content, 'content_type', None) or self._get_content_type(normalized_name)
            file_content = content.read() if hasattr(content, 'read') else content

            self.client.storage.from_(bucket_name).upload(
                normalized_name,
                file_content,
                {
                    'content-type': content_type,
                    'upsert': 'true',
                },
            )
            logger.info('Arquivo salvo no Supabase: %s (%s)', normalized_name, bucket_name)
            return normalized_name
        except Exception as exc:
            logger.error('Erro ao salvar %s no bucket %s: %s', normalized_name, bucket_name, exc)
            raise IOError(f'Não foi possível salvar {normalized_name}') from exc

    def delete(self, name):
        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            self.local_storage.delete(normalized_name)
            return

        bucket_name = self._get_bucket_name(normalized_name)
        try:
            self.client.storage.from_(bucket_name).remove([normalized_name])
        except Exception as exc:
            logger.error('Erro ao deletar %s do bucket %s: %s', normalized_name, bucket_name, exc)

    def exists(self, name):
        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            return self.local_storage.exists(normalized_name)

        bucket_name = self._get_bucket_name(normalized_name)
        directory, file_name = posixpath.split(normalized_name)
        try:
            files = self.client.storage.from_(bucket_name).list(directory or None)
            for item in files or []:
                if item.get('name') == file_name:
                    return True
            return False
        except Exception:
            return False

    def listdir(self, path):
        normalized_path = self._normalize_name(path)
        if not self.enabled or not self.client:
            return self.local_storage.listdir(normalized_path)

        bucket_name = self._get_bucket_name(normalized_path)
        try:
            files = self.client.storage.from_(bucket_name).list(normalized_path or None)
            dirs = []
            file_names = []
            for item in files or []:
                if item.get('id'):
                    file_names.append(item['name'])
                else:
                    dirs.append(item['name'])
            return dirs, file_names
        except Exception:
            return [], []

    def size(self, name):
        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            return self.local_storage.size(normalized_name)

        bucket_name = self._get_bucket_name(normalized_name)
        directory, file_name = posixpath.split(normalized_name)
        try:
            files = self.client.storage.from_(bucket_name).list(directory or None)
            for item in files or []:
                if item.get('name') == file_name:
                    metadata = item.get('metadata') or {}
                    size = metadata.get('size')
                    return int(size or 0)
            return 0
        except Exception:
            return 0

    def url(self, name):
        if not name:
            return ''
        if str(name).startswith(('http://', 'https://')):
            return name

        normalized_name = self._normalize_name(name)
        if not self.enabled or not self.client:
            return self.local_storage.url(normalized_name)

        bucket_name = self._get_bucket_name(normalized_name)
        try:
            if bucket_name in getattr(settings, 'SUPABASE_STORAGE_PUBLIC_BUCKETS', set()):
                url = self.client.storage.from_(bucket_name).get_public_url(normalized_name)
                return url['publicUrl'] if isinstance(url, dict) else url

            signed = self.client.storage.from_(bucket_name).create_signed_url(
                normalized_name,
                getattr(settings, 'SUPABASE_STORAGE_SIGNED_URL_TTL', 3600),
            )
            if isinstance(signed, dict):
                return signed.get('signedURL') or signed.get('signedUrl') or signed.get('signed_url') or ''
            return signed
        except Exception as exc:
            logger.error('Erro ao obter URL de %s (%s): %s', normalized_name, bucket_name, exc)
            return self.local_storage.url(normalized_name)

    def get_available_name(self, name, max_length=None):
        normalized_name = self._normalize_name(name)
        if self.exists(normalized_name):
            self.delete(normalized_name)
        return normalized_name

    def get_accessed_time(self, name):
        return None

    def get_created_time(self, name):
        return None

    def get_modified_time(self, name):
        return None

    def _get_bucket_name(self, name):
        normalized_name = self._normalize_name(name)
        routes = getattr(settings, 'SUPABASE_STORAGE_BUCKET_ROUTES', [])
        for prefix, bucket_name in routes:
            if normalized_name.startswith(prefix):
                return bucket_name
        return self.default_bucket

    @staticmethod
    def _normalize_name(name):
        normalized = (name or '').replace('\\', '/').lstrip('/')
        while '//' in normalized:
            normalized = normalized.replace('//', '/')
        if not normalized:
            return normalized

        segments = []
        for segment in normalized.split('/'):
            if segment in {'', '.', '..'}:
                continue
            segments.append(RoutedSupabaseStorage._sanitize_segment(segment))
        return '/'.join(segments)

    @staticmethod
    def _sanitize_segment(segment):
        normalized = unicodedata.normalize('NFKD', segment)
        ascii_only = normalized.encode('ascii', 'ignore').decode('ascii')
        ascii_only = ascii_only.replace(' ', '_')
        cleaned = get_valid_filename(ascii_only) or 'arquivo'
        return cleaned

    @staticmethod
    def _get_content_type(file_path):
        extension = os.path.splitext(file_path)[1].lower()
        explicit_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.csv': 'text/csv',
            '.xml': 'application/xml',
        }
        if extension in explicit_types:
            return explicit_types[extension]

        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'


SupabaseStorage = RoutedSupabaseStorage
