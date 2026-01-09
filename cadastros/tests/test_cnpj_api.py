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

    @patch('cadastros.views.requests.get')
    def test_buscar_cnpj_get_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'status': 'OK',
            'nome': 'Empresa Exemplo GET',
            'fantasia': 'Exemplo GET',
            'cnpj': '00000000000100',
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cnpj') + '?cnpj=00.000.000/0001-00'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('sucesso'))
        self.assertEqual(data['dados']['nome'], 'Empresa Exemplo GET')

    @patch('cadastros.views.requests.get')
    def test_buscar_cnpj_cached(self, mock_get):
        from django.core.cache import cache
        cache.clear()

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'status': 'OK',
            'nome': 'Empresa Cache',
            'fantasia': 'Cache',
            'cnpj': '00000000000100',
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cnpj')
        # First call populates cache
        resp1 = self.client.post(url, {'cnpj': '00.000.000/0001-00'})
        self.assertEqual(resp1.status_code, 200)
        # Make requests.get raise if called again
        mock_get.side_effect = Exception('Should not be called when cached')
        # Second call should return cached payload
        resp2 = self.client.post(url, {'cnpj': '00.000.000/0001-00'})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['dados']['nome'], 'Empresa Cache')
