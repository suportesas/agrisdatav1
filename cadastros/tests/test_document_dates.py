from django.test import TestCase, Client
from empresas.models import Empresa, Plano
from django.contrib.auth import get_user_model
from cadastros.models import Fazenda, DocumentoFazenda, Fornecedor, DocumentoFornecedor
from django.urls import reverse
from datetime import date


class DocumentoDateRenderTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='P1', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='ED', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='ud', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='ud', password='pass')
        self.fazenda = Fazenda.objects.create(empresa=self.empresa, nome='F', cnpj_cpf='11.111.111/0001-11', area_total=1)
        self.fornecedor = Fornecedor.objects.create(empresa=self.empresa, nome='For1')

    def test_fazenda_document_edit_shows_date_values(self):
        doc = DocumentoFazenda.objects.create(fazenda=self.fazenda, tipo='OUTROS', titulo='D1', arquivo='fazendas/documentos/x.pdf', data_emissao=date(2024,1,2), data_validade=date(2025,2,3))
        url = reverse('cadastros:documento_update', args=[self.fazenda.pk, doc.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('value="2024-01-02"', content)
        self.assertIn('value="2025-02-03"', content)

    def test_fornecedor_document_edit_shows_date_values(self):
        doc = DocumentoFornecedor.objects.create(fornecedor=self.fornecedor, tipo='OUTROS', titulo='D2', arquivo='fornecedores/documentos/x.pdf', data_emissao=date(2023,5,6), data_validade=date(2024,6,7))
        url = reverse('cadastros:fornecedor_documento_update', args=[self.fornecedor.pk, doc.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('value="2023-05-06"', content)
        self.assertIn('value="2024-06-07"', content)