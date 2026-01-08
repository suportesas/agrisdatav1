from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Empresa, Role

# Reuse DEFAULT_ROLES from management command to keep a single source
try:
    from .management.commands.seed_roles import DEFAULT_ROLES
except Exception:
    DEFAULT_ROLES = [
        'Proprietário',
        'Almoxarife',
        'Operacional do Campo',
        'Financeiro',
        'Gerente',
        'Vendedor',
    ]


@receiver(post_save, sender=Empresa)
def create_default_roles(sender, instance, created, **kwargs):
    """Cria roles padrão quando uma Empresa é criada (idempotente)."""
    if not created:
        return

    for nome in DEFAULT_ROLES:
        Role.objects.get_or_create(empresa=instance, name=nome, defaults={'builtin': True})