"""
Fernet field encryption helpers.

Encrypted values are stored as  "fernet:<ciphertext>"  so they are
self-describing and distinguishable from legacy plaintext rows.

Usage:
    from faturamento.encryption import encrypt_field, decrypt_field
"""
from __future__ import annotations

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_FERNET_PREFIX = "fernet:"
_fernet_instance = None  # lazily initialised — safe for multi-process servers


def _get_fernet():
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    key = getattr(settings, "FIELD_ENCRYPTION_KEY", "")
    if not key:
        return None
    from cryptography.fernet import Fernet
    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_field(plaintext: str) -> str:
    """
    Encrypt *plaintext* and return a "fernet:<ciphertext>" string.
    Idempotent: already-encrypted values are returned unchanged.
    If FIELD_ENCRYPTION_KEY is not set, returns plaintext unchanged (passthrough).
    """
    if not plaintext or plaintext.startswith(_FERNET_PREFIX):
        return plaintext
    fernet = _get_fernet()
    if fernet is None:
        return plaintext
    return _FERNET_PREFIX + fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_field(value: str) -> str:
    """
    Decrypt a "fernet:<ciphertext>" string and return plaintext.
    If value does NOT start with the prefix, returns it as-is
    (handles legacy plaintext rows transparently).
    """
    if not value or not value.startswith(_FERNET_PREFIX):
        return value
    fernet = _get_fernet()
    if fernet is None:
        logger.warning("decrypt_field: FIELD_ENCRYPTION_KEY não configurado — retornando string vazia")
        return ""
    from cryptography.fernet import InvalidToken
    try:
        ciphertext = value[len(_FERNET_PREFIX):].encode("utf-8")
        return fernet.decrypt(ciphertext).decode("utf-8")
    except InvalidToken:
        logger.error("decrypt_field: InvalidToken — chave incorreta ou ciphertext corrompido")
        return ""
