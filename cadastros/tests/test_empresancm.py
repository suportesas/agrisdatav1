from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from empresas.models import Empresa
from cadastros.models import NCM, EmpresaNCM

User = get_user_model()

class EmpresaNCMMultiTenantTests(TestCase):
    def setUp(self):
        # create two companies and users
        self.e1 = Empresa.objects.create(nome='Empresa A')
        self.e2 = Empresa.objects.create(nome='Empresa B')
        self.u1 = User.objects.create_user('u1', 'u1@example.com', 'pass')
        self.u1.empresa = self.e1
        self.u1.save()
        self.u2 = User.objects.create_user('u2', 'u2@example.com', 'pass')
        self.u2.empresa = self.e2
        self.u2.save()

        # create template
        self.t = NCM.objects.create(codigo='01012100', nome='Trigo')

        # seed per-company
        EmpresaNCM.objects.create(empresa=self.e1, codigo=self.t.codigo, nome=self.t.nome, template=self.t)
        EmpresaNCM.objects.create(empresa=self.e2, codigo=self.t.codigo, nome=self.t.nome, template=self.t)

    def test_company_edit_does_not_affect_other(self):
        e1_obj = EmpresaNCM.objects.get(empresa=self.e1, codigo='01012100')
        e2_obj = EmpresaNCM.objects.get(empresa=self.e2, codigo='01012100')
        e1_obj.nome = 'Trigo Empresa A'
        e1_obj.save()
        e2_obj.refresh_from_db()
        self.assertEqual(e2_obj.nome, 'Trigo')

    def test_unique_per_company(self):
        # same code for same company should fail uniqueness
        with self.assertRaises(Exception):
            EmpresaNCM.objects.create(empresa=self.e1, codigo='01012100', nome='Duplicado')
