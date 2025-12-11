from django.apps import AppConfig


class CadastrosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cadastros'

    def ready(self):
        # Importa sinais para registro automático
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
