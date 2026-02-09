from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from .models import Usuario


@receiver(post_save, sender=Usuario)
def grant_admin_permission(sender, instance, created, **kwargs):
    """Concede automaticamente permissão de ver estoque de outras fazendas para admins.
    
    Quando um usuário é criado/atualizado como admin (is_superuser, is_staff ou tipo='ADMIN'),
    ele automaticamente ganha permissão de escolher fazendas no estoque.
    """
    from cadastros.models import Fazenda
    
    # Verifica se é admin (superuser, staff, ou tipo ADMIN)
    is_admin = instance.is_superuser or instance.is_staff or (hasattr(instance, 'tipo') and instance.tipo == 'ADMIN')
    
    if is_admin:
        # Busca a permissão
        try:
            content_type = ContentType.objects.get_for_model(Fazenda)
            permission = Permission.objects.get(
                content_type=content_type,
                codename='view_other_fazendas_estoque'
            )
            # Adiciona a permissão ao usuário (idempotente)
            instance.user_permissions.add(permission)
        except Permission.DoesNotExist:
            # Permissão ainda não foi criada, será criada na migração
            pass
    else:
        # Se não é mais admin, remove a permissão
        try:
            content_type = ContentType.objects.get_for_model(Fazenda)
            permission = Permission.objects.get(
                content_type=content_type,
                codename='view_other_fazendas_estoque'
            )
            instance.user_permissions.remove(permission)
        except Permission.DoesNotExist:
            pass


@receiver(m2m_changed, sender=Usuario.roles.through)
def sync_roles_to_groups(sender, instance, action, pk_set, **kwargs):
    """Sincroniza os Groups do Django com as Roles atribuídas ao usuário.

    Quando Roles são adicionadas/removidas, atualiza 'instance.groups' para conter
    exatamente os Groups correspondentes às Roles atuais e cria registros de
    auditoria para atribuições/remoções de roles.
    """
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return

    # Coleta groups das roles atuais (defensivo: role.group pode ser None)
    groups = [r.group for r in instance.roles.all() if r.group]

    # Substitui grupos do usuário pelo conjunto derivado das roles
    instance.groups.set(groups)
    # Salva para garantir que mudanças de permissão se apliquem
    instance.save()

    # Auditoria: registrar quais roles foram adicionadas/removidas
    from django.apps import apps as django_apps
    RoleAudit = django_apps.get_model('empresas', 'RoleAudit')

    if action == 'post_add' and pk_set:
        RoleModel = django_apps.get_model('empresas', 'Role')
        for role_pk in pk_set:
            role = RoleModel.objects.filter(pk=role_pk).first()
            if role:
                RoleAudit.objects.create(role=role, actor=None, usuario=instance, action='role_assigned', details={'role': role.name})
    elif action == 'post_remove' and pk_set:
        RoleModel = django_apps.get_model('empresas', 'Role')
        for role_pk in pk_set:
            role = RoleModel.objects.filter(pk=role_pk).first()
            if role:
                RoleAudit.objects.create(role=role, actor=None, usuario=instance, action='role_removed', details={'role': role.name})
    elif action == 'post_clear':
        # All roles removed
        RoleAudit.objects.create(role=None, actor=None, usuario=instance, action='role_removed', details={'cleared': True})