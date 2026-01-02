from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Fazenda, ContaBancariaFazenda


class FazendaBankingTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='tfaz', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='tfaz', password='pass')
        self.f = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda Teste', cnpj_cpf='88888888888')

    def test_fazenda_conta_form_renders_tipo_conta_and_pix(self):
        url = reverse('cadastros:conta_bancaria_create', args=[self.f.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('name="tipo_conta"', content)
        self.assertIn('name="pix_habilitado"', content)
        self.assertIn('name="tipo_chave_pix"', content)
        self.assertIn('name="chave_pix"', content)
        self.assertIn('id="pix-options"', content)

    def test_creating_fazenda_conta_with_pix(self):
        url = reverse('cadastros:conta_bancaria_create', args=[self.f.pk])
        data = {
            'banco': 'Banco Teste',
            'agencia': '0001',
            'conta': '12345',
            'conta_digito': '6',
            'tipo_conta': 'CORRENTE',
            'pix_habilitado': 'on',
            'tipo_chave_pix': 'EMAIL',
            'chave_pix': 'fazenda@example.com'
        }
        resp = self.client.post(url, data)
        self.assertIn(resp.status_code, (302, 200))
        conta = ContaBancariaFazenda.objects.filter(fazenda=self.f, banco='Banco Teste').first()
        self.assertIsNotNone(conta)
        self.assertTrue(conta.pix_habilitado)
        self.assertEqual(conta.tipo_chave_pix, 'EMAIL')
        self.assertEqual(conta.chave_pix, 'fazenda@example.com')
