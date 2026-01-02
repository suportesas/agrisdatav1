from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from empresas.models import Empresa
from cadastros.models import Cliente

class RepairOrphanClientsCommandTests(TestCase):
    def setUp(self):
        self.emp = Empresa.objects.create(nome='RepairCo')
        self.other = Empresa.objects.create(nome='OtherCo')
        self.client_obj = Cliente.objects.create(empresa=self.emp, razao_social='To Orphan', cnpj_cpf='55555555555555')
        # Simulate an orphan by setting empresa_id to a non-existent ID (schema enforces NOT NULL)
        Cliente.objects.filter(pk=self.client_obj.pk).update(empresa_id=99999)

    def test_list_shows_orphan(self):
        out = StringIO()
        call_command('repair_orphan_clients', '--list', stdout=out)
        out_str = out.getvalue()
        self.assertIn('Found 1 orphaned client', out_str)
        self.assertIn('To Orphan', out_str)

    def test_assign_by_id_dry_run_and_confirm(self):
        out = StringIO()
        # Dry run should not assign
        call_command('repair_orphan_clients', '--assign', str(self.other.pk), '--dry-run', stdout=out)
        self.assertIn('Dry-run mode', out.getvalue())
        self.client_obj.refresh_from_db()
        # Should remain the fake/invalid empresa_id during dry-run
        self.assertEqual(self.client_obj.empresa_id, 99999)

        # Without confirm should raise
        with self.assertRaises(Exception):
            call_command('repair_orphan_clients', '--assign', str(self.other.pk), stdout=out)

        # With confirm should assign
        out = StringIO()
        call_command('repair_orphan_clients', '--assign', str(self.other.pk), '--confirm', stdout=out)
        out_str = out.getvalue()
        self.assertIn('Successfully assigned', out_str)
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.empresa_id, self.other.pk)
