from django.test import TestCase
from empresas.models import Empresa
from cadastros.models import NCM, EmpresaNCM
from cadastros.tasks import seed_ncms_for_company

class SeedingTests(TestCase):
    def setUp(self):
        NCM.objects.all().delete()
        EmpresaNCM.objects.all().delete()
        # create some templates
        NCM.objects.create(codigo='01012100', nome='Cavalos')
        NCM.objects.create(codigo='02011000', nome='Carne bovina')

    def test_seed_function_creates_company_rows(self):
        e = Empresa.objects.create(nome='Seed Company')
        res = seed_ncms_for_company(e.pk)
        self.assertEqual(res['created'], 2)
        self.assertEqual(EmpresaNCM.objects.filter(empresa=e).count(), 2)

    def test_idempotent(self):
        e = Empresa.objects.create(nome='Seed Company 2')
        res1 = seed_ncms_for_company(e.pk)
        res2 = seed_ncms_for_company(e.pk)
        # second run should create zero new
        self.assertEqual(res2['created'], 0)
