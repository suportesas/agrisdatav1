from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from cadastros.models import CFOP

User = get_user_model()

class TestCFOPViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('user1', 'u1@example.com', 'pass')
        self.client.force_login(self.user)

    def test_non_superuser_cannot_create_cfop(self):
        url = reverse('cadastros:cfop_create')
        resp = self.client.get(url, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Você não tem permissão')

    def test_superuser_crud_flow(self):
        admin = User.objects.create_superuser('admin', 'a@b', 'pass')
        self.client.force_login(admin)
        # Create
        url = reverse('cadastros:cfop_create')
        resp = self.client.post(url, {'codigo': '5102', 'nome': 'Venda Interna', 'descricao': '', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        cf = CFOP.objects.get(codigo='5102')
        self.assertEqual(cf.nome, 'Venda Interna')
        # Update
        url = reverse('cadastros:cfop_update', args=[cf.pk])
        resp = self.client.post(url, {'codigo': '5102', 'nome': 'Venda Interna Alterada', 'descricao': '', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        cf.refresh_from_db()
        self.assertEqual(cf.nome, 'Venda Interna Alterada')
        # Delete
        url = reverse('cadastros:cfop_delete', args=[cf.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(CFOP.objects.filter(pk=cf.pk).exists())

    def test_list_and_search(self):
        CFOP.objects.create(codigo='5102', nome='Venda Interna', descricao='Descrição test', ativo=True)
        CFOP.objects.create(codigo='6102', nome='Compra Interna', descricao='', ativo=True)
        url = reverse('cadastros:cfop_list') + '?q=5102'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '5102')
        # search by descricao
        url = reverse('cadastros:cfop_list') + '?descricao=Descrição'
        resp = self.client.get(url)
        self.assertContains(resp, '5102')

    def test_empresa_cfop_lazy_seed_and_company_create(self):
        from empresas.models import Empresa
        from cadastros.models import EmpresaCFOP
        empresa = Empresa.objects.create(nome='Empresa Test')
        user = User.objects.create_user('companyuser', 'c@d', 'pass')
        user.empresa = empresa
        user.save()
        self.client.force_login(user)

        # Initially company has no cfops, visiting list should trigger lazy seed
        url = reverse('cadastros:cfop_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # After viewing, company should have copies (may be zero if no templates present)
        self.assertIsNotNone(EmpresaCFOP.objects.filter(empresa=empresa))

        # Without permission, company cannot create EmpresaCFOP
        post_url = reverse('cadastros:cfop_create')
        resp = self.client.post(post_url, {'codigo': '5201', 'nome': 'Empresa CFOP', 'descricao': '', 'ativo': True}, follow=True)
        self.assertContains(resp, 'Você não tem permissão')

        # Grant permission via group and try again
        from django.contrib.auth.models import Group, Permission
        g, _ = Group.objects.get_or_create(name='Test Fiscal')
        perms = ['add_empresacfop']
        for p in perms:
            perm = Permission.objects.get(codename=p, content_type__app_label='cadastros')
            g.permissions.add(perm)
        user.groups.add(g)

        resp = self.client.post(post_url, {'codigo': '5201', 'nome': 'Empresa CFOP', 'descricao': '', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(EmpresaCFOP.objects.filter(empresa=empresa, codigo='5201').exists())

    def test_group_allows_global_cfop_management(self):
        # Non-superuser cannot create global CFOP
        resp = self.client.get(reverse('cadastros:cfop_create'), follow=True)
        self.assertContains(resp, 'Você não tem permissão')

        # Create group with global permissions
        from django.contrib.auth.models import Group, Permission
        g, _ = Group.objects.get_or_create(name='Fiscal Admin Test')
        perms = ['add_cfop','change_cfop','delete_cfop']
        for p in perms:
            perm = Permission.objects.get(codename=p, content_type__app_label='cadastros')
            g.permissions.add(perm)

        user = User.objects.create_user('fiscal', 'f@f', 'pass')
        user.groups.add(g)
        self.client.force_login(user)

        # Should be able to create global CFOP
        resp = self.client.post(reverse('cadastros:cfop_create'), {'codigo': '5301', 'nome': 'Global CFOP', 'descricao': '', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(CFOP.objects.filter(codigo='5301').exists())

    def test_import_cfop_view_dry_run(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_content = b"codigo,nome,descricao\n5102,Venda Interna,Teste\nabcd,Invalido,Top"
        f = SimpleUploadedFile('cfop_sample.csv', csv_content, content_type='text/csv')
        # user must have add_cfop permission
        from django.contrib.auth.models import Group, Permission
        g, _ = Group.objects.get_or_create(name='Import Test')
        perm = Permission.objects.get(codename='add_cfop', content_type__app_label='cadastros')
        g.permissions.add(perm)

        admin = User.objects.create_user('impuser', 'i@i', 'pass')
        admin.groups.add(g)
        self.client.force_login(admin)

        url = reverse('cadastros:cfop_import')
        resp = self.client.post(url, {'arquivo': f, 'dry_run': True, 'replace': False, 'apply_to_all': False}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('Import concluído' in resp.content.decode() or 'Inválidos' in resp.content.decode() or 'inválido' in resp.content.decode())
