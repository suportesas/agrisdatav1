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


@receiver(post_save, sender=Empresa)
def seed_ncms_on_create(sender, instance, created, **kwargs):
    """Seeds company NCMs when empresa is created and auto_seed_ncm is True."""
    if not created:
        return

    # Lazy import to avoid circular imports
    try:
        from cadastros.tasks import seed_ncms_for_company_async
        if getattr(instance, 'auto_seed_ncm', False):
            seed_ncms_for_company_async(instance.pk)
    except Exception:
        # Fail silently; admin can trigger via action
        pass