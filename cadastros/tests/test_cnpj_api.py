from django.test import TestCase, Client
from unittest.mock import patch, Mock
from django.urls import reverse

class BuscarCnpjTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create and login a user with an empresa to pass the @login_required
        from usuarios.models import Usuario
        self.user = Usuario.objects.create_user(username='t', password='t')
        # Attach empresa if model requires; many tests in project assume user has empresa
        from empresas.models import Empresa
        emp = Empresa.objects.create(nome='Empresa CNPJ')
        self.user.empresa = emp
        self.user.save()
        self.client.force_login(self.user)

    @patch('cadastros.views.requests.get')
    def test_buscar_cnpj_success(self, mock_get):
        # Mock API response
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'status': 'OK',
            'nome': 'Empresa Exemplo LTDA',
            'fantasia': 'Exemplo',
            'cnpj': '00000000000100',
            'telefone': '11223344',
            'email': 'contato@exemplo.com',
            'logradouro': 'Av Teste',
            'numero': '100',
            'complemento': '',
            'bairro': 'Centro',
            'municipio': 'São Paulo',
            'uf': 'SP',
            'cep': '01001-000'
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cnpj')
        resp = self.client.post(url, {'cnpj': '00.000.000/0001-00'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('sucesso'))
        self.assertEqual(data['dados']['nome'], 'Empresa Exemplo LTDA')

    @patch('cadastros.views.requests.get')
    def test_buscar_cnpj_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'status': 'ERROR', 'message': 'CNPJ not found'}
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cnpj')
        resp = self.client.post(url, {'cnpj': '00.000.000/0001-99'})
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertIn('erro', data)
