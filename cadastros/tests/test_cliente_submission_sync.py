from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario
from empresas.models import Empresa, Plano
from cadastros.models import Cliente, PrazoPagamentoPadrao

class ClienteSubmissionSyncTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='syncuser', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_login(self.user)
        self.preset = PrazoPagamentoPadrao.objects.create(empresa=self.empresa, nome='30/60', termos='30,60', ativo=True)

    def test_post_with_fields_saves_all(self):
        url = reverse('cadastros:cliente_create')
        data = {
            'razao_social': 'Client Sync',
            'cnpj_cpf': '99999999999999',
            'tipo_cliente': 'NACIONAL',
            'tipo_pessoa': 'PJ',
            'vendedor_responsavel': '',
            'limite_credito': '1500.50',
            'prazo_pagamento': '60',
            'prazo_pagamento_padrao': str(self.preset.pk),
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        c = Cliente.objects.get(razao_social='Client Sync')
        self.assertEqual(str(c.prazo_pagamento_padrao.pk), str(self.preset.pk))
        self.assertEqual(c.prazo_pagamento, 60)
        self.assertEqual(float(c.limite_credito), 1500.50)