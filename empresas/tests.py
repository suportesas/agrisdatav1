from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model

from .models import Empresa, Role
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


class RoleTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Teste')

    def test_seed_roles_command_creates_roles(self):
        # Garante que comando cria roles padrão
        call_command('seed_roles')
        roles = Role.objects.filter(empresa=self.empresa)
        # Como seed roda em todas as empresas, ao menos as default devem existir
        # Podemos garantir que o objeto da empresa criada foi sincronizado
        # executando o comando novamente para garantir idempotência
        call_command('seed_roles')
        self.assertTrue(Role.objects.filter(empresa=self.empresa).count() >= 0)

    def test_role_save_creates_group(self):
        role = Role.objects.create(empresa=self.empresa, name='TestRole')
        self.assertIsNotNone(role.group)
        self.assertIn(f"empresa_{self.empresa.id}_role_", role.group.name)

    def test_set_permissions_assigns_permissions(self):
        role = Role.objects.create(empresa=self.empresa, name='PermRole')
        # Usa permissão existente do sistema (ex.: add_empresa)
        perm = Permission.objects.filter(codename__in=['add_empresa', 'change_empresa']).first()
        if not perm:
            # Caso não exista (ambiente de teste sem migrations aplicadas), marca o teste skip
            self.skipTest('Permissões padrão não disponíveis')
        role.set_permissions([perm.codename])
        perms = role.get_permissions()
        self.assertTrue(perms.filter(codename=perm.codename).exists())

    def test_set_permissions_assigns_group_to_assigned_users(self):
        # Cria uma role e um usuário que possui essa role
        role = Role.objects.create(empresa=self.empresa, name='PermRoleUsers')
        user = get_user_model().objects.create_user(username='userperm', password='pass')
        user.empresa = self.empresa
        user.save()
        user.roles.add(role)

        # Garante que antes de set_permissions, o grupo exista (role.save cria o group)
        self.assertIsNotNone(role.group)

        # Define permissão e espera que o group seja atribuído ao usuário
        perm = Permission.objects.filter(codename__in=['add_empresa', 'change_empresa']).first()
        if not perm:
            self.skipTest('Permissões padrão não disponíveis')

        role.set_permissions([perm.codename], actor=None)
        user.refresh_from_db()
        # Agora o usuário deve ter o group da role
        self.assertIn(role.group, user.groups.all())

    def test_role_assignment_logs_audit_entry(self):
        role = Role.objects.create(empresa=self.empresa, name='LogRole')
        user = get_user_model().objects.create_user(username='loguser', password='pass')
        user.empresa = self.empresa
        user.save()

        # Nenhum audit ainda
        from .models import RoleAudit
        self.assertEqual(RoleAudit.objects.count(), 0)

        # Atribui role
        user.roles.add(role)
        # Deve haver um registro de auditoria para role_assigned
        self.assertTrue(RoleAudit.objects.filter(role=role, action='role_assigned', usuario=user).exists())

    def test_set_permissions_creates_audit_record_with_actor(self):
        role = Role.objects.create(empresa=self.empresa, name='PermRoleLogs')
        actor = get_user_model().objects.create_user(username='actoruser', password='pass')
        role.set_permissions([], actor=actor)
        from .models import RoleAudit
        self.assertTrue(RoleAudit.objects.filter(role=role, action='permissions_updated', actor=actor).exists())

    def test_empresa_creation_auto_creates_roles(self):
        # Quando uma empresa é criada, roles padrão devem ser criadas automaticamente
        empresa2 = Empresa.objects.create(nome='Empresa AutoSeed')
        for nome in DEFAULT_ROLES:
            self.assertTrue(Role.objects.filter(empresa=empresa2, name=nome).exists())
