from django.urls import reverse
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Safra, SafraCultura, Talhao, Cultura
from cadastros.forms import SafraForm


class SafraViewsTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.client = Client()
        self.client.login(username='u', password='pass')

    def test_safra_list_view_authenticated(self):
        resp = self.client.get(reverse('cadastros:safra_list'))
        self.assertEqual(resp.status_code, 200)


    def test_safra_list_renders_template(self):
        """Smoke test: GET /cadastros/safras/ renders safra_list template without error"""
        resp = self.client.get(reverse('cadastros:safra_list'))
        self.assertEqual(resp.status_code, 200)
        # Ensure the correct template was used
        self.assertTemplateUsed(resp, 'cadastros/safra/safra_list.html')


    def test_safra_form_contains_choicesjs(self):
        resp = self.client.get(reverse('cadastros:safra_create'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Smoke test da tela de criacao: garante renderizacao do formulario e do formset de culturas
        # (o formset começa vazio — a linha só existe no template usado pelo JS "Adicionar Cultura")
        self.assertIn('id="id_fazenda"', content)
        self.assertIn('id="btn-add-cultura"', content)
        self.assertIn('id="cultura-empty-form-template"', content)
        self.assertIn('id="id_culturas-__prefix__-cultura"', content)
        self.assertIn('id="id_culturas-__prefix__-periodo_inicio"', content)


    def test_safra_list_filters_and_pagination(self):
        # Cria fazenda e cultura
        fazenda = self.empresa.fazendas.create(nome='F Teste', area_total=10)

        # Cria 30 safras para testar paginação
        for i in range(30):
            Safra.objects.create(fazenda=fazenda, ano=2000 + i)

        resp = self.client.get(reverse('cadastros:safra_list'))
        self.assertEqual(resp.status_code, 200)
        # Deve conter page_obj no contexto
        self.assertIn('page_obj', resp.context)
        page_obj = resp.context['page_obj']
        self.assertTrue(page_obj.paginator.num_pages >= 2)

        # Testa filtro por ano
        resp2 = self.client.get(reverse('cadastros:safra_list') + '?ano=2005')
        self.assertEqual(resp2.status_code, 200)
        # Apenas safras com ano=2005
        safras = resp2.context['safras']
        for s in safras:
            self.assertEqual(s.ano, 2005)


    def test_safra_list_filter_by_fazenda_and_search(self):
        fazenda1 = self.empresa.fazendas.create(nome='Fazenda A', area_total=10, cnpj_cpf='11111111000101')
        fazenda2 = self.empresa.fazendas.create(nome='Fazenda B', area_total=10, cnpj_cpf='22222222000102')

        Safra.objects.create(fazenda=fazenda1, ano=2025, nome='Safra Alfa')
        Safra.objects.create(fazenda=fazenda2, ano=2025, nome='Safra Beta')

        # Filter by fazenda1
        resp = self.client.get(reverse('cadastros:safra_list') + f'?fazenda={fazenda1.pk}')
        self.assertEqual(resp.status_code, 200)
        safras = resp.context['safras']
        self.assertTrue(all(s.fazenda_id == fazenda1.pk for s in safras))

        # Search by name
        resp2 = self.client.get(reverse('cadastros:safra_list') + '?q=Alfa')
        self.assertEqual(resp2.status_code, 200)
        safras2 = resp2.context['safras']
        self.assertTrue(any('Alfa' in str(s) for s in safras2))

    def test_safra_edit_prefills_periodo_fields(self):
        # Create related objects and a safra cuja cultura tem periodo preenchido
        fazenda = self.empresa.fazendas.create(nome='F Teste 3', area_total=10)
        cultura = self.empresa.culturas.create(nome='C Teste 3')
        safra = Safra.objects.create(fazenda=fazenda)
        SafraCultura.objects.create(safra=safra, cultura=cultura, periodo_inicio='2025-01-01', periodo_fim='2025-12-31')

        url = reverse('cadastros:safra_update', args=[safra.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode('utf-8')
        # Ensure the date values are present in the rendered form inputs
        self.assertIn('value="2025-01-01"', content)
        self.assertIn('value="2025-12-31"', content)


    def test_ajax_talhoes_in_use_flag_and_form_validation(self):
        # Setup: fazenda, talhao, safra that uses talhao
        fazenda = self.empresa.fazendas.create(nome='F Teste 2', area_total=10)
        area = fazenda.areas.create(nome='A1', area_total=5, area_plantavel=4, empresa=self.empresa)
        talhao = Talhao.objects.create(area=area, fazenda=fazenda, nome='T1', codigo='T1', area_hac=1, empresa=self.empresa)

        cultura = Cultura.objects.create(empresa=self.empresa, nome='C Teste 2')
        safra_existing = Safra.objects.create(fazenda=fazenda, ano=2025)
        sc = SafraCultura.objects.create(safra=safra_existing, cultura=cultura)
        sc.talhoes.add(talhao)

        # AJAX should mark talhao as in_use
        url = reverse('cadastros:ajax_talhoes_fazenda', args=[fazenda.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(any(item['id'] == talhao.id and item['in_use'] for item in data))

        # Form should reject uma 2a safra para a mesma fazenda/ano
        form_data = {
            'fazenda': fazenda.pk,
            'ano': 2025,
        }
        form = SafraForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
