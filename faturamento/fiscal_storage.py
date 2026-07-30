"""
Upload de documentos fiscais (XML/PDF) para Supabase Storage.
Evita armazenar base64 no PostgreSQL, reduzindo o tamanho do banco.
"""
import base64
import logging

logger = logging.getLogger(__name__)

BUCKET = 'documentos-fiscais'


def _upload(raw_bytes: bytes, empresa_id, path: str) -> str:
    """Faz upload de bytes para o bucket e retorna a URL pública, ou '' se falhar."""
    try:
        from core.storage import storage_helper
        if not storage_helper.enabled:
            return ''
        url = storage_helper.upload_file(raw_bytes, BUCKET, path)
        return url or ''
    except Exception as exc:
        logger.error('fiscal_storage upload falhou (%s): %s', path, exc)
        return ''


def upload_xml(b64_value: str, empresa_id, tipo: str, filename: str) -> str:
    """Faz upload de XML base64 e retorna URL. tipo: 'nfe', 'cte', 'mdfe'."""
    if not b64_value:
        return ''
    try:
        raw = base64.b64decode(b64_value)
    except Exception:
        return ''
    return _upload(raw, empresa_id, f'{empresa_id}/{tipo}/{filename}')


def upload_pdf(b64_value: str, empresa_id, tipo: str, filename: str) -> str:
    """Faz upload de PDF base64 e retorna URL. tipo: 'nfe', 'cte', 'mdfe'."""
    if not b64_value:
        return ''
    try:
        raw = base64.b64decode(b64_value)
    except Exception:
        return ''
    return _upload(raw, empresa_id, f'{empresa_id}/{tipo}/{filename}')


def upload_xml_texto(xml_str: str, empresa_id, chave: str) -> str:
    """Faz upload de um XML já em texto puro (não base64) e retorna a URL.

    Usado pela Distribuição de DF-e, que recebe o XML já descompactado do docZip
    — diferente de upload_xml(), que espera XML em base64 vindo da IntegraNotas.
    """
    if not xml_str:
        return ''
    return _upload(xml_str.encode('utf-8'), empresa_id, f'{empresa_id}/dfe/{chave}.xml')
