from django.apps import AppConfig


class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usuarios'
    verbose_name = 'Usuários'
    
    def ready(self):
        """Importa signals se houver"""
        # Import signals to register signal handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            # If signals import fails, ignore to avoid breaking app import
            pass