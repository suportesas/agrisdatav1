from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from rh.models import Funcionario


class FuncionarioBankTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='tuser2', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='tuser2', password='pass')

    def test_funcionario_form_renders_tipo_conta(self):
        url = reverse('cadastros:funcionario_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('name="tipo_conta"', content)

    def test_creating_funcionario_with_tipo_conta(self):
        url = reverse('cadastros:funcionario_create')
        data = {
            'nome_completo': 'Carlos',
            'cpf': '12345678901',
            'funcao': '',
            'tipo_contrato': 'CLT',
            'salario': '1000.00',
            'banco': 'Banco X',
            'agencia': '1234',
            'conta': '56789',
            'tipo_conta': 'CORRENTE'
        }
        resp = self.client.post(url, data)
        # Expect redirect to list or detail (201 behavior is redirect for creation)
        self.assertIn(resp.status_code, (302, 200))
        f = Funcionario.objects.filter(nome_completo='Carlos').first()
        self.assertIsNotNone(f)
        self.assertEqual(f.tipo_conta, 'CORRENTE')

    def test_funcionario_form_renders_pix_fields(self):
        url = reverse('cadastros:funcionario_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('name="pix_habilitado"', content)
        self.assertIn('name="tipo_chave_pix"', content)
        self.assertIn('name="chave_pix"', content)
        # Ensure new pix fields wrappers are present
        self.assertIn('id="pix-options"', content)
        self.assertIn('id="tipo_chave_pix_field"', content)
        self.assertIn('id="chave_pix_field"', content)

    def test_creating_funcionario_with_pix(self):
        url = reverse('cadastros:funcionario_create')
        data = {
            'nome_completo': 'Mariana',
            'cpf': '22233344455',
            'funcao': '',
            'tipo_contrato': 'CLT',
            'salario': '1200.00',
            'banco': 'Banco Y',
            'agencia': '4321',
            'conta': '98765',
            'tipo_conta': 'POUPANCA',
            'pix_habilitado': 'on',
            'tipo_chave_pix': 'EMAIL',
            'chave_pix': 'mariana@example.com'
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 200))
        f = Funcionario.objects.filter(nome_completo='Mariana').first()
        self.assertIsNotNone(f)
        self.assertTrue(f.pix_habilitado)
        self.assertEqual(f.tipo_chave_pix, 'EMAIL')
        self.assertEqual(f.chave_pix, 'mariana@example.com')
