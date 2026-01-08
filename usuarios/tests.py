from django.test import TestCase
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Role

User = get_user_model()


class RoleSyncTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Sync')
        self.role = Role.objects.create(empresa=self.empresa, name='SyncRole')
        self.user = User.objects.create_user(username='syncuser', password='pass')
        self.user.empresa = self.empresa
        self.user.save()

    def test_adding_role_adds_group_to_user(self):
        # Initially no groups
        self.assertEqual(self.user.groups.count(), 0)

        # Add role - should add the corresponding group to user.groups
        self.user.roles.add(self.role)
        self.user.refresh_from_db()
        self.assertIn(self.role.group, self.user.groups.all())

    def test_removing_role_removes_group_from_user(self):
        # Add then remove
        self.user.roles.add(self.role)
        self.user.refresh_from_db()
        self.assertIn(self.role.group, self.user.groups.all())

        self.user.roles.remove(self.role)
        self.user.refresh_from_db()
        self.assertNotIn(self.role.group, self.user.groups.all())

    def test_clearing_roles_removes_all_groups(self):
        # Add multiple roles
        role2 = Role.objects.create(empresa=self.empresa, name='SyncRole2')
        self.user.roles.add(self.role, role2)
        self.user.refresh_from_db()
        self.assertIn(self.role.group, self.user.groups.all())
        self.assertIn(role2.group, self.user.groups.all())

        # Clear
        self.user.roles.clear()
        self.user.refresh_from_db()
        self.assertEqual(self.user.groups.count(), 0)
