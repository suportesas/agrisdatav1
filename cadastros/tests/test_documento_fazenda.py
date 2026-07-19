from django.test import TestCase, Client
from empresas.models import Empresa, Plano
from django.contrib.auth import get_user_model
from cadastros.models import Fazenda, DocumentoFazenda
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import timedelta
from django.utils import timezone


class DocumentoFazendaUploadTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E2', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u2', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u2', password='pass')
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='Faz1', cnpj_cpf='11.111.111/0001-11', area_total=5)

    def test_fazenda_document_upload_without_numero(self):
        url = reverse('cadastros:documento_create', args=[self.fazenda.pk])
        f = SimpleUploadedFile('doc.pdf', b'PDFDATA', content_type='application/pdf')
        data = {
            'tipo': 'OUTROS',
            'titulo': 'Doc Fazenda',
            'arquivo': f,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(self.fazenda.documentos.filter(titulo='Doc Fazenda').exists())

    def test_fazenda_document_form_contains_numero_input(self):
        url = reverse('cadastros:documento_create', args=[self.fazenda.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Check label and input presence
        self.assertIn('Número do Documento', content)
        self.assertIn('name="numero_documento"', content)

    def test_fazenda_document_form_field_types(self):
        url = reverse('cadastros:documento_create', args=[self.fazenda.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Emissão/validade devem ser date inputs
        self.assertIn('name="data_emissao"', content)
        self.assertIn('type="date"', content)
        self.assertIn('name="data_validade"', content)
        # Dias de antecedência deve ser number input
        self.assertIn('name="dias_antecedencia_alerta"', content)
        self.assertIn('type="number"', content)
        # Observações deve ser uma textarea
        self.assertIn('<textarea', content)
        self.assertIn('name="observacoes"', content)

    def test_edit_document_via_view(self):
        # Create a document
        doc = DocumentoFazenda.objects.create(fazenda=self.fazenda, tipo='OUTROS', titulo='Old', arquivo='fazendas/documentos/a.pdf')
        url = reverse('cadastros:documento_update', args=[self.fazenda.pk, doc.pk])
        # GET shows form with existing title
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Old', resp.content.decode('utf-8'))
        # POST updated title
        resp = self.client.post(url, {'tipo': 'OUTROS', 'titulo': 'New', 'arquivo': ''})
        self.assertEqual(resp.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.titulo, 'New')
