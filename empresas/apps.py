# ==========================================
# empresas/apps.py
# ==========================================

from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _sync_programas(sender, **kwargs):
    """Sincroniza a tabela Programa após `migrate` (ver empresas/programa_discovery.py)."""
    from .programa_discovery import sincronizar_programas
    try:
        sincronizar_programas()
    except Exception:
        # Nunca deve quebrar o comando migrate por causa da sincronização.
        pass


class EmpresasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empresas'
    verbose_name = 'Empresas e Planos'

    def ready(self):
        """Importa signals do app para registrar handlers"""
        from . import signals  # noqa: F401
        post_migrate.connect(_sync_programas, sender=self)
