from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, Mock
from empresas.models import Empresa, Plano

User = get_user_model()


class BuscarCepTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_buscar_cep_invalid(self):
        url = reverse('cadastros:buscar_cep')
        resp = self.client.post(url, {'cep': '123'})
        self.assertEqual(resp.status_code, 400)

    @patch('cadastros.views.requests.get')
    def test_buscar_cep_not_found(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'erro': True}
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cep')
        resp = self.client.post(url, {'cep': '00000000'})
        self.assertEqual(resp.status_code, 404)

    @patch('cadastros.views.requests.get')
    def test_buscar_cep_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'cep': '01001-000',
            'logradouro': 'Praça da Sé',
            'complemento': 'lado ímpar',
            'bairro': 'Sé',
            'localidade': 'São Paulo',
            'uf': 'SP'
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cep')
        resp = self.client.post(url, {'cep': '01001000'})
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data.get('sucesso'))
        self.assertIn('dados', json_data)
        self.assertEqual(json_data['dados']['cidade'], 'São Paulo')
        # Backwards-compatibility: old clients expect top-level fields too
        self.assertIn('logradouro', json_data)
        self.assertEqual(json_data['logradouro'], 'Praça da Sé')

    @patch('cadastros.views.requests.get')
    def test_buscar_cep_get_success(self, mock_get):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'cep': '01001-000',
            'logradouro': 'Praça da Sé',
            'complemento': 'lado ímpar',
            'bairro': 'Sé',
            'localidade': 'São Paulo',
            'uf': 'SP'
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cep') + '?cep=01001000'
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data.get('sucesso'))
        self.assertEqual(json_data['dados']['cidade'], 'São Paulo')

    @patch('cadastros.views.requests.get')
    def test_buscar_cep_cached(self, mock_get):
        from django.core.cache import cache
        cache.clear()

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'cep': '01001-000',
            'logradouro': 'Praça da Sé',
            'complemento': 'lado ímpar',
            'bairro': 'Sé',
            'localidade': 'São Paulo',
            'uf': 'SP'
        }
        mock_get.return_value = mock_resp

        url = reverse('cadastros:buscar_cep')
        resp1 = self.client.post(url, {'cep': '01001000'})
        self.assertEqual(resp1.status_code, 200)
        mock_get.side_effect = Exception('Should not be called when cached')
        resp2 = self.client.post(url, {'cep': '01001000'})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.json()['dados']['cidade'], 'São Paulo')
