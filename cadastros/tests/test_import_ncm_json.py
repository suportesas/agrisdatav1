from django.test import TestCase
from django.core.management import call_command
from cadastros.models import NCM, EmpresaNCM
from empresas.models import Empresa
import os

class ImportNCMJsonTests(TestCase):
    def setUp(self):
        # ensure clean
        NCM.objects.all().delete()
        Empresa.objects.all().delete()

        self.sample = os.path.join(os.path.dirname(__file__), 'data', 'sample_ncm.json')

    def test_import_json_creates_templates(self):
        call_command('import_ncm', '--path', self.sample)
        self.assertEqual(NCM.objects.count(), 2)
        n = NCM.objects.get(codigo='01012100')
        self.assertIn('Cavalos', n.nome)

    def test_import_json_and_apply_to_company(self):
        e = Empresa.objects.create(nome='Empresa Teste')
        call_command('import_ncm', '--path', self.sample, '--apply-to-all-companies')
        # templates created
        self.assertEqual(NCM.objects.count(), 2)
        # empresa copies created
        self.assertEqual(EmpresaNCM.objects.filter(empresa=e).count(), 2)
