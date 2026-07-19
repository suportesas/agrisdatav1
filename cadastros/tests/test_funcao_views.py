from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Plano, Empresa
from rh.models import FuncaoFuncionario, Funcionario


class FuncaoViewsTests(TestCase):
    def setUp(self):
        self.plano = Plano.objects.create(codigo='TV', nome='T', valor_mensal=0, valor_anual=0)
        self.empresa = Empresa.objects.create(nome='Emp', plano=self.plano)
        self.funcao = FuncaoFuncionario.objects.create(empresa=self.empresa, nome='Motorista')
        # create and login user
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='p')
        self.user.empresa = self.empresa
        self.user.save()
        self.client.force_login(self.user)

    def test_update_funcao(self):
        url = reverse('cadastros:funcao_update', args=[self.funcao.pk])
        resp = self.client.post(url, {'nome': 'Motorista X', 'descricao': '', 'salario_base': '', 'ativa': True})
        self.assertEqual(resp.status_code, 302)
        self.funcao.refresh_from_db()
        self.assertEqual(self.funcao.nome, 'Motorista X')

    def test_cannot_delete_when_has_employees(self):
        f = Funcionario.objects.create(empresa=self.empresa, nome_completo='Joao', cpf='00000000123', funcao=self.funcao, salario=0)
        url = reverse('cadastros:funcao_delete', args=[self.funcao.pk])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        # function should still exist
        self.assertTrue(FuncaoFuncionario.objects.filter(pk=self.funcao.pk).exists())

    def test_create_funcao_non_ajax_fallback(self):
        url = reverse('cadastros:funcao_create')
        resp = self.client.post(url, {'nome': 'Operador', 'descricao': 'x', 'salario_base': '0', 'ativa': 'on'})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(FuncaoFuncionario.objects.filter(nome='Operador').exists())
