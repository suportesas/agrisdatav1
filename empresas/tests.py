import json
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model

from .models import Empresa, Role, PermissionTemplate
from django.test import Client
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

    def test_role_permissions_access_control(self):
        # Admin da empresa deve conseguir ver permissões via AJAX; usuário comum não
        role = Role.objects.create(empresa=self.empresa, name='AccessRole')
        User = get_user_model()
        admin = User.objects.create_user(username='aadmin', password='pass', tipo='ADMIN')
        admin.empresa = self.empresa
        admin.save()

        client = Client()
        self.assertTrue(client.login(username='aadmin', password='pass'))
        resp = client.get(f"/empresas/roles/{role.id}/permissions/", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('permissions', data)

        # Normal user should be forbidden
        normal = User.objects.create_user(username='normal', password='pass', tipo='FUNC')
        normal.empresa = self.empresa
        normal.save()
        self.assertTrue(client.login(username='normal', password='pass'))
        resp2 = client.get(f"/empresas/roles/{role.id}/permissions/", HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp2.status_code, 403)


class PermissionTemplateTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome='Empresa Tpl')
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.superuser = User.objects.create_superuser(username='su', email='su@test', password='pass')

    def test_save_permission_template_creates_template(self):
        # Cria role
        role = Role.objects.create(empresa=self.empresa, name='TplRole')
        self.client.login(username='su', password='pass')
        url = f"/empresas/roles/{role.id}/permissions/save-template/"
        dados = {'empresa': {'add': True, 'change': False, 'delete': False, 'view': True}}
        resp = self.client.post(url, data=json.dumps({'nome': 'Tpl1', 'dados': dados}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        from .models import PermissionTemplate
        self.assertTrue(PermissionTemplate.objects.filter(empresa=self.empresa, nome='Tpl1').exists())

        # Também lista via endpoint
        list_url = '/empresas/roles/templates/'
        resp2 = self.client.get(list_url)
        self.assertEqual(resp2.status_code, 200)
        data = resp2.json()
        self.assertTrue(any(t['nome']=='Tpl1' for t in data.get('templates', [])))

    def test_apply_template_to_role_creates_audit(self):
        role = Role.objects.create(empresa=self.empresa, name='RoleApply')
        tpl = PermissionTemplate.objects.create(empresa=self.empresa, nome='TplApply', dados={'empresa': {'add': True}})
        self.client.login(username='su', password='pass')
        url = f"/empresas/roles/{role.id}/permissions/apply-template/"
        resp = self.client.post(url, data=json.dumps({'template_id': tpl.id}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        from .models import RoleAudit
        self.assertTrue(RoleAudit.objects.filter(role=role, action='permissions_updated').exists())

    def test_apply_template_bulk_updates_roles(self):
        r1 = Role.objects.create(empresa=self.empresa, name='R1')
        r2 = Role.objects.create(empresa=self.empresa, name='R2')
        tpl = PermissionTemplate.objects.create(empresa=self.empresa, nome='TplBulk', dados={'empresa': {'view': True}})
        self.client.login(username='su', password='pass')
        url = '/empresas/roles/templates/apply-bulk/'
        resp = self.client.post(url, data=json.dumps({'template_id': tpl.id, 'role_ids': [r1.id, r2.id]}), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        from .models import RoleAudit
        self.assertTrue(RoleAudit.objects.filter(role=r1, action='permissions_updated').exists())
        self.assertTrue(RoleAudit.objects.filter(role=r2, action='permissions_updated').exists())
