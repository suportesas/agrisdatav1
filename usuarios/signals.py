from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Usuario


@receiver(m2m_changed, sender=Usuario.roles.through)
def sync_roles_to_groups(sender, instance, action, pk_set, **kwargs):
    """Sincroniza os Groups do Django com as Roles atribuídas ao usuário.

    Quando Roles são adicionadas/removidas, atualiza 'instance.groups' para conter
    exatamente os Groups correspondentes às Roles atuais.
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    # Coleta groups das roles atuais (defensivo: role.group pode ser None)
    groups = [r.group for r in instance.roles.all() if r.group]

    # Substitui grupos do usuário pelo conjunto derivado das roles
    instance.groups.set(groups)
    # Salva para garantir que mudanças de permissão se apliquem
    instance.save()