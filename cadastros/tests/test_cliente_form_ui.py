from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario
from empresas.models import Empresa
from cadastros.models import Cliente

class ClienteFormUITests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='ui', password='ui')
        emp = Empresa.objects.create(nome='Empresa UI')
        self.user.empresa = emp
        self.user.save()
        self.client.force_login(self.user)

    def test_cliente_form_contains_buscar_cnpj_and_modal(self):
        url = reverse('cadastros:cliente_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('id="buscarCNPJ"', content)
        self.assertIn('id="cnpjLoadingModal"', content)
        self.assertIn('id="cnpjFeedback"', content)
        # Confirmation modal present
        self.assertIn('id="cnpjConfirmModal"', content)
        # Fields marked for auto-fill
        self.assertIn('data-auto="true"', content)
        # Vendedor select present
        self.assertIn('name="vendedor_responsavel"', content)
        # VAT field present for importadores
        self.assertIn('id="id_vat"', content)

    def test_cliente_detail_uses_shared_header_and_shows_ministats(self):
        # Create client and check detail page for header include and ministats
        from django.urls import reverse
        c = Cliente.objects.create(empresa=Empresa.objects.create(nome='E2'), razao_social='C Header', cnpj_cpf='12345678901234')
        url = reverse('cadastros:cliente_detail', args=[c.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Check header title present
        self.assertIn('C Header', content)
        # Ministats: labels
        self.assertIn('Endereços', content)
        self.assertIn('Contatos', content)
        self.assertIn('Contas', content)
        self.assertIn('Documentos', content)
        # Quick action buttons
        self.assertIn('Adicionar Contato', content)
        self.assertIn('Anexar Documento', content)
        self.assertIn('Enviar e‑mail', content)
        self.assertIn('Gerar Proposta', content)

    def test_modals_have_aria_and_accessibility_attributes(self):
        url = reverse('cadastros:cliente_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Global CNPJ modals
        self.assertIn('aria-labelledby="cnpjLoadingText"', content)
        self.assertIn('aria-modal="true"', content)
        self.assertIn('aria-describedby="cnpjConfirmNote"', content)
        # Proposal modal
        self.assertIn('aria-describedby="proposalMessage"', content)

    def test_update_client_without_empresa_field_preserves_empresa(self):
        # Create empresa and client; logon user must belong to the same empresa
        emp = Empresa.objects.create(nome='Empresa Update')
        self.user.empresa = emp
        self.user.save()
        c = Cliente.objects.create(empresa=emp, razao_social='Original', cnpj_cpf='12345678901234')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        # Post data intentionally omitting the hidden 'empresa' field
        data = {
            'razao_social': 'Updated',
            'cnpj_cpf': c.cnpj_cpf,
            'tipo_cliente': c.tipo_cliente,
            'tipo_pessoa': c.tipo_pessoa,
        }
        resp = self.client.post(url, data)
        # Should redirect on success
        self.assertEqual(resp.status_code, 302)
        c.refresh_from_db()
        self.assertEqual(c.empresa, emp)
        self.assertEqual(c.razao_social, 'Updated')

    def test_update_client_importador_requires_fields(self):
        from django.urls import reverse
        emp = Empresa.objects.create(nome='Empresa Update 2')
        self.user.empresa = emp
        self.user.save()
        c = Cliente.objects.create(empresa=emp, razao_social='Original', cnpj_cpf='12345678901234')
        url = reverse('cadastros:cliente_update', args=[c.pk])
        # Try to update to IMPORTADOR without required import fields
        data = {
            'razao_social': 'Updated Importador',
            'cnpj_cpf': c.cnpj_cpf,
            'tipo_cliente': 'IMPORTADOR',
            'tipo_pessoa': c.tipo_pessoa,
            # missing eori, vat, porto_destino
        }
        resp = self.client.post(url, data)
        # Should not redirect because form invalid
        self.assertNotEqual(resp.status_code, 302)
        form = resp.context.get('form')
        self.assertIsNotNone(form)
        # Expect errors for required import fields
        self.assertIn('eori', form.errors)
        self.assertIn('vat', form.errors)
        self.assertIn('porto_destino', form.errors)
