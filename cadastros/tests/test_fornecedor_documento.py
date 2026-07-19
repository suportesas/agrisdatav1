from django.test import TestCase
from empresas.models import Empresa, Plano
from django.contrib.auth import get_user_model
from cadastros.models import Fornecedor, DocumentoFornecedor
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from django.utils import timezone
from django.test import Client


class FornecedorDetailDocumentAlertsTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQD', nome='PD', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E3', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u3', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u3', password='pass')
        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome='Faux')

    def test_detail_shows_website_and_document_alerts(self):
        self.fornecedor.website = 'https://example.com'
        self.fornecedor.save()
        past = timezone.now().date() - timedelta(days=5)
        DocumentoFornecedor.objects.create(
            fornecedor=self.fornecedor, tipo='OUTROS', titulo='Old Doc',
            arquivo='fornecedores/documentos/old.pdf', data_validade=past,
            gerar_alerta_vencimento=True,
        )
        url = reverse('cadastros:fornecedor_detail', args=[self.fornecedor.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('https://example.com', content)
        self.assertIn('Atenção', content)
        self.assertIn('Vencido', content)


class DocumentoFornecedorUploadTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E2', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u2', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u2', password='pass')
        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome='Faz1')

    def test_fornecedor_document_edit(self):
        doc = DocumentoFornecedor.objects.create(fornecedor=self.fornecedor, tipo='OUTROS', titulo='Orig', arquivo='fornecedores/documentos/a.pdf')
        url = reverse('cadastros:fornecedor_documento_update', args=[self.fornecedor.pk, doc.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Orig', resp.content.decode('utf-8'))
        resp = self.client.post(url, {'tipo': 'OUTROS', 'titulo': 'Edited', 'arquivo': ''})
        self.assertEqual(resp.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.titulo, 'Edited')