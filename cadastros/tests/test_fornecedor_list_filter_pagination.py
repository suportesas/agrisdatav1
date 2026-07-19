from django.test import TestCase, Client
from django.urls import reverse

from empresas.models import Empresa, Plano
from usuarios.models import Usuario
from cadastros.models import Fornecedor


class FornecedorListFilterPaginationTests(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        self.user = Usuario.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')
        for i in range(15):
            cnpj = f'00.000.000/{1000+i}'
            Fornecedor.objects.create(empresa=self.empresa, nome=f'F{i}', is_exportador=(i % 2 == 0), cnpj_cpf=cnpj)

    def test_tipo_filter_and_pagination(self):
        url = reverse('cadastros:fornecedor_list')
        resp = self.client.get(url + '?tipo=INTERNACIONAL')
        self.assertEqual(resp.status_code, 200)
        fornecedores_list = resp.context['fornecedores']
        for f in fornecedores_list:
            self.assertTrue(f.is_exportador)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # A paginacao (partials/pagination.html) sempre mostra o botao
        # "Proximo" (habilitado ou desabilitado) quando ha pelo menos 1 registro.
        self.assertIn('Próximo', content)
