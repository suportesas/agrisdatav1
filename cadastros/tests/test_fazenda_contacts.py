from django.test import TestCase, Client
from django.urls import reverse
from empresas.models import Plano, Empresa
from usuarios.models import Usuario
from cadastros.models import Fazenda, ContatoFazenda

class FazendaContatoTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        self.f = Fazenda.objects.create(empresa=self.empresa, nome='F', cnpj_cpf='12345678901')

    def test_create_contato_without_telefone(self):
        url = reverse('cadastros:contato_create', args=[self.f.pk])
        resp = self.client.post(url, {'nome': 'Sem Telefone', 'email': 's@example.com'})
        self.assertEqual(resp.status_code, 302)
        self.f.refresh_from_db()
        self.assertEqual(self.f.contatos.count(), 1)
        c = self.f.contatos.first()
        self.assertEqual(c.nome, 'Sem Telefone')
        self.assertEqual(c.telefone, '')
