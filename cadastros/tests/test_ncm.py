from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from cadastros.models import NCM

User = get_user_model()

class TestNCMModel(TestCase):
    def test_codigo_validation(self):
        n = NCM(codigo='12A34', nome='Teste')
        with self.assertRaises(ValidationError):
            n.full_clean()

        n.codigo = '01012100'
        n.full_clean()  # OK
        n.save()
        self.assertEqual(NCM.objects.count(), 1)

class TestNCMViews(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'pass')
        self.client.force_login(self.user)

    def test_crud_flow(self):
        # Use superuser for template CRUD
        admin = User.objects.create_superuser('admin2', 'a2@b', 'pass')
        self.client.force_login(admin)

        # Create
        url = reverse('cadastros:ncm_create')
        resp = self.client.post(url, {'codigo': '01012100', 'nome': 'Trigo', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        n = NCM.objects.get(codigo='01012100')
        self.assertEqual(n.nome, 'Trigo')

        # Update
        url = reverse('cadastros:ncm_update', args=[n.pk])
        resp = self.client.post(url, {'codigo': '01012100', 'nome': 'Trigo Alterado', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        n.refresh_from_db()
        self.assertEqual(n.nome, 'Trigo Alterado')

        # Autocomplete
        url = reverse('cadastros:ncm_autocomplete') + '?q=010'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue('results' in data and len(data['results']) > 0)
        self.assertIn('pagination', data)

        # Delete
        url = reverse('cadastros:ncm_delete', args=[n.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(NCM.objects.filter(pk=n.pk).exists())

    def test_search_by_descricao(self):
        # Create two NCMs, one with a distinctive descricao
        NCM.objects.create(codigo='01022110', nome='Prenhes', descricao='Prenhes ou com cria ao pé', ativo=True)
        NCM.objects.create(codigo='01022190', nome='Outros', descricao='', ativo=True)
        url = reverse('cadastros:ncm_list') + '?descricao=cria'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Should contain the one with 'cria' in descricao and not the other
        self.assertContains(resp, '01022110')
        self.assertNotContains(resp, '01022190')

    def test_non_superuser_cannot_edit_template(self):
        n = NCM.objects.create(codigo='01012100', nome='Trigo', ativo=True)
        url = reverse('cadastros:ncm_update', args=[n.pk])
        resp = self.client.get(url, follow=True)
        # Should redirect to list and show a warning message
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Você não tem permissão')

    def test_superuser_can_edit_template(self):
        n = NCM.objects.create(codigo='01012100', nome='Trigo', ativo=True)
        admin = User.objects.create_superuser('admin', 'a@b', 'pass')
        self.client.force_login(admin)
        url = reverse('cadastros:ncm_update', args=[n.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(url, {'codigo': '01012100', 'nome': 'Trigo Alterado', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        n.refresh_from_db()
        self.assertEqual(n.nome, 'Trigo Alterado')

    def test_company_user_can_create_empresa_ncm(self):
        from empresas.models import Empresa
        from cadastros.models import EmpresaNCM
        empresa = Empresa.objects.create(nome='E2E Empresa')
        user = User.objects.create_user('companyuser', 'c@d', 'pass')
        user.empresa = empresa
        user.save()
        self.client.force_login(user)
        url = reverse('cadastros:ncm_create')
        resp = self.client.post(url, {'codigo': '01012101', 'nome': 'Empresa NCM', 'ativo': True})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(EmpresaNCM.objects.filter(empresa=empresa, codigo='01012101').exists())

    def test_postgres_unaccent_search(self):
        import unittest
        from django.db import connection
        # Only run this test when the DB is PostgreSQL (local/dev/CI where PG is configured)
        if connection.vendor != 'postgresql':
            self.skipTest('PostgreSQL not configured - skipping unaccent test')

        # Create two NCMs with accented characters
        NCM.objects.create(codigo='01013100', nome='Melão', descricao='Fruta típica', ativo=True)
        NCM.objects.create(codigo='01013101', nome='Amélia', descricao='Pessoa exemplo', ativo=True)

        url = reverse('cadastros:ncm_list') + '?descricao=Mel'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # Both should match because 'Mel' matches 'Melão' and 'Amélia' once unaccented
        self.assertContains(resp, '01013100')
        self.assertContains(resp, '01013101')

    def test_import_ncm_view_dry_run(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_content = "codigo,Nome,descricao\n01012100,Trigo,Grão\n01,Animais,Top".encode('utf-8')  # includes invalid hierarchical code
        f = SimpleUploadedFile('ncm_sample.csv', csv_content, content_type='text/csv')
        admin = User.objects.create_superuser('admin_import', 'a@b', 'pass')
        self.client.force_login(admin)
        url = reverse('cadastros:ncm_import')
        resp = self.client.post(url, {'arquivo': f, 'dry_run': True, 'replace': False, 'apply_to_all': False}, follow=True)
        self.assertEqual(resp.status_code, 200)
        # Should display a result area with summary from the import command
        self.assertTrue('Import concluído' in resp.content.decode() or 'Inválidos' in resp.content.decode() or 'inválido' in resp.content.decode())

    def test_seed_ncms_skipped_in_tests(self):
        """Ensure seed_ncms_for_company exits early during test runs to avoid DB locking."""
        from cadastros.tasks import seed_ncms_for_company
        from empresas.models import Empresa
        from cadastros.models import EmpresaNCM

        # Create company and a template NCM
        empresa = Empresa.objects.create(nome='Test Skip')
        NCM.objects.create(codigo='01012100', nome='Trigo', ativo=True)

        res = seed_ncms_for_company(empresa.pk)
        # Expect the guard to indicate we skipped seeding during tests
        self.assertTrue(res.get('skipped_in_tests', False))
        # No EmpresaNCM objects should have been created
        self.assertEqual(0, EmpresaNCM.objects.filter(empresa=empresa).count())

    def test_per_page_parameter_changes_items_per_page(self):
        # Create 60 NCM templates and verify per_page works
        for i in range(60):
            code = str(10000000 + i)[1:9]  # ensures 8-digit-like string
            NCM.objects.create(codigo=code, nome=f'NCM{i}', ativo=True)
        # Request with per_page=50
        url = reverse('cadastros:ncm_list') + '?per_page=50'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # The page context should have 50 items on page 1
        self.assertIn('page_obj', resp.context)
        page_obj = resp.context['page_obj']
        self.assertEqual(page_obj.paginator.per_page, 50)
        self.assertEqual(page_obj.end_index(), 50)
