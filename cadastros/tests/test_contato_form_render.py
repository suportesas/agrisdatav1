from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Fazenda

class ContatoFormRenderTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='tuser', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='tuser', password='pass')
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Fazenda Teste', cnpj_cpf='12345678901')

    def test_contato_form_has_single_email_field(self):
        url = reverse('cadastros:contato_create', args=[self.fazenda.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Ensure there's exactly one input/select with name="email"
        occurrences = content.count('name="email"')
        # Also check id occurrence
        id_occ = content.count('id="id_email"')
        self.assertEqual(occurrences, 1, msg=f'Expected a single email input, found {occurrences}')
        self.assertEqual(id_occ, 1, msg=f'Expected single id for email, found {id_occ}')

    def test_cliente_contato_form_renders_tipo_and_whatsapp(self):
        from cadastros.models import Cliente
        cliente = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente Teste', cnpj_cpf='22222222222')
        url = reverse('cadastros:cliente_contato_create', args=[cliente.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('name="tipo"', content)
        self.assertIn('name="whatsapp"', content)
        # Ensure celular appears exactly once
        self.assertEqual(content.count('name="celular"'), 1)

    def test_cliente_contato_create_without_tipo_succeeds(self):
        from cadastros.models import Cliente, ContatoCliente
        cliente = Cliente.objects.create(empresa=self.empresa, razao_social='Cliente Teste 2', cnpj_cpf='33333333333')
        url = reverse('cadastros:cliente_contato_create', args=[cliente.pk])
        data = {
            'nome': 'João da Silva',
            'telefone': '',
            'celular': '11999990000',
            'email': 'joao@example.com'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        contato = ContatoCliente.objects.filter(cliente=cliente, nome='João da Silva').first()
        self.assertIsNotNone(contato)
        # Default tipo should be PRINCIPAL
        self.assertEqual(contato.tipo, 'PRINCIPAL')
