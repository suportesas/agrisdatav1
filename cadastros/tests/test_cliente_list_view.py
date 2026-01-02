from django.test import TestCase
from django.urls import reverse
from usuarios.models import Usuario
from empresas.models import Empresa

class ClienteListViewTests(TestCase):
    def setUp(self):
        self.user = Usuario.objects.create_user(username='viewer', password='pass')
        emp = Empresa.objects.create(nome='Empresa List')
        self.user.empresa = emp
        self.user.save()
        self.client.force_login(self.user)

    def test_cliente_list_view_responds(self):
        url = reverse('cadastros:cliente_list')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        self.assertIn('Clientes', content)