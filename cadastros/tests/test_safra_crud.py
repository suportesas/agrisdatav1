from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from empresas.models import Empresa, Plano
from cadastros.models import Fazenda, Cultura, Safra, SafraCultura


class SafraCrudTest(TestCase):
    def setUp(self):
        plano = Plano.objects.create(codigo='PEQ', nome='P', valor_mensal=1)
        self.empresa = Empresa.objects.create(nome='E', plano=plano)
        User = get_user_model()
        self.user = User.objects.create_user(username='u', password='pass')
        self.user.empresa = self.empresa
        self.user.save()
        self.fazenda = Fazenda.objects.create(nome='F', empresa=self.empresa, area_total=1, cadastrado_por=self.user)
        self.cultura = Cultura.objects.create(nome='Milho', empresa=self.empresa)
        self.cultura2 = Cultura.objects.create(nome='Soja', empresa=self.empresa)
        self.client = Client()
        self.client.login(username='u', password='pass')

    def _formset_data(self, culturas, total_forms=None, initial_forms=0):
        """Monta os campos do management form + linhas do SafraCulturaFormSet (prefix='culturas')."""
        rows = list(culturas)
        data = {
            'culturas-TOTAL_FORMS': str(total_forms if total_forms is not None else len(rows)),
            'culturas-INITIAL_FORMS': str(initial_forms),
            'culturas-MIN_NUM_FORMS': '1',
            'culturas-MAX_NUM_FORMS': '1000',
        }
        for i, row in enumerate(rows):
            data[f'culturas-{i}-id'] = row.get('id', '')
            data[f'culturas-{i}-cultura'] = str(row['cultura'])
            data[f'culturas-{i}-periodo_inicio'] = row.get('periodo_inicio', '')
            data[f'culturas-{i}-periodo_fim'] = row.get('periodo_fim', '')
            data[f'culturas-{i}-status'] = row.get('status', 'PLANEJADA')
        return data

    def test_create_safra(self):
        url = reverse('cadastros:safra_create')
        data = {
            'nome': 'Safra Teste',
            'fazenda': str(self.fazenda.pk),
            'ano': '2025',
        }
        data.update(self._formset_data([
            {'cultura': self.cultura.pk, 'periodo_inicio': '2025-01-01', 'periodo_fim': '2025-12-31'},
        ]))
        resp = self.client.post(url, data)
        # redireciona para detail
        self.assertEqual(resp.status_code, 302)
        safra = Safra.objects.filter(nome='Safra Teste').first()
        self.assertIsNotNone(safra)
        self.assertEqual(safra.culturas.count(), 1)
        self.assertEqual(safra.culturas.first().cultura, self.cultura)

    def test_create_safra_com_multiplas_culturas(self):
        """Uma mesma safra pode ter mais de uma cultura (o motivo desta refatoração)."""
        url = reverse('cadastros:safra_create')
        data = {
            'nome': 'Safra 2026/27',
            'fazenda': str(self.fazenda.pk),
            'ano': '2026',
        }
        data.update(self._formset_data([
            {'cultura': self.cultura.pk, 'status': 'PLANEJADA'},
            {'cultura': self.cultura2.pk, 'status': 'PLANEJADA'},
        ]))
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        safra = Safra.objects.get(nome='Safra 2026/27')
        self.assertEqual(safra.culturas.count(), 2)
        nomes = set(safra.culturas.values_list('cultura__nome', flat=True))
        self.assertEqual(nomes, {'Milho', 'Soja'})

    def test_update_safra(self):
        safra = Safra.objects.create(nome='Old', fazenda=self.fazenda, ano=2025)
        sc = SafraCultura.objects.create(safra=safra, cultura=self.cultura)
        url = reverse('cadastros:safra_update', args=[safra.pk])
        data = {
            'nome': 'Atualizada',
            'fazenda': str(self.fazenda.pk),
            'ano': '2025',
        }
        data.update(self._formset_data(
            [{'id': sc.pk, 'cultura': self.cultura.pk}],
            initial_forms=1,
        ))
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        safra.refresh_from_db()
        self.assertEqual(safra.nome, 'Atualizada')

    def test_delete_safra(self):
        safra = Safra.objects.create(nome='Del', fazenda=self.fazenda, ano=2025)
        SafraCultura.objects.create(safra=safra, cultura=self.cultura)
        url = reverse('cadastros:safra_delete', args=[safra.pk])
        resp = self.client.post(url, {})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Safra.objects.filter(pk=safra.pk).exists())
