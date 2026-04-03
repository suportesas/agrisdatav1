"""
Helpers para feature flags do ERP Agricola.

Mantem uma camada unica para consultar flags de liberacao progressiva.
"""

from django.conf import settings


def is_feature_enabled(flag_name: str, default: bool = False) -> bool:
    """Retorna True se a feature flag estiver ativa em settings.FEATURE_FLAGS."""
    feature_flags = getattr(settings, 'FEATURE_FLAGS', {})
    return bool(feature_flags.get(flag_name, default))


def get_all_feature_flags() -> dict:
    """Retorna copia das feature flags configuradas para fins de diagnostico."""
    feature_flags = getattr(settings, 'FEATURE_FLAGS', {})
    return dict(feature_flags)
