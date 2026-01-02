from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, Mock
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente
from django.core.files.uploadedfile import SimpleUploadedFile

class AjaxSubresourcesTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.c = Cliente.objects.create(empresa=self.empresa, razao_social='C', cnpj_cpf='12345678901')

    def test_get_contato_form_ajax(self):
        url = reverse('cadastros:cliente_contato_create_ajax', args=[self.c.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('form_html', data)

    def test_post_contato_ajax(self):
        url = reverse('cadastros:cliente_contato_create_ajax', args=[self.c.pk])
        resp = self.client.post(url, {'nome':'X','telefone':'123'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('item_html', data)

    def test_post_conta_ajax(self):
        url = reverse('cadastros:cliente_conta_create_ajax', args=[self.c.pk])
        resp = self.client.post(url, {'banco':'Banco Teste','conta':'12345'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('item_html', data)

    def test_post_documento_ajax(self):
        url = reverse('cadastros:cliente_documento_create_ajax', args=[self.c.pk])
        f = SimpleUploadedFile('doc.pdf', b'PDFDATA', content_type='application/pdf')
        data = {'tipo':'CONTRATO','titulo':'T','data_emissao':'2025-01-01','data_validade':'2025-12-31','arquivo': f}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200, msg=resp.content.decode('utf-8'))
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertIn('item_html', data)
