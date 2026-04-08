from django.test import TestCase
from django.contrib.auth import get_user_model
from uuid import uuid4
from empresas.models import Empresa, Role
from usuarios.models import TipoUsuario

User = get_user_model()


class RoleSyncTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome=f'Empresa Sync {uuid4().hex[:8]}', is_interna_saas=True)
        self.role = Role.objects.create(empresa=self.empresa, name='SyncRole')
        self.user = User.objects.create_user(username='syncuser', password='pass')
        self.user.empresa = self.empresa
        self.user.is_staff = True
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


class UsuarioFormTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome=f'Empresa Form {uuid4().hex[:8]}', is_interna_saas=True)
        self.role = Role.objects.create(empresa=self.empresa, name='FormRole')
        self.user = User.objects.create_user(username='formadmin', password='pass')
        self.user.empresa = self.empresa
        self.user.is_staff = True
        self.user.save()

    def test_roles_visible_in_create_form_for_company_admin(self):
        # Login as staff (company admin)
        self.client.force_login(self.user)
        resp = self.client.get('/usuarios/novo/')
        self.assertEqual(resp.status_code, 200)
        # Ensure the role name appears in the rendered form
        self.assertContains(resp, 'FormRole')

    def test_other_company_roles_not_shown(self):
        other = Empresa.objects.create(nome=f'Outra {uuid4().hex[:8]}', is_interna_saas=True)
        Role.objects.create(empresa=other, name='OtherRole')
        self.client.force_login(self.user)
        resp = self.client.get('/usuarios/novo/')
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'OtherRole')

    def test_roles_save_on_update(self):
        # Create another user to edit
        target = User.objects.create_user(username='target', password='pass')
        target.empresa = self.empresa
        target.save()

        # Create a role in the same company
        role = Role.objects.create(empresa=self.empresa, name='EditorRole')

        # Login and post update selecting the role
        self.client.force_login(self.user)
        url = f'/usuarios/{target.pk}/editar/'
        data = {
            'username': target.username,
            'email': 't@example.com',
            'first_name': 'T',
            'last_name': 'User',
            'tipo': 'FUNC',
            'telefone': '',
            'cpf': '',
            'data_nascimento': '',
            'data_admissao': '',
            # do NOT provide comissao_vendas (should be optional for FUNC)
            'roles': [str(role.pk)],
            'is_active': True,
            'is_staff': True
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        target.refresh_from_db()
        self.assertIn(role, target.roles.all())
        # Also ensure the group was added via signals
        self.assertIn(role.group, target.groups.all())

    def test_update_without_comissao_for_non_vendedor_succeeds(self):
        target = User.objects.create_user(username='nocom', password='pass')
        target.empresa = self.empresa
        target.save()
        self.client.force_login(self.user)
        url = f'/usuarios/{target.pk}/editar/'
        data = {
            'username': target.username,
            'email': 'a@example.com',
            'first_name': 'A',
            'last_name': 'NoCom',
            'tipo': 'FUNC',
            # comissao_vendas intentionally omitted
            'roles': [],
            'is_active': True,
            'is_staff': True
        }
        resp = self.client.post(url, data, follow=True)
        self.assertEqual(resp.status_code, 200)
        target.refresh_from_db()
        # Should not raise validation error and leave comissao_vendas at default (0)
        from decimal import Decimal
        self.assertEqual(target.comissao_vendas, Decimal('0.00'))

    def test_roles_shown_in_user_list(self):
        # Create target user and assign a role
        target = User.objects.create_user(username='listuser', password='pass')
        target.empresa = self.empresa
        target.save()
        role = Role.objects.create(empresa=self.empresa, name='ListRole')
        target.roles.add(role)

        # Login and fetch the user list page
        self.client.force_login(self.user)
        resp = self.client.get('/usuarios/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'ListRole')

    def test_custom_tipo_visible_in_create_form(self):
        TipoUsuario.objects.create(codigo='SUPORTE', nome='Suporte', ordem=70)
        self.client.force_login(self.user)
        resp = self.client.get('/usuarios/novo/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Suporte')


class TipoUsuarioCrudTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='root',
            email='root@example.com',
            password='pass12345'
        )

    def test_superuser_can_create_tipo_usuario(self):
        self.client.force_login(self.superuser)
        resp = self.client.post('/usuarios/tipos/novo/', {
            'codigo': 'SUPORTE',
            'nome': 'Suporte',
            'descricao': 'Atendimento interno',
            'ordem': 90,
            'ativo': 'on',
        }, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(TipoUsuario.objects.filter(codigo='SUPORTE', nome='Suporte').exists())

    def test_tipo_display_uses_dynamic_registry(self):
        TipoUsuario.objects.update_or_create(
            codigo='SUPORTE',
            defaults={'nome': 'Suporte', 'ordem': 90}
        )
        user = User.objects.create_user(username='dinamico', password='pass12345', tipo='SUPORTE')
        self.assertEqual(user.get_tipo_display(), 'Suporte')
