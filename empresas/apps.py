# ==========================================
# empresas/apps.py
# ==========================================

from django.apps import AppConfig


class EmpresasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'empresas'
    verbose_name = 'Empresas e Planos'
    
    def ready(self):
        """Importa signals do app para registrar handlers"""
        from . import signals  # noqa: F401
