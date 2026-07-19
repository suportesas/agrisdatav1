from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from rh.models import FuncaoFuncionario


class FuncaoAjaxTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_create_funcao_ajax_success(self):
        url = reverse('cadastros:funcao_create_ajax')
        data = {'nome': 'Tratorista', 'descricao': 'Operador de trator', 'salario_base': '1500.00', 'ativa': 'on'}
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data.get('sucesso'))
        self.assertTrue(FuncaoFuncionario.objects.filter(nome='Tratorista').exists())

    def test_create_funcao_ajax_validation_error(self):
        url = reverse('cadastros:funcao_create_ajax')
        data = {'descricao': 'Sem nome'}  # missing required nome
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 400)
        json_data = resp.json()
        self.assertFalse(json_data.get('sucesso'))
        self.assertIn('nome', json_data.get('erros', {}))
