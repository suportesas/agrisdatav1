from django.test import TestCase, Client
from django.urls import reverse
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente, Porto

class ClienteDetailRenderTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        # Create a porto - empresa/codigo/pais/cidade sao obrigatorios no model
        # (empresa e FK NOT NULL; sem ela objects.create() levanta IntegrityError)
        self.porto = Porto.objects.create(empresa=self.empresa, codigo='PT01', nome='Porto Teste', pais='Brasil', cidade='Salvador')
        # Create cliente with several fields populated to exercise template
        self.cliente = Cliente.objects.create(
            empresa=self.empresa,
            razao_social='Cliente Teste',
            nome_comercial='Comercial Teste',
            cnpj_cpf='12345678901',
            contribuinte_icms=True,
            indicador_ie='1',
            inscricao_suframa='SUF123',
            eori='EORI123',
            vat='VAT123',
            porto_destino=self.porto,
            pais='Brasil',
            limite_credito=1000,
            prazo_pagamento=30,
        )
        # assign cadastrado_por explicitly
        self.cliente.cadastrado_por = self.user
        self.cliente.save()

    def test_cliente_detail_renders_added_fields(self):
        url = reverse('cadastros:cliente_detail', args=[self.cliente.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Check expected strings
        self.assertIn('Contribuinte ICMS', content)
        self.assertIn('Indicador IE', content)
        self.assertIn('Inscrição SUFRAMA', content)
        self.assertIn('VAT', content)
        self.assertIn('Porto Destino', content)
        self.assertIn('Cadastrado por', content)
        self.assertIn(self.user.username, content)
