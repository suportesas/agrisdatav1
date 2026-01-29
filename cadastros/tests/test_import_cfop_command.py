import io
import csv
import tempfile
from django.core.management import call_command
from django.test import TestCase
from cadastros.models import CFOP

class ImportCFOPCommandTest(TestCase):
    def test_dry_run_does_not_persist(self):
        # create temp csv
        fd, path = tempfile.mkstemp(suffix='.csv')
        with open(path, 'w', encoding='utf-8', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['codigo','nome','descricao'])
            writer.writerow(['9999','Teste Dry','Descricao'])

        # run dry_run
        out = io.StringIO()
        call_command('import_cfop', path=path, dry_run=True, stdout=out)
        self.assertIn('Criado (dry-run): 9999', out.getvalue())
        self.assertFalse(CFOP.objects.filter(codigo='9999').exists())
