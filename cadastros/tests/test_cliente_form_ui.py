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
        # Confirmation modal was removed: CNPJ lookup now applies data directly
        self.assertNotIn('id="cnpjConfirmModal"', content)
        # Fields marked for auto-fill
        self.assertIn('data-auto="true"', content)
        # Vendedor select present
        self.assertIn('name="vendedor_responsavel"', content)
        # VAT field present for importadores
        self.assertIn('id="id_vat"', content)

    def test_cliente_detail_uses_shared_header_and_shows_ministats(self):
        # cliente_detail faz get_object_or_404(..., empresa=request.user.empresa)
        # — o cliente tem que pertencer a MESMA empresa do usuario logado,
        # senao da 404 em vez de 200 (o teste original criava numa empresa
        # diferente da de self.user).
        c = Cliente.objects.create(empresa=self.user.empresa, razao_social='C Header', cnpj_cpf='12345678901234')
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
        # Quick action buttons ("Enviar e-mail" nao existe nessa tela atualmente)
        self.assertIn('Adicionar Contato', content)
        self.assertIn('Anexar Documento', content)
        self.assertIn('Gerar Proposta', content)

    def test_modals_have_aria_and_accessibility_attributes(self):
        url = reverse('cadastros:cliente_create')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Global CNPJ modals (templates/base.html — presentes em toda página)
        self.assertIn('aria-labelledby="cnpjLoadingText"', content)

    def test_detail_proposal_modal_has_aria_attributes(self):
        # O modal de Proposta so existe no detalhe do cliente (cliente_detail.html), nao no form
        emp = Empresa.objects.create(nome='Empresa Proposal')
        self.user.empresa = emp
        self.user.save()
        c = Cliente.objects.create(empresa=emp, razao_social='C Proposal', cnpj_cpf='12345678901234')
        url = reverse('cadastros:cliente_detail', args=[c.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
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

    def test_preset_select_shows_selected_on_edit(self):
        # Ensure that when editing a client with a preset, the select is pre-selected on the form
        from django.urls import reverse
        from cadastros.models import PrazoPagamentoPadrao
        emp = Empresa.objects.create(nome='Empresa Preset')
        self.user.empresa = emp
        self.user.save()
        preset = PrazoPagamentoPadrao.objects.create(empresa=emp, nome='30/60/90', termos='30,60,90', ativo=True)
        c = Cliente.objects.create(empresa=emp, razao_social='Com Preset', cnpj_cpf='10101010101010', prazo_pagamento_padrao=preset, prazo_pagamento=60)
        url = reverse('cadastros:cliente_update', args=[c.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Option with preset pk should be selected
        self.assertIn(f'<option value="{preset.pk}"', content)
        self.assertIn('selected', content)
        # The prazo input should reflect the client's prazo_pagamento value
        self.assertIn('id="id_prazo_pagamento"', content)
        self.assertIn('value="60"', content)
