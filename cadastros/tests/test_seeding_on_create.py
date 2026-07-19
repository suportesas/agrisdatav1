import sys
from unittest.mock import patch

from django.test import TestCase
from empresas.models import Empresa
from cadastros.models import NCM, EmpresaNCM
from cadastros.tasks import seed_ncms_for_company

class SeedingTests(TestCase):
    """`seed_ncms_for_company` tem uma guarda que sempre retorna
    {'created': 0, 'skipped_in_tests': True} quando `sys.argv` contem
    qualquer argumento comecando com 'test' (e.g. 'manage.py test ...') —
    o que e sempre o caso quando esses testes rodam via `manage.py test`.
    Sem o patch de sys.argv abaixo, as asercoes de 'created' == 2 nunca
    passavam de verdade. `auto_seed_ncm=False` evita que o post_save signal
    da Empresa tambem chame a funcao (com outro valor de sys.argv possivel)."""

    def setUp(self):
        NCM.objects.all().delete()
        EmpresaNCM.objects.all().delete()
        # create some templates
        NCM.objects.create(codigo='01012100', nome='Cavalos')
        NCM.objects.create(codigo='02011000', nome='Carne bovina')

    def test_seed_function_creates_company_rows(self):
        e = Empresa.objects.create(nome='Seed Company', auto_seed_ncm=False)
        with patch.object(sys, 'argv', ['manage.py']):
            res = seed_ncms_for_company(e.pk)
        self.assertEqual(res['created'], 2)
        self.assertEqual(EmpresaNCM.objects.filter(empresa=e).count(), 2)

    def test_idempotent(self):
        e = Empresa.objects.create(nome='Seed Company 2', auto_seed_ncm=False)
        with patch.object(sys, 'argv', ['manage.py']):
            seed_ncms_for_company(e.pk)
            res2 = seed_ncms_for_company(e.pk)
        # second run should create zero new
        self.assertEqual(res2['created'], 0)
